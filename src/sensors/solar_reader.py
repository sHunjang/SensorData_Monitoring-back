"""
일사량(Solar) 센서 통신 모듈

이 모듈은 실제 Modbus RTU 프로토콜을 통해 일사량 센서와 통신하여
일사량 데이터를 읽어옵니다.

주요 기능:
    1. Modbus RTU 시리얼 통신
    2. 일사량 센서 데이터 읽기
    3. 5초 주기 데이터 수집
    4. 메모리 버퍼 관리
    5. 1분마다 자동 집계 및 DB 저장

하드웨어 구성:
    - 센서: Modbus RTU (RS485)
    - 통신 방식: Serial (TTL/RS485 변환기 사용)
    - 보드레이트: 9600 (기본값)

Modbus 레지스터 맵 (예시):
    - 일사량: 0x0000 (W/m² 단위)

사용법:
    python -m src.collectors.solar_reader

작성일: 2025-10-10
"""

import time
import logging
import statistics
from datetime import datetime, timezone
from typing import List, Optional

try:
    from pymodbus.client import ModbusSerialClient
    from pymodbus.exceptions import ModbusException
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False
    logging.warning("⚠️  pymodbus not installed. Install with: pip install pymodbus")

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("solar_reader")

# ========================================
# 전역 변수
# ========================================
SOLAR_DEVICE = settings.SOLAR_ID  # 31
COLLECTION_INTERVAL = settings.COLLECTION_INTERVAL  # 5초

# 메모리 버퍼: 5초 데이터를 1분간 누적
data_buffer: List[dict] = []

# Modbus 클라이언트 (전역)
modbus_client: Optional[ModbusSerialClient] = None


# ========================================
# Modbus 클라이언트 초기화
# ========================================
def init_modbus_client() -> Optional[ModbusSerialClient]:
    """
    Modbus RTU 시리얼 클라이언트 초기화
    
    Returns:
        ModbusSerialClient: 초기화된 클라이언트 또는 None
    
    설정:
        - port: settings.SOLAR_PORT (예: /dev/ttyUSB2)
        - baudrate: settings.SOLAR_BAUDRATE (기본: 9600)
        - timeout: settings.SOLAR_TIMEOUT (기본: 1.0초)
    """
    if not MODBUS_AVAILABLE:
        log.error("❌ pymodbus not available")
        return None
    
    try:
        client = ModbusSerialClient(
            port=settings.SOLAR_PORT,
            baudrate=settings.SOLAR_BAUDRATE,
            timeout=settings.SOLAR_TIMEOUT,
            bytesize=8,
            parity='N',
            stopbits=1
        )
        
        if client.connect():
            log.info(f"✅ Solar Modbus client connected: {settings.SOLAR_PORT}")
            return client
        else:
            log.error(f"❌ Solar Modbus connection failed: {settings.SOLAR_PORT}")
            return None
            
    except Exception as e:
        log.exception(f"❌ Solar Modbus client initialization failed: {e}")
        return None


# ========================================
# Modbus 레지스터 읽기
# ========================================
def read_modbus_registers(
    client: ModbusSerialClient,
    address: int,
    count: int
) -> Optional[List[int]]:
    """
    Modbus 홀딩 레지스터 읽기
    
    Args:
        client: Modbus 클라이언트
        address: 시작 레지스터 주소
        count: 읽을 레지스터 개수
    
    Returns:
        Optional[List[int]]: 레지스터 값 리스트 또는 None (실패 시)
    """
    try:
        response = client.read_holding_registers(
            address=address,
            count=count,
            slave=SOLAR_DEVICE
        )
        
        if response.isError():
            log.error(f"❌ Modbus read error: device={SOLAR_DEVICE}, addr={address}")
            return None
        
        return response.registers
        
    except ModbusException as e:
        log.error(f"❌ Modbus exception: device={SOLAR_DEVICE}, {e}")
        return None
    except Exception as e:
        log.error(f"❌ Unexpected error: device={SOLAR_DEVICE}, {e}")
        return None


# ========================================
# 일사량 센서 데이터 읽기
# ========================================
def read_solar_sensor_data(client: ModbusSerialClient) -> Optional[dict]:
    """
    일사량 센서에서 데이터 읽기
    
    Args:
        client: Modbus 클라이언트
    
    Returns:
        Optional[dict]: 일사량 데이터 또는 None (실패 시)
            {
                'device_id': int,
                'timestamp': datetime,
                'irradiance_w_per_m2': float  # 일사량 (W/m²)
            }
    
    레지스터 맵 (예시 - 실제 센서 매뉴얼 참고):
        0x0000: 일사량 (W/m² 단위, 또는 0.1 W/m² 단위)
    
    주의:
        - 레지스터 주소는 센서 모델마다 다를 수 있음
        - 스케일 팩터는 매뉴얼 참고
        - 일부 센서는 16-bit, 일부는 32-bit 사용
    """
    try:
        # ========================================
        # 1. 일사량 레지스터 읽기
        # ========================================
        # 예시 1: 16-bit 단일 레지스터 (0.1 W/m² 단위)
        regs = read_modbus_registers(client, 0x0000, 1)
        if not regs:
            return None
        
        irradiance = regs[0] / 10.0  # 스케일 팩터: 10
        
        # 예시 2: 32-bit 두 레지스터 (1 W/m² 단위)
        # regs = read_modbus_registers(client, 0x0000, 2)
        # if not regs:
        #     return None
        # irradiance = (regs[0] << 16) | regs[1]  # 32-bit 결합
        
        # ========================================
        # 2. 범위 검증 (0 ~ 2000 W/m²)
        # ========================================
        if irradiance < 0 or irradiance > 2000:
            log.warning(f"⚠️  Invalid irradiance value: {irradiance} W/m²")
            irradiance = max(0, min(2000, irradiance))  # 클리핑
        
        # ========================================
        # 3. 결과 데이터 구성
        # ========================================
        data = {
            'device_id': SOLAR_DEVICE,
            'timestamp': datetime.now(timezone.utc),
            'irradiance_w_per_m2': round(irradiance, 1)
        }
        
        return data
        
    except Exception as e:
        log.error(f"❌ Failed to read solar sensor: {e}")
        return None


# ========================================
# 5초 데이터 수집 (메모리 버퍼)
# ========================================
def collect_5s_data(client: ModbusSerialClient):
    """
    Solar 디바이스의 5초 데이터를 읽어 메모리 버퍼에 저장
    
    Args:
        client: Modbus 클라이언트
    
    동작:
        1. 일사량 데이터 읽기
        2. 메모리 버퍼에 추가 (DB 저장 안함)
        3. 실시간 API에서 이 버퍼를 읽어서 제공
    """
    data = read_solar_sensor_data(client)
    
    if data:
        data_buffer.append(data)
        
        log.debug(
            f"📥 Solar: "
            f"일사량={data['irradiance_w_per_m2']:.1f}W/m²"
        )
    else:
        log.warning(f"⚠️  Solar: 데이터 읽기 실패")


# ========================================
# 1분마다 평균 계산 및 DB 저장
# ========================================
def flush_1m_aggregation():
    """
    1분마다 버퍼의 5초 데이터를 평균 계산하여 1분 테이블에 저장
    
    동작:
        dummy_solar_collector.py의 flush_1m_aggregation()과 동일
        실제 장치에서 읽은 데이터를 집계하여 DB에 저장
    """
    global data_buffer
    
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    
    log.info(f"\n⏰ 1분 집계 시작: {now.isoformat()}")
    
    try:
        if not data_buffer:
            log.warning(f"  ⚠️  Solar: 버퍼 데이터 없음")
            return
        
        # 집계 계산
        irradiances = [r['irradiance_w_per_m2'] for r in data_buffer]
        
        avg_irradiance = statistics.mean(irradiances)
        max_irradiance = max(irradiances)
        min_irradiance = min(irradiances)
        
        count = len(data_buffer)
        
        # DB INSERT
        with get_cursor() as cur:
            cur.execute(f"""
                INSERT INTO solar_data_{SOLAR_DEVICE}_1m (
                    time_bucket,
                    avg_irradiance_w_per_m2,
                    max_irradiance_w_per_m2,
                    min_irradiance_w_per_m2,
                    count
                ) VALUES (
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (time_bucket) DO UPDATE SET
                    avg_irradiance_w_per_m2 = EXCLUDED.avg_irradiance_w_per_m2,
                    max_irradiance_w_per_m2 = EXCLUDED.max_irradiance_w_per_m2,
                    min_irradiance_w_per_m2 = EXCLUDED.min_irradiance_w_per_m2,
                    count = EXCLUDED.count;
            """, (
                now, avg_irradiance, max_irradiance, min_irradiance, count
            ))
        
        log.info(
            f"  ✅ Solar 1분 집계 저장: "
            f"평균={avg_irradiance:.1f}W/m²({min_irradiance:.1f}-{max_irradiance:.1f}), "
            f"samples={count}"
        )
        
    except Exception as e:
        log.error(f"  ❌ Solar 1분 집계 실패: {e}")
    
    # 버퍼 클리어
    data_buffer.clear()
    log.info("🧹 버퍼 클리어 완료\n")


# ========================================
# 메인 실행 루프
# ========================================
def run():
    """
    Solar Reader 메인 루프
    
    동작:
        1. Modbus 클라이언트 초기화
        2. 5초마다 데이터 수집 (메모리 버퍼)
        3. 1분마다 집계 및 DB 저장
        4. Ctrl+C로 종료 시 정상 종료
    """
    global modbus_client
    
    log.info("=" * 60)
    log.info("🔌 Solar Reader 시작")
    log.info(f"   Port: {settings.SOLAR_PORT}")
    log.info(f"   Baudrate: {settings.SOLAR_BAUDRATE}")
    log.info(f"   Device: {SOLAR_DEVICE}")
    log.info("=" * 60)
    
    # Modbus 클라이언트 초기화
    modbus_client = init_modbus_client()
    if not modbus_client:
        log.error("❌ Modbus 클라이언트 초기화 실패. 종료합니다.")
        return
    
    # 마지막 집계 시각
    last_flush_minute = datetime.now(timezone.utc).minute
    
    try:
        while True:
            # 5초 데이터 수집
            collect_5s_data(modbus_client)
            
            # 1분 경과 확인
            current_minute = datetime.now(timezone.utc).minute
            if current_minute != last_flush_minute:
                flush_1m_aggregation()
                last_flush_minute = current_minute
            
            # 5초 대기
            time.sleep(COLLECTION_INTERVAL)
            
    except KeyboardInterrupt:
        log.info("\n🛑 Solar Reader 종료 (사용자 요청)")
    except Exception as e:
        log.exception(f"❌ Solar Reader 오류: {e}")
    finally:
        if modbus_client:
            modbus_client.close()
            log.info("🔌 Modbus 연결 종료")


if __name__ == "__main__":
    """
    직접 실행 시 Solar 리더 시작
    
    사용법:
        python -m src.collectors.solar_reader
    
    요구사항:
        pip install pymodbus
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run()
