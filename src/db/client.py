"""
데이터베이스 클라이언트 유틸리티

이 모듈은 PostgreSQL 데이터베이스 연결 및 커서 관리를 제공합니다.

주요 기능:
    1. 컨텍스트 매니저를 통한 안전한 커서 관리
    2. 자동 커밋/롤백
    3. 연결 풀링 (선택적)
    4. 에러 핸들링

사용법:
    from src.db.client import get_cursor
    
    with get_cursor() as cur:
        cur.execute("SELECT * FROM table")
        rows = cur.fetchall()

작성일: 2025-10-10
"""

import logging
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config.settings import settings

log = logging.getLogger("db_client")


# ========================================
# 커서 컨텍스트 매니저
# ========================================
@contextmanager
def get_cursor(
    dict_cursor: bool = False,
    autocommit: bool = True
) -> Generator:
    """
    데이터베이스 커서 컨텍스트 매니저
    
    이 함수는 PostgreSQL 커서를 안전하게 관리합니다.
    컨텍스트 종료 시 자동으로 커밋/롤백 및 리소스 정리를 수행합니다.
    
    Args:
        dict_cursor: True이면 딕셔너리 형태로 결과 반환 (기본: False)
        autocommit: True이면 자동 커밋 활성화 (기본: True)
    
    Yields:
        psycopg2.cursor: 데이터베이스 커서
    
    사용 예시:
        # 기본 사용 (튜플 결과)
        with get_cursor() as cur:
            cur.execute("SELECT id, name FROM users")
            for row in cur.fetchall():
                print(row[0], row[1])  # (1, 'John')
        
        # 딕셔너리 결과
        with get_cursor(dict_cursor=True) as cur:
            cur.execute("SELECT id, name FROM users")
            for row in cur.fetchall():
                print(row['id'], row['name'])  # {'id': 1, 'name': 'John'}
        
        # 수동 커밋
        with get_cursor(autocommit=False) as cur:
            cur.execute("INSERT INTO users (name) VALUES (%s)", ('Jane',))
            # 컨텍스트 종료 시 자동 커밋
    
    에러 처리:
        - 예외 발생 시 자동 롤백
        - 연결 실패 시 재시도 없음 (호출자가 처리)
    
    Raises:
        psycopg2.Error: 데이터베이스 오류
    """
    conn = None
    cur = None
    
    try:
        # ========================================
        # 1. 데이터베이스 연결
        # ========================================
        conn = psycopg2.connect(settings.PG_DSN)
        conn.autocommit = autocommit
        
        # ========================================
        # 2. 커서 생성
        # ========================================
        if dict_cursor:
            # 딕셔너리 커서: 결과를 dict 형태로 반환
            cur = conn.cursor(cursor_factory=RealDictCursor)
        else:
            # 기본 커서: 결과를 튜플 형태로 반환
            cur = conn.cursor()
        
        # ========================================
        # 3. 커서 반환 (yield)
        # ========================================
        yield cur
        
        # ========================================
        # 4. 정상 종료 시 커밋 (autocommit=False인 경우)
        # ========================================
        if not autocommit and conn:
            conn.commit()
            log.debug("✅ Transaction committed")
            
    except psycopg2.Error as e:
        # ========================================
        # 에러 발생 시 롤백
        # ========================================
        if not autocommit and conn:
            conn.rollback()
            log.error(f"❌ Transaction rolled back due to error: {e}")
        else:
            log.error(f"❌ Database error: {e}")
        raise
        
    except Exception as e:
        # ========================================
        # 기타 예외 처리
        # ========================================
        if not autocommit and conn:
            conn.rollback()
            log.error(f"❌ Unexpected error, rolled back: {e}")
        else:
            log.error(f"❌ Unexpected error: {e}")
        raise
        
    finally:
        # ========================================
        # 리소스 정리 (항상 실행)
        # ========================================
        if cur:
            cur.close()
            log.debug("🔒 Cursor closed")
        
        if conn:
            conn.close()
            log.debug("🔒 Connection closed")


# ========================================
# 연결 테스트 함수
# ========================================
def test_connection() -> bool:
    """
    데이터베이스 연결 테스트
    
    Returns:
        bool: 연결 성공 시 True, 실패 시 False
    
    사용 예시:
        if test_connection():
            print("Database connection OK")
        else:
            print("Database connection failed")
    """
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()
            
            if result and result[0] == 1:
                log.info("✅ Database connection test successful")
                return True
            else:
                log.error("❌ Database connection test failed: unexpected result")
                return False
                
    except Exception as e:
        log.error(f"❌ Database connection test failed: {e}")
        return False


# ========================================
# 직접 실행 시 연결 테스트
# ========================================
if __name__ == "__main__":
    """
    연결 테스트 실행
    
    사용법:
        python -m src.db.client
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    log.info("=" * 60)
    log.info("🔌 데이터베이스 연결 테스트")
    log.info(f"   DSN: {settings.PG_DSN}")
    log.info("=" * 60)
    
    # 연결 테스트
    if test_connection():
        log.info("\n✅ 연결 테스트 성공")
        
        # 추가 테스트: 딕셔너리 커서
        log.info("\n📋 딕셔너리 커서 테스트...")
        try:
            with get_cursor(dict_cursor=True) as cur:
                cur.execute("""
                    SELECT 
                        'test_value' AS column1,
                        123 AS column2,
                        TRUE AS column3
                """)
                row = cur.fetchone()
                log.info(f"   결과: {row}")
                log.info("   ✅ 딕셔너리 커서 테스트 성공")
        except Exception as e:
            log.error(f"   ❌ 딕셔너리 커서 테스트 실패: {e}")
        
        # 추가 테스트: 트랜잭션
        log.info("\n🔄 트랜잭션 테스트...")
        try:
            with get_cursor(autocommit=False) as cur:
                cur.execute("SELECT NOW()")
                result = cur.fetchone()
                log.info(f"   결과: {result}")
                log.info("   ✅ 트랜잭션 테스트 성공")
        except Exception as e:
            log.error(f"   ❌ 트랜잭션 테스트 실패: {e}")
    else:
        log.error("\n❌ 연결 테스트 실패")
    
    log.info("\n" + "=" * 60)
