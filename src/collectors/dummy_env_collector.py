import time, random, datetime, logging
from src.db.client import get_cursor

log = logging.getLogger("dummy_env")

DEVS = [21,22,23]; i = 0

def next_dev():  # 라운드 로빈
    global i; d = DEVS[i % len(DEVS)]; i += 1; return d

def ensure_table():
    with get_cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS env_data(
            time_stamp TIMESTAMPTZ NOT NULL, device_id INT NOT NULL,
            temperature DOUBLE PRECISION, humidity DOUBLE PRECISION);""")

def insert_row():
    row = dict(time_stamp=datetime.datetime.utcnow(),
               device_id=next_dev(),
               temperature=round(random.uniform(15,32),2),
               humidity=round(random.uniform(25,70),2))
    with get_cursor() as cur:
        cur.execute("INSERT INTO env_data(time_stamp,device_id,temperature,humidity) VALUES (%s,%s,%s,%s)",
                    (row["time_stamp"],row["device_id"],row["temperature"],row["humidity"]))

def run_collector(interval=10):
    ensure_table(); log.info("Dummy Env started interval=%s", interval)
    while True:
        try: insert_row()
        except Exception as e: log.exception("env fail: %s", e)
        time.sleep(interval)
