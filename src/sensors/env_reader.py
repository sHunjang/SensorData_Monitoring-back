"""
환경(온습도) 센서 통신 모듈

이 모듈은 실제 Modbus RTU 프로토콜을 통해 온습도 센서와 통신하여
환경 데이터를 읽어옵니다.

주요 기능:
    1. Modbus RTU 시리얼 통신
    2. 온도/습도 센서 데이터 읽기
    3. 5초 주기 데이터 수집
    4. 메모리 버퍼 관리
    5. 1분마다 자동 집계 및 DB 저장

하드웨어 구성:
    - 센서: Modbus RTU (RS485)
    - 통신 방식: Serial (TTL/RS485 변환기 사용)
    - 보드레이트: 9600 (기본값)

Modbus 레지스터 맵 (예시):
    - 온도: 0x0000 (0.1°C 단위)
    - 습도: 0x0001 (0.1% 단위)

사용법:
    python -m src.collectors.env_reader

작성일: 2025-10-10
"""

import time
import logging
import statistics
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Optional

try:
    from pymodbus.client import ModbusSerialClient
    from pymodbus.exceptions import ModbusException
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False
    logging.warning("⚠️  pymodbus not installed. Install with: pip install pymodbus")

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("env_reader")

# ========================================
# 전역 변수
# ========================================
ENV_DEVICES = settings.ENV_IDS
COLLECTION_INTERVAL = settings.COLLECTION_INTERVAL  # 5초

# 메모리 버퍼: device_id별로 5초 데이터를 1분간 누적
data_buffer: Dict[int, List[dict]] = defaultdict(list)

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
        - port: settings.ENV_PORT (예: /dev/ttyUSB1)
        - baudrate: settings.ENV_BAUDRATE (기본: 9600)
        - timeout: settings.ENV_TIMEOUT (기본: 1.0초)
    """
    if not MODBUS_AVAILABLE:
        log.error("❌ pymodbus not available")
        return None
    
    try:
        client = ModbusSerialClient(
            port=settings.ENV_PORT,
            baudrate=settings.ENV_BAUDRATE,
            timeout=settings.ENV_TIMEOUT,
            bytesize=8,
            parity='N',
            stopbits=1
        )
        
        if client.connect():
            log.info(f"✅ Env Modbus client connected: {settings.ENV_PORT}")
            return client
        else:
            log.error(f"❌ Env Modbus connection failed: {settings.ENV_PORT}")
            return None
            
    except Exception as e:
        log.exception(f"❌ Env Modbus client initialization failed: {e}")
        return None


# ========================================
# Modbus 레지스터 읽기
# ========================================
def read_modbus_registers(
    client: ModbusSerialClient,
    device_id: int,
    address: int,
    count: int
) -> Optional[List[int]]:
    """
    Modbus 홀딩 레지스터 읽기
    
    Args:
        client: Modbus 클라이언트
        device_id: 슬레이브 디바이스 ID (21-23)
        address: 시작 레지스터 주소
        count: 읽을 레지스터 개수
    
    Returns:
        Optional[List[int]]: 레지스터 값 리스트 또는 None (실패 시)
    """
    try:
        response = client.read_holding_registers(
            address=address,
            count=count,
            slave=device_id
        )
        
        if response.isError():
            log.error(f"❌ Modbus read error: device={device_id}, addr={address}")
            return None
        
        return response.registers
        
    except ModbusException as e:
        log.error(f"❌ Modbus exception: device={device_id}, {e}")
        return None
    except Exception as e:
        log.error(f"❌ Unexpected error: device={device_id}, {e}")
        return None


# ========================================
# 온습도 센서 데이터 읽기
# ========================================
def read_env_sensor_data(client: ModbusSerialClient, device_id: int) -> Optional[dict]:
    """
    온습도 센서에서 환경 데이터 읽기
    
    Args:
        client: Modbus 클라이언트
        device_id: 디바이스 ID (21-23)
    
    Returns:
        Optional[dict]: 환경 데이터 또는 None (실패 시)
            {
                'device_id': int,
                'timestamp': datetime,
                'temperature_c': float,      # 온도 (섭씨)
                'humidity_percent': float    # 습도 (%)
            }
    
    레지스터 맵 (예시 - 실제 센서 매뉴얼 참고):
        0x0000: 온도 (0.1°C 단위, signed)
        0x0001: 습도 (0.1% 단위)
    
    주의:
        - 레지스터 주소는 센서 모델마다 다를 수 있음
        - 스케일 팩터는 매뉴얼 참고
    """
    try:
        # ========================================
        # 1. 온도/습도 레지스터 읽기 (2개)
        # ========================================
        regs = read_modbus_registers(client, device_id, 0x0000, 2)
        if not regs:
            return None
        
        # ========================================
        # 2. 온도 변환 (signed 16-bit)
        # ========================================
        # 음수 처리: 0x8000 이상이면 음수로 변환
        temp_raw = regs[0]
        if temp_raw >= 0x8000:
            temp_raw = temp_raw - 0x10000  # 2의 보수 변환
        
        temperature_c = temp_raw / 10.0  # 스케일 팩터: 10
        
        # ========================================
        # 3. 습도 변환 (unsigned 16-bit)
        # ========================================
        humidity_percent = regs[1] / 10.0  # 스케일 팩터: 10
        
        # ========================================
        # 4. 결과 데이터 구성
        # ========================================
        data = {
            'device_id': device_id,
            'timestamp': datetime.now(timezone.utc),
            'temperature_c': round(temperature_c, 1),
            'humidity_percent': round(humidity_percent, 1)
        }
        
        return data
        
    except Exception as e:
        log.error(f"❌ Failed to read env sensor {device_id}: {e}")
        return None


# ========================================
# 5초 데이터 수집 (메모리 버퍼)
# ========================================
def collect_5s_data(client: ModbusSerialClient):
    """
    모든 Env 디바이스의 5초 데이터를 읽어 메모리 버퍼에 저장
    
    Args:
        client: Modbus 클라이언트
    
    동작:
        1. 각 device_id에 대해 온습도 데이터 읽기
        2. 메모리 버퍼에 추가 (DB 저장 안함)
        3. 실시간 API에서 이 버퍼를 읽어서 제공
    """
    for device_id in ENV_DEVICES:
        data = read_env_sensor_data(client, device_id)
        
        if data:
            data_buffer[device_id].append(data)
            
            log.debug(
                f"📥 Device {device_id}: "
                f"온도={data['temperature_c']:.1f}°C, "
                f"습도={data['humidity_percent']:.1f}%"
            )
        else:
            log.warning(f"⚠️  Device {device_id}: 데이터 읽기 실패")


# ========================================
# 1분마다 평균 계산 및 DB 저장
# ========================================
def flush_1m_aggregation():
    """
    1분마다 버퍼의 5초 데이터를 평균 계산하여 1분 테이블에 저장
    
    동작:
        dummy_env_collector.py의 flush_1m_aggregation()과 동일
        실제 장치에서 읽은 데이터를 집계하여 DB에 저장
    """
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    
    log.info(f"\n⏰ 1분 집계 시작: {now.isoformat()}")
    
    for device_id in ENV_DEVICES:
        try:
            rows = data_buffer[device_id]
            
            if not rows:
                log.warning(f"  ⚠️  Device {device_id}: 버퍼 데이터 없음")
                continue
            
            # 집계 계산
            temps = [r['temperature_c'] for r in rows]
            humids = [r['humidity_percent'] for r in rows]
            
            avg_temp = statistics.mean(temps)
            max_temp = max(temps)
            min_temp = min(temps)
            
            avg_humid = statistics.mean(humids)
            max_humid = max(humids)
            min_humid = min(humids)
            
            count = len(rows)
            
            # DB INSERT
            with get_cursor() as cur:
                cur.execute(f"""
                    INSERT INTO env_data_{device_id}_1m (
                        time_bucket,
                        avg_temperature_c,
                        max_temperature_c,
                        min_temperature_c,
                        avg_humidity_percent,
                        max_humidity_percent,
                        min_humidity_percent,
                        count
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (time_bucket) DO UPDATE SET
                        avg_temperature_c = EXCLUDED.avg_temperature_c,
                        max_temperature_c = EXCLUDED.max_temperature_c,
                        min_temperature_c = EXCLUDED.min_temperature_c,
                        avg_humidity_percent = EXCLUDED.avg_humidity_percent,
                        max_humidity_percent = EXCLUDED.max_humidity_percent,
                        min_humidity_percent = EXCLUDED.min_humidity_percent,
                        count = EXCLUDED.count;
                """, (
                    now, avg_temp, max_temp, min_temp,
                    avg_humid, max_humid, min_humid, count
                ))
            
            log.info(
                f"  ✅ Device {device_id} 1분 집계 저장: "
                f"온도={avg_temp:.1f}°C({min_temp:.1f}-{max_temp:.1f}), "
                f"습도={avg_humid:.1f}%({min_humid:.1f}-{max_humid:.1f}), "
                f"samples={count}"
            )
            
        except Exception as e:
            log.error(f"  ❌ Device {device_id} 1분 집계 실패: {e}")
    
    # 버퍼 클리어
    data_buffer.clear()
    log.info("🧹 버퍼 클리어 완료\n")


# ========================================
# 메인 실행 루프
# ========================================
def run():
    """
    Env Reader 메인 루프
    
    동작:
        1. Modbus 클라이언트 초기화
        2. 5초마다 데이터 수집 (메모리 버퍼)
        3. 1분마다 집계 및 DB 저장
        4. Ctrl+C로 종료 시 정상 종료
    """
    global modbus_client
    
    log.info("=" * 60)
    log.info("🔌 Env Reader 시작")
    log.info(f"   Port: {settings.ENV_PORT}")
    log.info(f"   Baudrate: {settings.ENV_BAUDRATE}")
    log.info(f"   Devices: {ENV_DEVICES}")
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
        log.info("\n🛑 Env Reader 종료 (사용자 요청)")
    except Exception as e:
        log.exception(f"❌ Env Reader 오류: {e}")
    finally:
        if modbus_client:
            modbus_client.close()
            log.info("🔌 Modbus 연결 종료")


if __name__ == "__main__":
    """
    직접 실행 시 Env 리더 시작
    
    사용법:
        python -m src.collectors.env_reader
    
    요구사항:
        pip install pymodbus
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run()
