import psycopg2
from contextlib import contextmanager
from typing import Iterator
from src.config.settings import settings

def get_connection():
    return psycopg2.connect(settings.pg_dsn)

@contextmanager
def get_cursor():
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def ensure_tables_exist() -> None:
    """테이블이 없으면 생성 (IF NOT EXISTS)."""
    ddl = """
    CREATE TABLE IF NOT EXISTS modbus_data (
        ts TIMESTAMPTZ NOT NULL,
        avg_voltage DOUBLE PRECISION,
        sum_current DOUBLE PRECISION,
        p_total DOUBLE PRECISION,
        q_total DOUBLE PRECISION,
        s_total DOUBLE PRECISION,
        pf_total DOUBLE PRECISION,
        e_active DOUBLE PRECISION,
        e_reactive DOUBLE PRECISION,
        e_apparent DOUBLE PRECISION
    );
    """
    with get_cursor() as cur:
        cur.execute(ddl)

def insert_modbus_row(row: dict) -> None:
    """1분치 측정값을 modbus_data에 저장."""
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO modbus_data
            (ts, avg_voltage, sum_current, p_total, q_total, s_total,
             pf_total, e_active, e_reactive, e_apparent)
            VALUES (NOW(), %s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                round(row["avg_voltage_V"], 2),
                round(row["sum_current_A"], 2),
                round(row["total_active_kW"], 2),
                round(row["total_reactive_kvar"], 2),
                round(row["total_apparent_kVA"], 2),
                round(row["total_power_factor"], 2),
                round(row["total_active_energy_kWh"], 2),
                round(row["total_reactive_energy_kvarh"], 2),
                round(row["total_apparent_energy_kVAh"], 2),
            ),
        )
