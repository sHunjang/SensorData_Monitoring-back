# src/db/client.py
"""
DB 커넥션 유틸.
- 설정은 src.config.settings.settings.PG_DSN 사용.
- 일반 모드: psycopg2로 실제 Postgres 연결.
- dummy 모드: DB 연결 실패 시 파괴적이지 않게 'DummyCursor'를 반환하여 수집기 테스트 가능.
- get_cursor() 컨텍스트매니저는 자동 커밋/롤백을 처리.
"""

import logging
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import execute_values
from src.config.settings import settings

log = logging.getLogger("db.client")


@contextmanager
def get_cursor():
    """
    사용 예:
      with get_cursor() as cur:
          cur.execute("SELECT 1")
    동작:
      - 정상: psycopg2 커넥션/커서 생성, yield cursor, 커밋 또는 롤백 후 close
      - 실패: settings.MODE == 'dummy' 이면 DummyCursor 반환(실행은 로깅만 함).
              그렇지 않으면 예외를 다시 던짐.
    """
    try:
        # settings.PG_DSN 사용 (대소문자 주의)
        dsn = getattr(settings, "PG_DSN", None)
        if not dsn:
            raise ValueError("PG_DSN not configured in settings")

        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        # DB 연결 실패 처리
        log.warning("get_cursor: DB connect failed: %s", e)
        # dummy 모드면 no-op cursor 반환하여 수집기 테스트 허용
        if getattr(settings, "MODE", "real") == "dummy":
            log.info("get_cursor: falling back to DummyCursor due to dummy MODE")

            class DummyCursor:
                def execute(self, *args, **kwargs):
                    # 간단 로그: SQL만 로깅(민감정보 주의)
                    try:
                        sql = args[0] if args else None
                        log.debug("DummyCursor.execute: %s", sql)
                    except Exception:
                        log.debug("DummyCursor.execute called")
                def executemany(self, *args, **kwargs):
                    log.debug("DummyCursor.executemany")
                def fetchone(self):
                    return None
                def fetchall(self):
                    return []
                def close(self):
                    pass

            # yield the dummy cursor within the context manager
            try:
                yield DummyCursor()
            finally:
                return
        # real 모드면 예외 재발생
        raise


def get_connection():
    """
    실 DB connection이 필요한 경우 사용.
    경고: 호출자는 닫아야 함.
    """
    dsn = getattr(settings, "PG_DSN", None)
    if not dsn:
        raise ValueError("PG_DSN not configured in settings")
    return psycopg2.connect(dsn)


def batch_insert_modbus_rows(conn, rows):
    """
    배치 INSERT 유틸(예시).
    rows: list of tuples matching VALUES order in SQL.
    """
    if not rows:
        return
    sql = """
    INSERT INTO modbus_data (
      time_stamp, device_id,
      avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
      sum_line_currents_a, total_active_power_kw, total_reactive_power_kvar,
      total_apparent_power_kva, total_power_factor,
      total_active_energy_kwh
    ) VALUES %s
    """
    try:
        execute_values(conn.cursor(), sql, rows, page_size=100)
        conn.commit()
    except Exception:
        log.exception("batch_insert_modbus_rows failed")
        conn.rollback()
        raise
