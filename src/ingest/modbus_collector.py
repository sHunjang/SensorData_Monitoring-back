import time
import logging
from pymodbus.client import ModbusSerialClient
from src.common.logging_config import setup_logging
from src.db.client import get_cursor

log = logging.getLogger("collector")

def ensure_table():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                -- avg_power_factor DOUBLE PRECISION,
                -- total_active_power_kW DOUBLE PRECISION,
                -- total_reactive_power_kvar DOUBLE PRECISION,
                -- total_apparent_power_kVA DOUBLE PRECISION,
                -- sum_line_currents_A DOUBLE PRECISION,
                -- avg_line_to_neutral_volts_V DOUBLE PRECISION,
                -- avg_line_to_line_volts_V DOUBLE PRECISION,
                -- avg_line_current_A DOUBLE PRECISION,
                total_active_energy_kwh DOUBLE PRECISION,
                total_reactive_energy_kvarh DOUBLE PRECISION,
                total_apparent_energy_kVAh DOUBLE PRECISION
            );
        """)

def insert_row(device_id: int, row: dict):
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO modbus_data
            (time_stamp, device_id,
             total_active_energy_kwh, total_reactive_energy_kvarh, total_apparent_energy_kVAh)
            VALUES (NOW(), %s,%s,%s,%s)
        """, (
            device_id,
            row["total_active_energy_kwh"],
            row["total_reactive_energy_kvarh"],
            row["total_apparent_energy_kVAh"]
        ))

def read_u32_scaled(client, unit_id, address, scale=1.0, signed=False):
    res = client.read_holding_registers(address=address, count=2, slave=unit_id)
    if res.isError():
        raise RuntimeError(res)
    raw = (res.registers[0] << 16) | res.registers[1]
    if signed and raw & 0x80000000:
        raw -= 0x100000000
    return round(raw * scale, 3)

def main():
    setup_logging()
    ensure_table()
    log.info("collector start")

    client = ModbusSerialClient(port="COM7", baudrate=9600, bytesize=8,
                                parity="N", stopbits=1, timeout=1)
    if not client.connect():
        log.error("Modbus 연결 실패")
        return

    device_ids = [11, 12, 13, 14, 15]

    ADDR_EN = {
        "total_active_energy_kwh": 0x0404,      # LONG ×0.01
        "total_reactive_energy_kvarh": 0x040C,  # LONG ×0.01
        "total_apparent_energy_kVAh": 0x0410,   # ULONG ×0.01
    }

    while True:
        for sid in device_ids:
            try:
                row = {
                    "total_active_energy_kwh": read_u32_scaled(client, sid, ADDR_EN["total_active_energy_kwh"], 0.01, signed=True),
                    "total_reactive_energy_kvarh": read_u32_scaled(client, sid, ADDR_EN["total_reactive_energy_kvarh"], 0.01, signed=True),
                    "total_apparent_energy_kVAh": read_u32_scaled(client, sid, ADDR_EN["total_apparent_energy_kVAh"], 0.01),
                }
                insert_row(sid, row)
                log.info("sid=%d E=%.2f kWh, Q=%.2f kvarh, S=%.2f kVAh",
                         sid, row["total_active_energy_kwh"], row["total_reactive_energy_kvarh"], row["total_apparent_energy_kVAh"])
            except Exception as e:
                log.warning("sid=%d error: %s", sid, e)

        time.sleep(60)

    client.close()

if __name__ == "__main__":
    main()
