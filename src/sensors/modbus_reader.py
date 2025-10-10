"""
Modbus 장치 통신 모듈

이 모듈은 실제 Modbus RTU 프로토콜을 통해 전력계와 통신하여
전력 데이터를 읽어옵니다.

주요 기능:
    1. Modbus RTU 시리얼 통신
    2. 3상 4선/3선 전력계 데이터 읽기
    3. 5초 주기 데이터 수집
    4. 메모리 버퍼 관리
    5. 1분마다 자동 집계 및 DB 저장

하드웨어 구성:
    - 전력계: Modbus RTU (RS485)
    - 통신 방식: Serial (TTL/RS485 변환기 사용)
    - 보드레이트: 9600 (기본값)
    - 데이터 비트: 8
    - 패리티: None
    - 스톱 비트: 1

Modbus 레지스터 맵:
    - 전압: 0x0000-0x0003
    - 전류: 0x0008-0x000B
    - 전력: 0x0012-0x0015
    - 역률: 0x001E
    - 전력량: 0x0100-0x0103

사용법:
    python -m src.collectors.modbus_reader

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

log = logging.getLogger("modbus_reader")

# ========================================
# 전역 변수
# ========================================
MODBUS_DEVICES = settings.MODBUS_3W_IDS
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
        - port: settings.MODBUS_PORT (예: /dev/ttyUSB0)
        - baudrate: settings.MODBUS_BAUDRATE (기본: 9600)
        - timeout: settings.MODBUS_TIMEOUT (기본: 1.0초)
        - bytesize: 8
        - parity: N (None)
        - stopbits: 1
    
    예외 처리:
        연결 실패 시 None 반환 및 로그 기록
    """
    if not MODBUS_AVAILABLE:
        log.error("❌ pymodbus not available")
        return None
    
    try:
        client = ModbusSerialClient(
            port=settings.MODBUS_PORT,
            baudrate=settings.MODBUS_BAUDRATE,
            timeout=settings.MODBUS_TIMEOUT,
            bytesize=8,
            parity='N',
            stopbits=1
        )
        
        if client.connect():
            log.info(f"✅ Modbus client connected: {settings.MODBUS_PORT}")
            return client
        else:
            log.error(f"❌ Modbus connection failed: {settings.MODBUS_PORT}")
            return None
            
    except Exception as e:
        log.exception(f"❌ Modbus client initialization failed: {e}")
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
        device_id: 슬레이브 디바이스 ID (11-15)
        address: 시작 레지스터 주소
        count: 읽을 레지스터 개수
    
    Returns:
        Optional[List[int]]: 레지스터 값 리스트 또는 None (실패 시)
    
    예외 처리:
        - 통신 오류: None 반환 및 로그 기록
        - 타임아웃: None 반환
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
# 전력계 데이터 읽기
# ========================================
def read_power_meter_data(client: ModbusSerialClient, device_id: int) -> Optional[dict]:
    """
    전력계에서 전력 데이터 읽기
    
    Args:
        client: Modbus 클라이언트
        device_id: 디바이스 ID (11-15)
    
    Returns:
        Optional[dict]: 전력 데이터 또는 None (실패 시)
            {
                'device_id': int,
                'timestamp': datetime,
                'avg_line_to_line_volts_v': float,
                'avg_line_to_neutral_volts_v': float,  # 3상 4선만
                'sum_line_currents_a': float,
                'total_active_power_kw': float,
                'total_reactive_power_kvar': float,
                'total_apparent_power_kva': float,
                'total_power_factor': float,
                'total_active_energy_kwh': float,
            }
    
    레지스터 맵 (예시 - 실제 전력계 매뉴얼 참고):
        0x0000: 선간 전압 평균 (V × 10)
        0x0001: 상전압 평균 (V × 10) - 3상 4선만
        0x0008: 총 전류 (A × 100)
        0x0012: 유효 전력 (kW × 100)
        0x0013: 무효 전력 (kvar × 100)
        0x0014: 피상 전력 (kVA × 100)
        0x001E: 역률 (× 1000)
        0x0100: 누적 전력량 상위 (kWh)
        0x0101: 누적 전력량 하위 (kWh)
    
    주의:
        - 레지스터 주소는 전력계 모델마다 다를 수 있음
        - 스케일 팩터는 매뉴얼 참고
    """
    try:
        # ========================================
        # 1. 전압 읽기 (선간 전압)
        # ========================================
        voltage_regs = read_modbus_registers(client, device_id, 0x0000, 1)
        if not voltage_regs:
            return None
        line_to_line_v = voltage_regs[0] / 10.0  # 스케일 팩터: 10
        
        # ========================================
        # 2. 상전압 읽기 (3상 4선만)
        # ========================================
        line_to_neutral_v = None
        if device_id in settings.THREE_PHASE_FOUR_WIRE_IDS:
            neutral_regs = read_modbus_registers(client, device_id, 0x0001, 1)
            if neutral_regs:
                line_to_neutral_v = neutral_regs[0] / 10.0
        
        # ========================================
        # 3. 전류 읽기
        # ========================================
        current_regs = read_modbus_registers(client, device_id, 0x0008, 1)
        if not current_regs:
            return None
        current_a = current_regs[0] / 100.0  # 스케일 팩터: 100
        
        # ========================================
        # 4. 전력 읽기 (유효, 무효, 피상)
        # ========================================
        power_regs = read_modbus_registers(client, device_id, 0x0012, 3)
        if not power_regs:
            return None
        active_kw = power_regs[0] / 100.0
        reactive_kvar = power_regs[1] / 100.0
        apparent_kva = power_regs[2] / 100.0
        
        # ========================================
        # 5. 역률 읽기
        # ========================================
        pf_regs = read_modbus_registers(client, device_id, 0x001E, 1)
        if not pf_regs:
            return None
        power_factor = pf_regs[0] / 1000.0  # 스케일 팩터: 1000
        
        # ========================================
        # 6. 누적 전력량 읽기 (32비트: 상위+하위)
        # ========================================
        energy_regs = read_modbus_registers(client, device_id, 0x0100, 2)
        if not energy_regs:
            return None
        # 32비트 결합: (상위 << 16) | 하위
        energy_kwh = ((energy_regs[0] << 16) | energy_regs[1]) / 100.0
        
        # ========================================
        # 7. 결과 데이터 구성
        # ========================================
        data = {
            'device_id': device_id,
            'timestamp': datetime.now(timezone.utc),
            'avg_line_to_line_volts_v': round(line_to_line_v, 2),
            'sum_line_currents_a': round(current_a, 2),
            'total_active_power_kw': round(active_kw, 2),
            'total_reactive_power_kvar': round(reactive_kvar, 2),
            'total_apparent_power_kva': round(apparent_kva, 2),
            'total_power_factor': round(power_factor, 3),
            'total_active_energy_kwh': round(energy_kwh, 2),
        }
        
        # 3상 4선인 경우 상전압 추가
        if line_to_neutral_v is not None:
            data['avg_line_to_neutral_volts_v'] = round(line_to_neutral_v, 2)
        
        return data
        
    except Exception as e:
        log.error(f"❌ Failed to read power meter {device_id}: {e}")
        return None


# ========================================
# 5초 데이터 수집 (메모리 버퍼)
# ========================================
def collect_5s_data(client: ModbusSerialClient):
    """
    모든 Modbus 디바이스의 5초 데이터를 읽어 메모리 버퍼에 저장
    
    Args:
        client: Modbus 클라이언트
    
    동작:
        1. 각 device_id에 대해 전력계 데이터 읽기
        2. 메모리 버퍼에 추가 (DB 저장 안함)
        3. 실시간 API에서 이 버퍼를 읽어서 제공
    """
    for device_id in MODBUS_DEVICES:
        data = read_power_meter_data(client, device_id)
        
        if data:
            # 메모리 버퍼에 추가
            data_buffer[device_id].append(data)
            
            log.debug(
                f"📥 Device {device_id}: "
                f"{data['total_active_power_kw']:.2f}kW, "
                f"{data['sum_line_currents_a']:.2f}A"
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
        dummy_modbus_collector.py의 flush_1m_aggregation()과 동일
        실제 장치에서 읽은 데이터를 집계하여 DB에 저장
    """
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    
    log.info(f"\n⏰ 1분 집계 시작: {now.isoformat()}")
    
    for device_id in MODBUS_DEVICES:
        try:
            rows = data_buffer[device_id]
            
            if not rows:
                log.warning(f"  ⚠️  Device {device_id}: 버퍼 데이터 없음")
                continue
            
            # 집계 계산
            avg_voltage = statistics.mean(r['avg_line_to_line_volts_v'] for r in rows)
            avg_current = statistics.mean(r['sum_line_currents_a'] for r in rows)
            avg_kw = statistics.mean(r['total_active_power_kw'] for r in rows)
            max_kw = max(r['total_active_power_kw'] for r in rows)
            min_kw = min(r['total_active_power_kw'] for r in rows)
            avg_pf = statistics.mean(r['total_power_factor'] for r in rows)
            avg_kvar = statistics.mean(r['total_reactive_power_kvar'] for r in rows)
            avg_kva = statistics.mean(r['total_apparent_power_kva'] for r in rows)
            total_kwh = rows[-1]['total_active_energy_kwh'] - rows[0]['total_active_energy_kwh']
            count = len(rows)
            
            # DB INSERT (3상 4선/3선 구분)
            if device_id in settings.THREE_PHASE_FOUR_WIRE_IDS:
                avg_voltage_n = statistics.mean(
                    r['avg_line_to_neutral_volts_v'] for r in rows
                )
                
                with get_cursor() as cur:
                    cur.execute(f"""
                        INSERT INTO modbus_data_{device_id}_1m (
                            time_bucket,
                            avg_line_to_line_volts_v,
                            avg_line_to_neutral_volts_v,
                            sum_line_currents_a,
                            avg_active_power_kw,
                            max_active_power_kw,
                            min_active_power_kw,
                            avg_reactive_power_kvar,
                            avg_apparent_power_kva,
                            avg_power_factor,
                            total_active_energy_kwh,
                            count
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (time_bucket) DO UPDATE SET
                            avg_line_to_line_volts_v = EXCLUDED.avg_line_to_line_volts_v,
                            avg_line_to_neutral_volts_v = EXCLUDED.avg_line_to_neutral_volts_v,
                            sum_line_currents_a = EXCLUDED.sum_line_currents_a,
                            avg_active_power_kw = EXCLUDED.avg_active_power_kw,
                            max_active_power_kw = EXCLUDED.max_active_power_kw,
                            min_active_power_kw = EXCLUDED.min_active_power_kw,
                            avg_power_factor = EXCLUDED.avg_power_factor,
                            count = EXCLUDED.count;
                    """, (
                        now, avg_voltage, avg_voltage_n, avg_current,
                        avg_kw, max_kw, min_kw, avg_kvar, avg_kva,
                        avg_pf, total_kwh, count
                    ))
            
            elif device_id in settings.THREE_PHASE_THREE_WIRE_IDS:
                with get_cursor() as cur:
                    cur.execute(f"""
                        INSERT INTO modbus_data_{device_id}_1m (
                            time_bucket,
                            avg_line_to_line_volts_v,
                            sum_line_currents_a,
                            avg_active_power_kw,
                            max_active_power_kw,
                            min_active_power_kw,
                            avg_reactive_power_kvar,
                            avg_apparent_power_kva,
                            avg_power_factor,
                            total_active_energy_kwh,
                            count
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (time_bucket) DO UPDATE SET
                            avg_line_to_line_volts_v = EXCLUDED.avg_line_to_line_volts_v,
                            sum_line_currents_a = EXCLUDED.sum_line_currents_a,
                            avg_active_power_kw = EXCLUDED.avg_active_power_kw,
                            max_active_power_kw = EXCLUDED.max_active_power_kw,
                            min_active_power_kw = EXCLUDED.min_active_power_kw,
                            avg_power_factor = EXCLUDED.avg_power_factor,
                            count = EXCLUDED.count;
                    """, (
                        now, avg_voltage, avg_current,
                        avg_kw, max_kw, min_kw, avg_kvar, avg_kva,
                        avg_pf, total_kwh, count
                    ))
            
            log.info(
                f"  ✅ Device {device_id} 1분 집계 저장: "
                f"avg={avg_kw:.2f}kW, max={max_kw:.2f}kW, samples={count}"
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
    Modbus 리더 메인 루프
    
    동작:
        1. Modbus 클라이언트 초기화
        2. 5초마다 데이터 수집 (메모리 버퍼)
        3. 1분마다 집계 및 DB 저장
        4. Ctrl+C로 종료 시 정상 종료
    """
    global modbus_client
    
    log.info("=" * 60)
    log.info("🔌 Modbus Reader 시작")
    log.info(f"   Port: {settings.MODBUS_PORT}")
    log.info(f"   Baudrate: {settings.MODBUS_BAUDRATE}")
    log.info(f"   Devices: {MODBUS_DEVICES}")
    log.info(f"   3상 4선: {settings.THREE_PHASE_FOUR_WIRE_IDS}")
    log.info(f"   3상 3선: {settings.THREE_PHASE_THREE_WIRE_IDS}")
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
        log.info("\n🛑 Modbus Reader 종료 (사용자 요청)")
    except Exception as e:
        log.exception(f"❌ Modbus Reader 오류: {e}")
    finally:
        if modbus_client:
            modbus_client.close()
            log.info("🔌 Modbus 연결 종료")


if __name__ == "__main__":
    """
    직접 실행 시 Modbus 리더 시작
    
    사용법:
        python -m src.collectors.modbus_reader
    
    요구사항:
        pip install pymodbus
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run()
