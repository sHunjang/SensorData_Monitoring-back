"""
데이터베이스 연결 클라이언트 모듈

주요 기능:
- PostgreSQL 연결 관리
- Context manager를 통한 안전한 커서 사용
- 트랜잭션 관리 (commit/rollback)
- 더미 모드에서만 DummyCursor 사용
- 배치 INSERT 지원

사용법:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM table")
        results = cur.fetchall()
"""

import logging
import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import execute_values
from src.config.settings import settings

log = logging.getLogger("db.client")


@contextmanager
def get_cursor():
    """
    PostgreSQL 커서를 Context Manager로 제공
    
    - 실제 PostgreSQL 연결 우선
    - 연결 실패시 에러 상세 로깅
    - MODE=dummy일 때만 DummyCursor 사용
    - 자동 commit/rollback 처리
    
    사용예:
        with get_cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
    """
    # 1. PostgreSQL DSN 확인
    dsn = getattr(settings, "PG_DSN", None)
    if not dsn:
        log.error("❌ PG_DSN not configured in settings!")
        raise ValueError("PG_DSN not configured in settings")
    
    log.debug(f"🔌 Attempting DB connection to: {dsn}")
    
    # 2. 실제 PostgreSQL 연결 시도
    try:
        # PostgreSQL 연결
        conn = psycopg2.connect(dsn)
        conn.autocommit = False  # 트랜잭션 관리 활성화
        cur = conn.cursor()
        
        log.debug("✅ PostgreSQL connection established")
        
        try:
            # 커서 제공
            yield cur
            # 성공시 커밋
            conn.commit()
            log.debug("✅ Transaction committed")
            
        except Exception as e:
            # 오류시 롤백
            conn.rollback()
            log.error(f"❌ Transaction rolled back: {e}")
            raise
            
        finally:
            # 리소스 정리
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
                
    except psycopg2.OperationalError as e:
        # DB 연결 실패 상세 로깅
        log.error(f"❌ PostgreSQL connection failed: {e}")
        log.error(f"   DSN: {dsn}")
        
        # 3. MODE=dummy일 때만 DummyCursor로 전환
        if getattr(settings, "MODE", "real").lower() == "dummy":
            log.warning("🎭 Falling back to DummyCursor due to dummy MODE")
            
            class DummyCursor:
                """더미 커서 - 실제 DB 작업 없이 로깅만"""
                
                def execute(self, *args, **kwargs):
                    """SQL 실행 시뮬레이션"""
                    try:
                        sql = args[0] if args else "Unknown SQL"
                        log.info(f"🎭 DummyCursor.execute: {sql[:100]}...")
                    except Exception:
                        log.info("🎭 DummyCursor.execute called")
                
                def executemany(self, *args, **kwargs):
                    """배치 SQL 실행 시뮬레이션"""
                    log.info("🎭 DummyCursor.executemany called")
                
                def fetchone(self):
                    """단일 row 반환 시뮬레이션"""
                    return None
                
                def fetchall(self):
                    """전체 rows 반환 시뮬레이션"""
                    return []
                
                def close(self):
                    """커서 닫기 시뮬레이션"""
                    pass
            
            try:
                yield DummyCursor()
            finally:
                pass  # 더미에서는 정리할 것 없음
        else:
            # 실제 모드에서는 연결 실패시 예외 발생
            log.error("🚨 Real mode requires working PostgreSQL connection!")
            raise
    
    except Exception as e:
        log.error(f"❌ Unexpected database error: {e}")
        raise


def get_connection():
    """
    순수 PostgreSQL 연결 객체 반환 (고급 사용시)
    
    Returns:
        psycopg2.connection: PostgreSQL 연결 객체
    """
    dsn = getattr(settings, "PG_DSN", None)
    if not dsn:
        raise ValueError("PG_DSN not configured in settings")
    
    return psycopg2.connect(dsn)


def batch_insert_modbus_rows(conn, rows):
    """
    Modbus 데이터 배치 삽입
    
    Args:
        conn: PostgreSQL 연결 객체
        rows: 삽입할 데이터 튜플 리스트
        
    배치 성능 최적화를 위한 execute_values 사용
    """
    if not rows:
        return
    
    # 🔥 새 스키마에 맞춘 SQL (modbus_data 테이블)
    sql = """
        INSERT INTO modbus_data (
            time_stamp, device_id, 
            avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
            sum_line_currents_a, total_active_power_kw,
            total_reactive_power_kvar, total_apparent_power_kva,
            total_power_factor, total_active_energy_kwh
        ) VALUES %s
    """
    
    try:
        execute_values(conn.cursor(), sql, rows, page_size=100)
        conn.commit()
        log.info(f"✅ Batch inserted {len(rows)} modbus records")
        
    except Exception:
        log.exception("❌ batch_insert_modbus_rows failed")
        conn.rollback()
        raise
