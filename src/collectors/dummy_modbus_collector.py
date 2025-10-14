"""
더미 Modbus 수집기 모듈

주요 기능:
- TAC4300 전력계 시뮬레이션 (테스트용)
- 3상 4선식(4W)/3상 3선식(3W) 전력계 구분
- 현실적인 전력 데이터 생성
- 실시간 DB 저장 (modbus_data 원본 테이블)
- 주기적 데이터 수집 (기본 5초)

센서 타입별 시뮬레이션:
- 3상 4선식 (ID: 11,12,13): Line-to-Line 전압 (200-240V)
- 3상 3선식 (ID: 14,15): Line-to-Neutral 전압 (110-140V)
- 전류, 전력, 에너지(누적), 역률 등

사용법:
  python -m src.collectors.dummy_modbus_collector
  
  또는 main.py에서 자동 실행 (MODE=dummy)
"""

import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional, Dict

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("dummy_modbus")

# ============================================================
# 전역 설정
# ============================================================

KST = ZoneInfo("Asia/Seoul")

# 디바이스 ID 설정 (settings.py에서 로드)
DEVICE_IDS: List[int] = settings.MODBUS_DEVICE_IDS  # [11, 12, 13, 14, 15]
POLL_INTERVAL: int = settings.MODBUS_POLL_INTERVAL  # 5초
MAX_FAILS: int = settings.MODBUS_MAX_FAILS  # 3

# 에너지 누적값 관리 (디바이스별 상태 유지)
# 실제 전력계처럼 에너지는 계속 증가해야 함
_energy_state: Dict[int, float] = {}


# ============================================================
# 테이블 관리
# ============================================================

def ensure_table():
    """
    modbus_data 원본 테이블 생성 확인
    
    ⚠️ 주의: bootstrap.py와 동일한 스키마 사용
    - 3상 4선식 + 3상 3선식 데이터가 혼재된 테이블
    - 실제 운영에서는 bootstrap.py 실행 후 이 함수는 스킵됨 (IF NOT EXISTS)
    """
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                -- 3상 4선식 전용 (Line-to-Line)
                avg_line_to_line_volts_v DOUBLE PRECISION,
                -- 3상 3선식 전용 (Line-to-Neutral)
                avg_line_to_neutral_volts_v DOUBLE PRECISION,
                -- 공통 컬럼
                sum_line_currents_a DOUBLE PRECISION,
                total_active_power_kw DOUBLE PRECISION,
                total_reactive_power_kvar DOUBLE PRECISION,
                total_apparent_power_kva DOUBLE PRECISION,
                total_power_factor DOUBLE PRECISION,
                total_active_energy_kwh DOUBLE PRECISION,
                total_reactive_energy_kvarh DOUBLE PRECISION,
                total_apparent_energy_kvah DOUBLE PRECISION
            );
        """)
        log.debug("✅ modbus_data table ensured")


# ============================================================
# 더미 데이터 생성
# ============================================================

def make_row_for_device(device_id: int) -> Dict:
    """
    디바이스별 현실적인 더미 데이터 생성
    
    Args:
        device_id: 디바이스 ID (11~15)
        
    Returns:
        dict: 전력 데이터 행
        
    동작:
        1. 디바이스 타입 확인 (3상 4선 or 3상 3선)
        2. 타입에 맞는 전압 생성 (다른 컬럼은 NULL)
        3. 전력 데이터 시뮬레이션
        4. 에너지 누적값 계산 (계속 증가)
    """
    global _energy_state
    
    # 디바이스 타입 확인 (settings.py에서 판단)
    is_4wire = settings.is_4wire_device(device_id)  # True면 4선식 (11,12,13)
    is_3wire = settings.is_3wire_device(device_id)  # True면 3선식 (14,15)
    
    # 현재 시각
    now = datetime.now(KST)
    
    # 전력 시뮬레이션 (0~10kW 범위)
    active_power_kw = round(random.uniform(0.5, 10.0), 3)
    reactive_power_kvar = round(random.uniform(-2.0, 3.0), 3)
    apparent_power_kva = round((active_power_kw**2 + reactive_power_kvar**2)**0.5, 3)
    power_factor = round(active_power_kw / apparent_power_kva if apparent_power_kva > 0 else 0.95, 3)
    
    # 전류 계산 (P = V * I * PF * sqrt(3) 근사)
    voltage = 220.0 if is_4wire else 127.0
    current_a = round(active_power_kw * 1000 / (voltage * power_factor * 1.732), 2)
    
    # 에너지 누적 (실제 전력계처럼 계속 증가)
    if device_id not in _energy_state:
        # 초기값 설정 (0~100 kWh 랜덤 시작)
        _energy_state[device_id] = round(random.uniform(0, 100), 3)
    
    # 이전 수집 이후 누적량 추가 (P * time_interval / 3600)
    # 예: 5초마다 수집 시, 10kW면 약 0.014kWh 증가
    energy_increment = active_power_kw * (POLL_INTERVAL / 3600.0)
    _energy_state[device_id] += energy_increment
    
    total_active_energy_kwh = round(_energy_state[device_id], 3)
    
    # 무효/피상 에너지도 비례하여 증가
    total_reactive_energy_kvarh = round(total_active_energy_kwh * 0.4, 3)
    total_apparent_energy_kvah = round(total_active_energy_kwh * 1.2, 3)
    
    # 데이터 행 생성
    row = {
        "time_stamp": now,
        "device_id": device_id,
        # 전압 (타입에 따라 한 쪽만 값 입력, 나머지는 NULL)
        "avg_line_to_line_volts_v": round(random.uniform(200, 240), 2) if is_4wire else None,
        "avg_line_to_neutral_volts_v": round(random.uniform(110, 140), 2) if is_3wire else None,
        # 공통 데이터
        "sum_line_currents_a": current_a,
        "total_active_power_kw": active_power_kw,
        "total_reactive_power_kvar": reactive_power_kvar,
        "total_apparent_power_kva": apparent_power_kva,
        "total_power_factor": power_factor,
        # 에너지 (누적값)
        "total_active_energy_kwh": total_active_energy_kwh,
        "total_reactive_energy_kvarh": total_reactive_energy_kvarh,
        "total_apparent_energy_kvah": total_apparent_energy_kvah,
    }
    
    return row


# ============================================================
# 데이터베이스 저장
# ============================================================

def insert_row(row: Dict):
    """
    modbus_data 테이블에 원시 데이터 삽입
    
    Args:
        row: 삽입할 데이터 딕셔너리
        
    동작:
        - 5초마다 수집된 원시 데이터를 저장
        - 이후 별도 집계 프로세스가 이를 읽어 1분/15분/... 테이블로 집계
    """
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO modbus_data (
                time_stamp, device_id,
                avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
                sum_line_currents_a, total_active_power_kw,
                total_reactive_power_kvar, total_apparent_power_kva,
                total_power_factor, total_active_energy_kwh,
                total_reactive_energy_kvarh, total_apparent_energy_kvah
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row["time_stamp"], row["device_id"],
            row.get("avg_line_to_line_volts_v"),
            row.get("avg_line_to_neutral_volts_v"),
            row.get("sum_line_currents_a"),
            row.get("total_active_power_kw"),
            row.get("total_reactive_power_kvar"),
            row.get("total_apparent_power_kva"),
            row.get("total_power_factor"),
            row.get("total_active_energy_kwh"),
            row.get("total_reactive_energy_kvarh"),
            row.get("total_apparent_energy_kvah")
        ))


# ============================================================
# 수집기 메인 루프
# ============================================================

def run_collector(interval: Optional[int] = None, device_ids: Optional[List[int]] = None):
    """
    더미 Modbus 수집기 메인 루프
    
    Args:
        interval: 수집 주기 (초), 기본값은 settings에서 로드 (5초)
        device_ids: 수집할 디바이스 ID 목록, 기본값은 settings에서 로드
        
    동작 흐름:
        1. 테이블 생성 확인
        2. 무한 루프 시작
        3. 각 디바이스 순환하며 데이터 생성
        4. DB에 저장
        5. interval 초 대기
        6. 반복
        
    종료 조건:
        - Ctrl+C (KeyboardInterrupt)
        - 치명적 에러 발생
    """
    # 파라미터 기본값 설정
    interval = interval if interval is not None else POLL_INTERVAL
    devices = device_ids if device_ids is not None else DEVICE_IDS
    
    # 테이블 생성 확인
    try:
        ensure_table()
    except Exception as e:
        log.error(f"❌ Failed to ensure table: {e}")
        return
    
    log.info("=" * 70)
    log.info("🎭 Dummy Modbus Collector Started")
    log.info(f"   Interval: {interval}s")
    log.info(f"   Devices: {devices}")
    log.info(f"   4-Wire (Line-to-Line): {settings.MODBUS_4W_IDS}")
    log.info(f"   3-Wire (Line-to-Neutral): {settings.MODBUS_3W_IDS}")
    log.info("=" * 70)
    
    # 디바이스 순환 인덱스
    idx = 0
    fail_count = 0
    
    try:
        while True:
            try:
                # 순환 방식으로 디바이스 선택
                # 예: [11,12,13,14,15] -> 11 -> 12 -> 13 -> 14 -> 15 -> 11 -> ...
                dev = devices[idx % len(devices)]
                
                # 더미 데이터 생성
                row = make_row_for_device(dev)
                
                # DB 저장
                insert_row(row)
                
                # 성공 로깅
                wire_type = "4W" if settings.is_4wire_device(dev) else "3W"
                voltage = row.get("avg_line_to_line_volts_v") or row.get("avg_line_to_neutral_volts_v")
                
                log.info(
                    f"🔌 [{wire_type}] ID={dev:2d} | "
                    f"V={voltage:6.2f}V | "
                    f"I={row['sum_line_currents_a']:5.2f}A | "
                    f"P={row['total_active_power_kw']:6.3f}kW | "
                    f"E={row['total_active_energy_kwh']:8.3f}kWh"
                )
                
                # 실패 카운터 리셋
                fail_count = 0
                
                # 다음 디바이스로
                idx += 1
                
            except Exception as e:
                fail_count += 1
                log.error(f"❌ Insert failed (attempt {fail_count}/{MAX_FAILS}): {e}")
                
                if fail_count >= MAX_FAILS:
                    log.critical(f"🔥 Max failures reached ({MAX_FAILS}), stopping collector")
                    break
            
            # 수집 주기 대기
            time.sleep(interval)
            
    except KeyboardInterrupt:
        log.info("")
        log.info("=" * 70)
        log.info("🛑 Dummy Modbus collector stopped by user (Ctrl+C)")
        log.info("=" * 70)
        
    except Exception as e:
        log.exception(f"❌ Dummy Modbus collector fatal error: {e}")


# ============================================================
# 직접 실행
# ============================================================

if __name__ == "__main__":
    # 직접 실행 시 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    run_collector()
