"""
Modbus 수집기 (pymodbus, FC=03H)
- 3상 3선: ID 11,12,13 → 선간전압 평균(v_ll)
- 3상 4선: ID 14,15     → 상전압 평균(v_ln)
- 공통: 평균 PF, 총 P/Q/S, 전류합, 평균전류, 총 에너지(Active/Reactive/Apparent)
- 1분 주기 DB 저장
"""
import time
import logging
from pymodbus.client import ModbusSerialClient
from src.common.logging_config import setup_logging
from src.db.client import get_cursor

log = logging.getLogger("collector")

def ensure_table():
    """modbus_data 테이블 생성"""
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                avg_power_factor DOUBLE PRECISION,
                total_active_power_kW DOUBLE PRECISION,
                total_reactive_power_kvar DOUBLE PRECISION,
                total_apparent_power_kVA DOUBLE PRECISION,
                sum_line_currents_A DOUBLE PRECISION,
                avg_line_to_neutral_volts_V DOUBLE PRECISION,
                avg_line_to_line_volts_V DOUBLE PRECISION,
                avg_line_current_A DOUBLE PRECISION,
                total_active_energy_kWh DOUBLE PRECISION,
                total_reactive_energy_kvarh DOUBLE PRECISION,
                total_apparent_energy_kVAh DOUBLE PRECISION
            );
        """)

def insert_row(device_id: int, row: dict):
    """한 건 저장"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO modbus_data
            (time_stamp, device_id,
             avg_power_factor, total_active_power_kW, total_reactive_power_kvar,
             total_apparent_power_kVA, sum_line_currents_A,
             avg_line_to_neutral_volts_V, avg_line_to_line_volts_V, avg_line_current_A,
             total_active_energy_kWh, total_reactive_energy_kvarh, total_apparent_energy_kVAh)
            VALUES (NOW(), %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            device_id,
            row["pf"], row["p"], row["q"], row["s"],
            row["sum_i"], row.get("v_ln"), row.get("v_ll"), row["i_avg"],
            row["e_active"], row["e_reactive"], row["e_apparent"]
        ))

def read_u32_scaled(client: ModbusSerialClient, unit_id: int, address: int,
                    scale: float = 0.01, signed: bool = False) -> float:
    """
    32비트(2워드) Holding Register 읽기 + 스케일
    - FC=03H
    - signed=True 면 32bit 부호 처리
    """
    res = client.read_holding_registers(address=address, count=2, slave=unit_id)
    if res.isError():
        raise RuntimeError(f"응답 오류: {res}")
    raw = (res.registers[0] << 16) | res.registers[1]
    if signed and (raw & 0x80000000):
        raw -= 0x100000000
    return raw * scale

def main():
    setup_logging()
    ensure_table()
    log.info("collector start")

    # RS485 포트 설정(환경에 맞게 COM 수정)
    client = ModbusSerialClient(
        port="COM3", baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=1
    )
    if not client.connect():
        log.error("Modbus 연결 실패")
        return

    # 장치 그룹
    three_phase_3w = [11, 12, 13]  # 3상 3선
    three_phase_4w = [14, 15]      # 3상 4선

    # 공통 레지스터
    ADDR_COMMON = {
        "pf": 0x0050,    # 평균 Power Factor (×0.001)
        "p":  0x0048,    # Total Active Power kW (×0.001, signed)
        "q":  0x004A,    # Total Reactive Power kvar (×0.001, signed)
        "s":  0x004C,    # Total Apparent Power kVA (×0.001)
        "sum_i": 0x0042, # Sum of Line Currents A (×0.001)
        "i_avg": 0x0044, # Average Line Current A (×0.001)
    }
    # 전압
    ADDR_3W = {"v_ll": 0x0038}  # Average Line to Line Volts (×0.01)
    ADDR_4W = {"v_ln": 0x0036}  # Average Line to Neutral Volts (×0.01)
    # 에너지
    ADDR_EN = {
        "e_active":   0x1000,  # Total Active Energy kWh (×0.01)
        "e_reactive": 0x1002,  # Total Reactive Energy kvarh (×0.01)
        "e_apparent": 0x1004,  # Total Apparent Energy kVAh (×0.01)
    }

    while True:
        # 3상 3선
        for sid in three_phase_3w:
            try:
                row = {
                    "pf":    read_u32_scaled(client, sid, ADDR_COMMON["pf"], 0.001),
                    "p":     read_u32_scaled(client, sid, ADDR_COMMON["p"], 0.001, signed=True),
                    "q":     read_u32_scaled(client, sid, ADDR_COMMON["q"], 0.001, signed=True),
                    "s":     read_u32_scaled(client, sid, ADDR_COMMON["s"], 0.001),
                    "sum_i": read_u32_scaled(client, sid, ADDR_COMMON["sum_i"], 0.001),
                    "i_avg": read_u32_scaled(client, sid, ADDR_COMMON["i_avg"], 0.001),
                    "v_ll":  read_u32_scaled(client, sid, ADDR_3W["v_ll"], 0.01),
                    "v_ln":  None,
                    "e_active":   read_u32_scaled(client, sid, ADDR_EN["e_active"], 0.01),
                    "e_reactive": read_u32_scaled(client, sid, ADDR_EN["e_reactive"], 0.01),
                    "e_apparent": read_u32_scaled(client, sid, ADDR_EN["e_apparent"], 0.01),
                }
                insert_row(sid, row)
                log.info("3W sid=%d P=%.3f Q=%.3f S=%.3f PF=%.3f", sid, row["p"], row["q"], row["s"], row["pf"])
            except Exception as e:
                log.warning("3W sid=%d error: %s", sid, e)

        # 3상 4선
        for sid in three_phase_4w:
            try:
                row = {
                    "pf":    read_u32_scaled(client, sid, ADDR_COMMON["pf"], 0.001),
                    "p":     read_u32_scaled(client, sid, ADDR_COMMON["p"], 0.001, signed=True),
                    "q":     read_u32_scaled(client, sid, ADDR_COMMON["q"], 0.001, signed=True),
                    "s":     read_u32_scaled(client, sid, ADDR_COMMON["s"], 0.001),
                    "sum_i": read_u32_scaled(client, sid, ADDR_COMMON["sum_i"], 0.001),
                    "i_avg": read_u32_scaled(client, sid, ADDR_COMMON["i_avg"], 0.001),
                    "v_ln":  read_u32_scaled(client, sid, ADDR_4W["v_ln"], 0.01),
                    "v_ll":  None,
                    "e_active":   read_u32_scaled(client, sid, ADDR_EN["e_active"], 0.01),
                    "e_reactive": read_u32_scaled(client, sid, ADDR_EN["e_reactive"], 0.01),
                    "e_apparent": read_u32_scaled(client, sid, ADDR_EN["e_apparent"], 0.01),
                }
                insert_row(sid, row)
                log.info("4W sid=%d P=%.3f Q=%.3f S=%.3f PF=%.3f", sid, row["p"], row["q"], row["s"], row["pf"])
            except Exception as e:
                log.warning("4W sid=%d error: %s", sid, e)

        time.sleep(60)  # 수집 주기(초)

    client.close()

if __name__ == "__main__":
    main()
