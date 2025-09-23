import time, random, datetime, logging
from src.db.client import get_cursor
log = logging.getLogger("dummy_modbus")
DEVS = [11,12,13,14,15]
def ensure_table():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data(
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
        );
        """)
def insert_row(dev: int):
    now = datetime.datetime.utcnow()
    row = dict(
        v_ll=round(random.uniform(370,400),1), v_ln=round(random.uniform(210,230),1),
        i_sum=round(random.uniform(10,100),2),
        p=round(random.uniform(5,50),2), q=round(random.uniform(0,20),2), s=round(random.uniform(5,60),2),
        pf=round(random.uniform(0.7,1.0),3),
        kwh=round(random.uniform(1000,5000),2), kvarh=round(random.uniform(500,2000),2), kvah=round(random.uniform(1500,6000),2),
    )
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO modbus_data(
                time_stamp,device_id,
                avg_line_to_line_volts_v,
                avg_line_to_neutral_volts_v,
                sum_line_currents_a,
                total_active_power_kw,
                total_reactive_power_kvar,
                total_apparent_power_kva,
                total_power_factor,
                total_active_energy_kwh,
                total_reactive_energy_kvarh,
                total_apparent_energy_kvah)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (now,dev,row["v_ll"],row["v_ln"],row["i_sum"],row["p"],row["q"],row["s"],row["pf"],row["kwh"],row["kvarh"],row["kvah"]))

def run_collector(interval=60):
    ensure_table(); log.info("Dummy Modbus started interval=%s", interval)
    while True:
        for d in DEVS:
            try: insert_row(d)
            except Exception as e: log.exception("modbus fail dev=%s: %s", d, e)
        time.sleep(interval)
