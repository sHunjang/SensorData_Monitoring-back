"""
마이그레이션 테스트용 데이터 생성 스크립트

실행 순서:
1. 기존 분리 테이블 삭제
2. 통합 테이블 생성 (device_id 포함)
3. 테스트 데이터 삽입
4. 서버 재시작하여 자동 마이그레이션 테스트

실행 방법:
    python test_migration_setup.py
"""

import os
import psycopg2
import random
from datetime import datetime, timedelta, timezone

# DB 연결 설정
DSN = os.getenv("PG_DSN", "postgresql://postgres:1234@127.0.0.1:5432/energydb")

# Device ID 목록
MODBUS_DEVICES = [11, 12, 13, 14, 15]
ENV_DEVICES = [21, 22, 23]
SOLAR_DEVICE = 31


def clean_all_tables(cur):
    """기존 모든 테이블 삭제 (깨끗한 테스트 환경)"""
    print("🗑️  기존 테이블 정리 중...")
    
    # 분리 테이블 삭제
    for device_id in MODBUS_DEVICES:
        cur.execute(f"DROP TABLE IF EXISTS modbus_data_{device_id} CASCADE")
        print(f"  ✅ modbus_data_{device_id} 삭제")
    
    for device_id in ENV_DEVICES:
        cur.execute(f"DROP TABLE IF EXISTS env_data_{device_id} CASCADE")
        print(f"  ✅ env_data_{device_id} 삭제")
    
    cur.execute("DROP TABLE IF EXISTS solar_data CASCADE")
    print(f"  ✅ solar_data 삭제")
    
    # 통합 테이블 삭제 (존재할 경우)
    cur.execute("DROP TABLE IF EXISTS modbus_data CASCADE")
    cur.execute("DROP TABLE IF EXISTS env_data CASCADE")
    
    # 백업 테이블 삭제
    cur.execute("DROP TABLE IF EXISTS modbus_data_backup_legacy CASCADE")
    cur.execute("DROP TABLE IF EXISTS env_data_backup_legacy CASCADE")
    
    print("✅ 테이블 정리 완료\n")


def create_legacy_tables(cur):
    """구 버전 통합 테이블 생성 (device_id 포함)"""
    print("📊 통합 테이블 생성 중...")
    
    # Modbus 통합 테이블
    cur.execute("""
        CREATE TABLE modbus_data (
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
        )
    """)
    print("  ✅ modbus_data 테이블 생성")
    
    # Env 통합 테이블
    cur.execute("""
        CREATE TABLE env_data (
            time_stamp TIMESTAMPTZ NOT NULL,
            device_id INT NOT NULL,
            temperature DOUBLE PRECISION,
            humidity DOUBLE PRECISION
        )
    """)
    print("  ✅ env_data 테이블 생성")
    
    # Solar 테이블 (device_id 없음 - 구버전)
    cur.execute("""
        CREATE TABLE solar_data (
            time_stamp TIMESTAMPTZ NOT NULL,
            irradiance DOUBLE PRECISION
        )
    """)
    print("  ✅ solar_data 테이블 생성 (device_id 없음)\n")


def generate_test_data(cur):
    """테스트 데이터 생성"""
    print("🎲 테스트 데이터 생성 중...")
    
    now = datetime.now(timezone.utc)
    base_time = now - timedelta(hours=1)  # 1시간 전부터
    
    # Modbus 데이터 삽입 (각 장치당 20건)
    print("  ⚡ Modbus 데이터 삽입 중...")
    modbus_count = 0
    for device_id in MODBUS_DEVICES:
        for i in range(20):
            timestamp = base_time + timedelta(minutes=i * 3)
            cur.execute("""
                INSERT INTO modbus_data (
                    time_stamp, device_id,
                    avg_line_to_line_volts_v,
                    avg_line_to_neutral_volts_v,
                    sum_line_currents_a,
                    total_active_power_kw,
                    total_reactive_power_kvar,
                    total_apparent_power_kva,
                    total_power_factor,
                    total_active_energy_kwh,
                    total_reactive_energy_kvarh,
                    total_apparent_energy_kvah
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                timestamp, device_id,
                round(random.uniform(380, 400), 2),
                round(random.uniform(220, 230), 2),
                round(random.uniform(10, 50), 2),
                round(random.uniform(1, 10), 3),
                round(random.uniform(0.1, 2), 3),
                round(random.uniform(1, 12), 3),
                round(random.uniform(0.85, 0.99), 3),
                round(random.uniform(100, 1000), 2),
                round(random.uniform(10, 100), 2),
                round(random.uniform(100, 1100), 2)
            ))
            modbus_count += 1
    print(f"    ✅ {modbus_count}건 삽입 완료")
    
    # Env 데이터 삽입 (각 장치당 20건)
    print("  🌡️ Env 데이터 삽입 중...")
    env_count = 0
    for device_id in ENV_DEVICES:
        for i in range(20):
            timestamp = base_time + timedelta(minutes=i * 3)
            cur.execute("""
                INSERT INTO env_data (
                    time_stamp, device_id,
                    temperature, humidity
                ) VALUES (%s, %s, %s, %s)
            """, (
                timestamp, device_id,
                round(random.uniform(15, 35), 1),
                round(random.uniform(30, 70), 1)
            ))
            env_count += 1
    print(f"    ✅ {env_count}건 삽입 완료")
    
    # Solar 데이터 삽입 (device_id 없이 30건)
    print("  ☀️ Solar 데이터 삽입 중...")
    solar_count = 0
    for i in range(30):
        timestamp = base_time + timedelta(minutes=i * 2)
        cur.execute("""
            INSERT INTO solar_data (
                time_stamp, irradiance
            ) VALUES (%s, %s)
        """, (
            timestamp,
            round(random.uniform(0, 1000), 2)
        ))
        solar_count += 1
    print(f"    ✅ {solar_count}건 삽입 완료\n")
    
    print(f"🎉 총 {modbus_count + env_count + solar_count}건 테스트 데이터 생성 완료!\n")


def verify_data(cur):
    """데이터 확인"""
    print("📊 생성된 데이터 확인:")
    
    # Modbus
    cur.execute("SELECT device_id, COUNT(*) FROM modbus_data GROUP BY device_id ORDER BY device_id")
    modbus_counts = cur.fetchall()
    print("  ⚡ Modbus:")
    for device_id, count in modbus_counts:
        print(f"    - Device {device_id}: {count}건")
    
    # Env
    cur.execute("SELECT device_id, COUNT(*) FROM env_data GROUP BY device_id ORDER BY device_id")
    env_counts = cur.fetchall()
    print("  🌡️ Env:")
    for device_id, count in env_counts:
        print(f"    - Device {device_id}: {count}건")
    
    # Solar
    cur.execute("SELECT COUNT(*) FROM solar_data")
    solar_count = cur.fetchone()[0]
    print(f"  ☀️ Solar: {solar_count}건 (device_id 없음)")
    
    # 샘플 데이터 확인
    print("\n📝 샘플 데이터:")
    cur.execute("SELECT time_stamp, device_id, total_active_power_kw FROM modbus_data LIMIT 3")
    print("  Modbus:")
    for row in cur.fetchall():
        print(f"    {row}")
    
    cur.execute("SELECT time_stamp, device_id, temperature FROM env_data LIMIT 3")
    print("  Env:")
    for row in cur.fetchall():
        print(f"    {row}")
    
    cur.execute("SELECT time_stamp, irradiance FROM solar_data LIMIT 3")
    print("  Solar:")
    for row in cur.fetchall():
        print(f"    {row}")


def main():
    """메인 실행"""
    print("=" * 60)
    print("🧪 마이그레이션 테스트 환경 구축")
    print("=" * 60)
    print()
    
    try:
        conn = psycopg2.connect(DSN)
        conn.autocommit = True
        
        with conn.cursor() as cur:
            # Step 1: 기존 테이블 삭제
            clean_all_tables(cur)
            
            # Step 2: 통합 테이블 생성
            create_legacy_tables(cur)
            
            # Step 3: 테스트 데이터 삽입
            generate_test_data(cur)
            
            # Step 4: 데이터 확인
            verify_data(cur)
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ 테스트 환경 구축 완료!")
        print("=" * 60)
        print("\n다음 단계:")
        print("1. 서버 재시작: uvicorn src.main:app --reload")
        print("2. 자동 마이그레이션 로그 확인")
        print("3. 분리 테이블 생성 및 데이터 이동 확인")
        print("\n확인 쿼리:")
        print("  SELECT table_name FROM information_schema.tables")
        print("  WHERE table_schema='public' ORDER BY table_name;")
        print("\n백업 테이블:")
        print("  - modbus_data_backup_legacy")
        print("  - env_data_backup_legacy")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
