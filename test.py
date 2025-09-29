"""
PostgreSQL 16 연결 테스트 스크립트
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def test_pg16_connection():
    dsn = os.getenv("PG_DSN", "postgresql://postgres:postgres@127.0.0.1:5432/energydb")
    print(f"🎯 PostgreSQL 16 연결 테스트")
    print(f"🔍 DSN: {dsn}")
    
    # 1단계: postgres 데이터베이스에 먼저 연결 (기본 DB)
    try:
        base_dsn = dsn.replace('/energydb', '/postgres')
        print(f"🔍 1단계: 기본 postgres DB 연결 시도...")
        print(f"   DSN: {base_dsn}")
        
        conn = psycopg2.connect(base_dsn)
        print("✅ PostgreSQL 16 서버 연결 성공!")
        
        cur = conn.cursor()
        
        # 버전 확인
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"📊 PostgreSQL 버전: {version}")
        
        # energydb 존재 여부 확인
        cur.execute("SELECT datname FROM pg_database WHERE datname='energydb';")
        result = cur.fetchone()
        
        if result:
            print("✅ energydb 데이터베이스 존재함")
        else:
            print("⚠️  energydb 데이터베이스 없음, 생성 중...")
            conn.autocommit = True
            cur.execute("CREATE DATABASE energydb;")
            print("✅ energydb 데이터베이스 생성 완료!")
        
        conn.close()
        
        # 2단계: energydb에 직접 연결 테스트
        print(f"🔍 2단계: energydb 연결 시도...")
        conn = psycopg2.connect(dsn)
        print("✅ energydb 연결 성공!")
        
        cur = conn.cursor()
        cur.execute("SELECT current_database();")
        db_name = cur.fetchone()[0]
        print(f"🗄️  현재 데이터베이스: {db_name}")
        
        conn.close()
        print("🎉 PostgreSQL 16 연결 테스트 완료!")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ PostgreSQL 16 연결 실패:")
        print(f"   에러: {e}")
        
        if "could not connect to server" in str(e):
            print("💡 해결책:")
            print("   1. PostgreSQL 16 서비스 시작: net start postgresql-x64-16")
            print("   2. 방화벽에서 5432 포트 허용")
        elif "authentication failed" in str(e):
            print("💡 해결책:")
            print("   1. 비밀번호 확인")
            print("   2. pg_hba.conf에서 인증 설정 확인")
        elif "database" in str(e) and "does not exist" in str(e):
            print("💡 해결책:")
            print("   1. psql -U postgres로 연결 후 CREATE DATABASE energydb;")
        
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 에러: {e}")
        return False

def check_pg16_service():
    """PostgreSQL 16 서비스 상태 확인 (Windows)"""
    import subprocess
    try:
        result = subprocess.run(['sc', 'query', 'postgresql-x64-16'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            if "RUNNING" in result.stdout:
                print("✅ PostgreSQL 16 서비스 실행 중")
                return True
            else:
                print("⚠️  PostgreSQL 16 서비스 중지됨")
                print("💡 서비스 시작: net start postgresql-x64-16")
                return False
        else:
            print("❌ PostgreSQL 16 서비스를 찾을 수 없음")
            print("💡 PostgreSQL 16이 올바르게 설치되었는지 확인")
            return False
    except Exception as e:
        print(f"⚠️  서비스 상태 확인 실패: {e}")
        return False

if __name__ == "__main__":
    print("🎯 PostgreSQL 16 연결 진단 시작...")
    print("=" * 50)
    
    # 서비스 상태 확인
    service_ok = check_pg16_service()
    print()
    
    # 연결 테스트
    if service_ok:
        connection_ok = test_pg16_connection()
    else:
        print("⚠️  서비스가 실행되지 않아 연결 테스트를 건너뜁니다.")
        connection_ok = False
    
    print("=" * 50)
    if connection_ok:
        print("🎉 모든 테스트 통과! PostgreSQL 16 연결 준비 완료!")
    else:
        print("❌ 연결 문제가 있습니다. 위의 해결책을 시도해보세요.")
