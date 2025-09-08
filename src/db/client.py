"""
PostgreSQL 커넥션 헬퍼
- 매 쿼리마다 커넥션을 짧게 열고 닫아 단순화
- 컨텍스트 매니저 get_cursor() 사용
"""
import psycopg2
from contextlib import contextmanager
from src.config.settings import settings

@contextmanager
def get_cursor():
    conn = psycopg2.connect(settings.pg_dsn)
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()
