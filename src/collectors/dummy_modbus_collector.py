"""
더미 Modbus 수집기 - Device별 분리 테이블 지원

기능:
- 5개 Device (11~15)를 순환하며 더미 전력 데이터 생성
- Device별 분리 테이블에 저장 (modbus_data_11 ~ modbus_data_15)
- 3초마다 랜덤 데이터 생성

작성일: 2025-10-02 (마이그레이션 대응)
"""

import os
import time
import random
import logging
from datetime import datetime, timezone
from src.db.client import get_cursor

log = logging.getLogger("dummy_modbus")

# Device ID 목록
MODBUS_DEVICE_IDS = [11, 12, 13, 14, 15]


def ensure_tables():
    """
    모든 Modbus Device별 분리 테이블 생성
    """
    log.info("📊 Modbus 분리 테이블 확인 중...")
    
    with get_cursor() as cur:
        for device_id in MODBUS_DEVICE_IDS:
            table_name = f"modbus_data_{device_id}"
            
            # 테이블 생성
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    time_stamp TIMESTAMPTZ NOT NULL,
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
            
            # 인덱스 생성
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_time 
                ON {table_name}(time_stamp DESC)
            """)
            
            log.info(f"  ✅ {table_name} 준비 완료")


def generate_dummy_data(device_id: int) -> dict:
    """
    특정 Device ID에 대한 더미 Modbus 데이터 생성
    
    Args:
        device_id: Modbus 장치 ID (11~15)
        
    Returns:
        dict: 더미 전력 데이터
    """
    # Device별로 약간 다른 값 범위 설정 (실제처럼)
    base_voltage_ll = 380 + (device_id - 11) * 2  # 380, 382, 384, 386, 388
    base_voltage_ln = 220 + (device_id - 11) * 1  # 220, 221, 222, 223, 224
    base_current = 20 + (device_id - 11) * 5      # 20, 25, 30, 35, 40
    base_power = 5 + (device_id - 11) * 2         # 5, 7, 9, 11, 13
    
    return {
        "time_stamp": datetime.now(timezone.utc),
        "avg_line_to_line_volts_v": round(random.uniform(base_voltage_ll - 5, base_voltage_ll + 5), 2),
        "avg_line_to_neutral_volts_v": round(random.uniform(base_voltage_ln - 3, base_voltage_ln + 3), 2),
        "sum_line_currents_a": round(random.uniform(base_current - 5, base_current + 5), 2),
        "total_active_power_kw": round(random.uniform(base_power - 2, base_power + 2), 3),
        "total_reactive_power_kvar": round(random.uniform(0.5, 2.5), 3),
        "total_apparent_power_kva": round(random.uniform(base_power - 1, base_power + 3), 3),
        "total_power_factor": round(random.uniform(0.85, 0.99), 3),
        "total_active_energy_kwh": round(random.uniform(500, 2000), 2),
        "total_reactive_energy_kvarh": round(random.uniform(50, 200), 2),
        "total_apparent_energy_kvah": round(random.uniform(550, 2200), 2),
    }


def save_data(device_id: int, data: dict):
    """
    Device별 분리 테이블에 데이터 저장
    
    Args:
        device_id: Modbus 장치 ID
        data: 저장할 데이터
    """
    table_name = f"modbus_data_{device_id}"
    
    with get_cursor() as cur:
        cur.execute(f"""
            INSERT INTO {table_name} (
                time_stamp,
                avg_line_to_line_volts_v,
                avg_line_to_neutral_volts_v,
                sum_line_currents_a,
                total_active_power_kw,
                total_reactive_power_kvar,
                total_apparent_power_kva,
                total_power_factor,
                total_active_energy_kwh,
                total_reactive_energy_kvarh,
                total_apparent_energy_kvah
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            data["time_stamp"],
            data["avg_line_to_line_volts_v"],
            data["avg_line_to_neutral_volts_v"],
            data["sum_line_currents_a"],
            data["total_active_power_kw"],
            data["total_reactive_power_kvar"],
            data["total_apparent_power_kva"],
            data["total_power_factor"],
            data["total_active_energy_kwh"],
            data["total_reactive_energy_kvarh"],
            data["total_apparent_energy_kvah"],
        ))


def run_collector(interval: int = 3):
    """
    더미 Modbus 수집기 메인 루프
    
    Args:
        interval: 수집 주기 (초)
    """
    log.info("🔌 더미 Modbus 수집기 시작 (Device별 분리 테이블)")
    
    # 테이블 생성
    ensure_tables()
    
    # Device 순환 인덱스
    device_index = 0
    
    while True:
        try:
            # 현재 Device 선택 (순환)
            device_id = MODBUS_DEVICE_IDS[device_index]
            
            # 더미 데이터 생성
            data = generate_dummy_data(device_id)
            
            # 저장
            save_data(device_id, data)
            
            log.info(
                f"⚡ Device {device_id}: "
                f"{data['total_active_power_kw']}kW, "
                f"{data['avg_line_to_line_volts_v']}V"
            )
            
            # 다음 Device로 이동
            device_index = (device_index + 1) % len(MODBUS_DEVICE_IDS)
            
            # 대기
            time.sleep(interval)
            
        except KeyboardInterrupt:
            log.info("🛑 더미 Modbus 수집기 종료")
            break
        except Exception as e:
            log.error(f"❌ 더미 Modbus 수집 오류: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # 수집기 실행
    run_collector(interval=3)
