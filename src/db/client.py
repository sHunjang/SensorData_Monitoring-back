"""
PostgreSQL 연결 관리
"""

import psycopg2
from contextlib import contextmanager
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