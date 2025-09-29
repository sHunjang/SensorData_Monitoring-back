"""
더미 Modbus 수집기 모듈

주요 기능:
- TAC4300 전력계 시뮬레이션
- 3선식(3W)/4선식(4W) 전력계 구분
- 랜덤 전력 데이터 생성
- 실시간 DB 저장
- 주기적 데이터 수집 (설정 가능)

테스트용 더미 데이터:
- 3선식 (11,12,13): Line-to-Line 전압 (200-240V)
- 4선식 (14,15): Line-to-Neutral 전압 (110-140V)
- 전류, 전력, 에너지 시뮬레이션

사용법:
    python -m src.collectors.dummy_modbus_collector
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

# 설정값
KST = ZoneInfo("Asia/Seoul")

# 디바이스 ID 설정 (환경변수 또는 기본값)
DEVICE_IDS: List[int] = getattr(settings, "MODBUS_DEVICE_IDS", [11, 12, 13, 14, 15]) or [11, 12, 13, 14, 15]
POLL_INTERVAL: int = getattr(settings, "MODBUS_POLL_INTERVAL", 3)
MAX_FAILS: int = getattr(settings, "MODBUS_MAX_FAILS", 3)


def ensure_table():
    """
    더미용 modbus_data 테이블 생성
    
    🎯 새 스키마에 맞춘 테이블명 사용 (modbus_data)
    bootstrap.py와 동일한 구조 유지
    """
    with get_cursor() as cur:
        # 새 스키마에 맞춘 테이블 생성
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                avg_line_to_line_volts_v DOUBLE PRECISION,
                avg_line_to_neutral_volts_v DOUBLE PRECISION,
                sum_line_currents_a DOUBLE PRECISION,
                total_active_power_kw DOUBLE PRECISION,
                total_reactive_power_kvar DOUBLE PRECISION,
                total_apparent_power_kva DOUBLE PRECISION,
                total_power_factor DOUBLE PRECISION,
                total_active_energy_kwh DOUBLE PRECISION,
                total_reactive_energy_kvarh DOUBLE PRECISION,
                total_apparent_energy_kvah DOUBLE PRECISION
            )
        """)


def make_row_for_device(device_id: int) -> Dict:
    """
    디바이스별 더미 데이터 생성
    
    Args:
        device_id: 디바이스 ID (11-15)
        
    Returns:
        dict: 전력 데이터 행
        
    구분:
        - 3선식 (11,12,13): Line-to-Line 전압
        - 4선식 (14,15): Line-to-Neutral 전압
    """
    # 3선식/4선식 구분 (settings에서 읽기)
    ids_3w = getattr(settings, "MODBUS_3W_IDS", [11, 12, 13]) or [11, 12, 13]
    ids_4w = getattr(settings, "MODBUS_4W_IDS", [14, 15]) or [14, 15]
    
    is_3w = device_id in ids_3w
    
    # 시뮬레이션 데이터 생성
    row = {
        "time_stamp": datetime.now(KST),
        "device_id": device_id,
        
        # 🔥 3선식: Line-to-Line, 4선식: Line-to-Neutral
        "avg_line_to_line_volts_v": round(random.uniform(200, 240), 2) if is_3w else None,
        "avg_line_to_neutral_volts_v": round(random.uniform(110, 140), 2) if not is_3w else None,
        
        # 공통 데이터
        "sum_line_currents_a": round(random.uniform(0, 50), 2),
        "total_active_power_kw": round(random.uniform(0, 10), 3),
        "total_reactive_power_kvar": round(random.uniform(-5, 5), 3),
        "total_apparent_power_kva": round(random.uniform(0, 12), 3),
        "total_power_factor": round(random.uniform(0.6, 1.0), 3),
        "total_active_energy_kwh": round(random.uniform(0, 1000), 3),
        "total_reactive_energy_kvarh": round(random.uniform(0, 500), 3),
        "total_apparent_energy_kvah": round(random.uniform(0, 1200), 3),
    }
    
    return row


def insert_row(row: Dict):
    """
    데이터베이스에 행 삽입
    
    Args:
        row: 삽입할 데이터 딕셔너리
        
    🎯 새 스키마 테이블명과 컬럼명 사용
    """
    with get_cursor() as cur:
        # 새 스키마에 맞춘 INSERT
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


def run_collector(interval: Optional[int] = None, device_ids: Optional[List[int]] = None):
    """
    더미 Modbus 수집기 메인 루프
    
    Args:
        interval: 수집 주기 (초), 기본값은 설정에서 읽기
        device_ids: 수집할 디바이스 ID 목록, 기본값은 설정에서 읽기
        
    동작:
        1. 테이블 생성 확인
        2. 디바이스별 순환 수집
        3. 더미 데이터 생성 및 DB 저장
        4. 주기적 반복
    """
    # 파라미터 기본값 설정
    interval = interval if interval is not None else POLL_INTERVAL
    devices = device_ids if device_ids is not None else DEVICE_IDS
    
    # 테이블 생성 확인
    ensure_table()
    
    log.info(f"🎭 Dummy Modbus started: interval={interval}s devices={devices}")
    
    # 디바이스 순환 인덱스
    idx = 0
    
    try:
        while True:
            try:
                # 순환 방식으로 디바이스 선택
                dev = devices[idx % len(devices)]
                
                # 더미 데이터 생성
                row = make_row_for_device(dev)
                
                # DB 저장
                insert_row(row)
                
                # 성공 로깅
                log.info(f"🔌 dummy_modbus: id={dev} P={row['total_active_power_kw']:.3f}kW E={row['total_active_energy_kwh']:.3f}kWh")
                
                # 다음 디바이스로
                idx += 1
                
            except Exception as e:
                log.exception(f"❌ dummy_modbus insert failed: {e}")
            
            # 수집 주기 대기
            time.sleep(interval)
            
    except KeyboardInterrupt:
        log.info("🛑 Dummy Modbus collector stopped by user")
    except Exception as e:
        log.exception(f"❌ Dummy Modbus collector fatal error: {e}")


if __name__ == "__main__":
    # 직접 실행시 로깅 설정
    logging.basicConfig(level=logging.INFO)
    run_collector()
