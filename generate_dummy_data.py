"""
더미 데이터 생성 스크립트 (9월~10월)

목적: bootstrap.py 마이그레이션 테스트용 더미 데이터 생성
기간: 2025-09-01 00:00:00 ~ 2025-10-14 23:59:59 (약 44일)
주기: 5초마다 1개 레코드 (실제 센서 수집 주기)

센서 구성:
- Modbus 3상 4선식: ID 11, 12, 13
- Modbus 3상 3선식: ID 14, 15
- 환경센서: ID 21, 22, 23
- 태양광센서: ID 31

예상 데이터량:
- 44일 × 24시간 × 3600초 / 5초 = 약 760,320개 레코드 (센서당)
- 전체: 760,320 × 9개 센서 = 약 6,842,880개 레코드

사용법:
  python generate_dummy_data.py
"""

import os
import random
import psycopg2
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# 설정
KST = ZoneInfo("Asia/Seoul")
PG_DSN = os.getenv("PG_DSN", "postgresql://postgres:1234@127.0.0.1:5432/energydb")

# 데이터 생성 기간
START_DATE = datetime(2025, 9, 1, 0, 0, 0, tzinfo=KST)
END_DATE = datetime(2025, 10, 14, 23, 59, 59, tzinfo=KST)
INTERVAL_SECONDS = 5  # 5초마다 데이터 수집

# 센서 ID 정의
MODBUS_4WIRE_IDS = [11, 12, 13]  # 3상 4선식
MODBUS_3WIRE_IDS = [14, 15]      # 3상 3선식
ENV_IDS = [21, 22, 23]           # 온습도
SOLAR_IDS = [31]                 # 일사량

print("=" * 80)
print("🔧 Dummy Data Generator for IoT Monitoring System")
print("=" * 80)
print(f"📅 Period: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}")
print(f"⏱️  Interval: {INTERVAL_SECONDS} seconds")
print(f"📊 Sensors: Modbus(5), Env(3), Solar(1) = Total 9 sensors")

# 예상 데이터 개수 계산
total_seconds = int((END_DATE - START_DATE).total_seconds())
records_per_sensor = total_seconds // INTERVAL_SECONDS
total_records = records_per_sensor * 9

print(f"📈 Expected records: {records_per_sensor:,} per sensor × 9 = {total_records:,} total")
print("=" * 80)
print()

# 사용자 확인
response = input("⚠️  This will insert ~6.8M records. Continue? (yes/no): ")
if response.lower() != 'yes':
    print("❌ Cancelled by user")
    exit(0)

print()
print("🚀 Starting data generation...")
print()


def generate_modbus_4wire_data(device_id: int, timestamp: datetime) -> dict:
    """
    Modbus 3상 4선식 더미 데이터 생성 (ID: 11, 12, 13)
    특징: Line-to-Line 전압 (200-240V)
    """
    # 시간에 따른 변동 시뮬레이션 (낮 시간대 높은 전력)
    hour = timestamp.hour
    time_factor = 1.0
    if 9 <= hour <= 17:  # 업무 시간
        time_factor = 1.5
    elif 18 <= hour <= 22:  # 저녁 시간
        time_factor = 1.2
    else:  # 심야 시간
        time_factor = 0.6
    
    # 기본 전력량 (누적값 시뮬레이션)
    base_energy = (timestamp - START_DATE).total_seconds() / 3600 * 10 * time_factor  # 시간당 10kWh 기준
    
    return {
        'avg_line_to_line_volts_v': round(random.uniform(200, 240), 2),
        'avg_line_to_neutral_volts_v': None,  # 4선식은 사용 안함
        'sum_line_currents_a': round(random.uniform(20, 50) * time_factor, 2),
        'total_active_power_kw': round(random.uniform(5, 12) * time_factor, 2),
        'total_reactive_power_kvar': round(random.uniform(1, 3) * time_factor, 2),
        'total_apparent_power_kva': round(random.uniform(5, 13) * time_factor, 2),
        'total_power_factor': round(random.uniform(0.85, 0.95), 3),
        'total_active_energy_kwh': round(base_energy + random.uniform(-0.5, 0.5), 3),
        'total_reactive_energy_kvarh': round(base_energy * 0.2, 3),
        'total_apparent_energy_kvah': round(base_energy * 1.05, 3),
    }


def generate_modbus_3wire_data(device_id: int, timestamp: datetime) -> dict:
    """
    Modbus 3상 3선식 더미 데이터 생성 (ID: 14, 15)
    특징: Line-to-Neutral 전압 (110-140V)
    """
    hour = timestamp.hour
    time_factor = 1.0
    if 9 <= hour <= 17:
        time_factor = 1.5
    elif 18 <= hour <= 22:
        time_factor = 1.2
    else:
        time_factor = 0.6
    
    base_energy = (timestamp - START_DATE).total_seconds() / 3600 * 8 * time_factor
    
    return {
        'avg_line_to_line_volts_v': None,  # 3선식은 사용 안함
        'avg_line_to_neutral_volts_v': round(random.uniform(110, 140), 2),
        'sum_line_currents_a': round(random.uniform(15, 40) * time_factor, 2),
        'total_active_power_kw': round(random.uniform(4, 10) * time_factor, 2),
        'total_reactive_power_kvar': round(random.uniform(1, 2.5) * time_factor, 2),
        'total_apparent_power_kva': round(random.uniform(4, 11) * time_factor, 2),
        'total_power_factor': round(random.uniform(0.85, 0.95), 3),
        'total_active_energy_kwh': round(base_energy + random.uniform(-0.5, 0.5), 3),
        'total_reactive_energy_kvarh': round(base_energy * 0.2, 3),
        'total_apparent_energy_kvah': round(base_energy * 1.05, 3),
    }


def generate_env_data(device_id: int, timestamp: datetime) -> dict:
    """
    환경센서 더미 데이터 생성 (ID: 21, 22, 23)
    특징: 온도/습도 - 시간과 계절에 따른 변화
    """
    hour = timestamp.hour
    month = timestamp.month
    
    # 9월은 가을, 10월은 더 선선
    base_temp = 20 if month == 9 else 15
    
    # 시간대별 온도 변화
    if 12 <= hour <= 16:  # 낮 시간
        temp_offset = random.uniform(3, 7)
    elif 6 <= hour <= 11:  # 아침
        temp_offset = random.uniform(0, 3)
    elif 17 <= hour <= 21:  # 저녁
        temp_offset = random.uniform(1, 4)
    else:  # 밤
        temp_offset = random.uniform(-3, 0)
    
    temperature = round(base_temp + temp_offset + random.uniform(-1, 1), 2)
    
    # 습도는 온도와 반비례 경향
    humidity = round(70 - (temperature - base_temp) * 2 + random.uniform(-5, 5), 2)
    humidity = max(30, min(90, humidity))  # 30~90% 범위
    
    return {
        'temperature': temperature,
        'humidity': humidity,
    }


def generate_solar_data(device_id: int, timestamp: datetime) -> dict:
    """
    태양광센서 더미 데이터 생성 (ID: 31)
    특징: 일사량 - 시간과 날씨에 따른 변화
    """
    hour = timestamp.hour
    
    # 밤에는 일사량 0
    if hour < 6 or hour > 18:
        irradiance = 0.0
    else:
        # 낮 시간대 일사량 계산 (정오에 최대)
        # 6시~12시: 상승, 12시~18시: 하강
        if hour <= 12:
            progress = (hour - 6) / 6  # 0 ~ 1
        else:
            progress = (18 - hour) / 6  # 1 ~ 0
        
        # 기본 일사량 (W/m²)
        max_irradiance = 1000  # 맑은 날 최대 일사량
        base_irradiance = max_irradiance * progress
        
        # 구름에 의한 변동 (20% 확률로 흐림)
        if random.random() < 0.2:
            cloud_factor = random.uniform(0.3, 0.7)  # 흐림
        else:
            cloud_factor = random.uniform(0.85, 1.0)  # 맑음
        
        irradiance = round(base_irradiance * cloud_factor + random.uniform(-50, 50), 2)
        irradiance = max(0, irradiance)
    
    return {
        'irradiance': irradiance,
    }


def insert_data_batch():
    """
    배치로 데이터 삽입 (성능 최적화)
    """
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = False
    
    try:
        cur = conn.cursor()
        
        # 배치 크기 (한 번에 삽입할 레코드 수)
        BATCH_SIZE = 10000
        
        current_time = START_DATE
        batch_count = 0
        total_inserted = 0
        
        # Modbus 배치 버퍼
        modbus_batch = []
        env_batch = []
        solar_batch = []
        
        print("📊 Generating data...")
        print(f"   Batch size: {BATCH_SIZE:,} records")
        print()
        
        while current_time <= END_DATE:
            # Modbus 3상 4선식 (ID: 11, 12, 13)
            for device_id in MODBUS_4WIRE_IDS:
                data = generate_modbus_4wire_data(device_id, current_time)
                modbus_batch.append((
                    current_time, device_id,
                    data['avg_line_to_line_volts_v'],
                    data['avg_line_to_neutral_volts_v'],
                    data['sum_line_currents_a'],
                    data['total_active_power_kw'],
                    data['total_reactive_power_kvar'],
                    data['total_apparent_power_kva'],
                    data['total_power_factor'],
                    data['total_active_energy_kwh'],
                    data['total_reactive_energy_kvarh'],
                    data['total_apparent_energy_kvah']
                ))
            
            # Modbus 3상 3선식 (ID: 14, 15)
            for device_id in MODBUS_3WIRE_IDS:
                data = generate_modbus_3wire_data(device_id, current_time)
                modbus_batch.append((
                    current_time, device_id,
                    data['avg_line_to_line_volts_v'],
                    data['avg_line_to_neutral_volts_v'],
                    data['sum_line_currents_a'],
                    data['total_active_power_kw'],
                    data['total_reactive_power_kvar'],
                    data['total_apparent_power_kva'],
                    data['total_power_factor'],
                    data['total_active_energy_kwh'],
                    data['total_reactive_energy_kvarh'],
                    data['total_apparent_energy_kvah']
                ))
            
            # 환경센서 (ID: 21, 22, 23)
            for device_id in ENV_IDS:
                data = generate_env_data(device_id, current_time)
                env_batch.append((
                    current_time, device_id,
                    data['temperature'],
                    data['humidity']
                ))
            
            # 태양광센서 (ID: 31)
            for device_id in SOLAR_IDS:
                data = generate_solar_data(device_id, current_time)
                solar_batch.append((
                    current_time, device_id,
                    data['irradiance']
                ))
            
            # 배치 크기에 도달하면 삽입
            if len(modbus_batch) >= BATCH_SIZE:
                # Modbus 데이터 삽입
                cur.executemany("""
                    INSERT INTO modbus_data (
                        time_stamp, device_id,
                        avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
                        sum_line_currents_a, total_active_power_kw,
                        total_reactive_power_kvar, total_apparent_power_kva,
                        total_power_factor, total_active_energy_kwh,
                        total_reactive_energy_kvarh, total_apparent_energy_kvah
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, modbus_batch)
                
                # 환경센서 데이터 삽입
                cur.executemany("""
                    INSERT INTO env_data (time_stamp, device_id, temperature, humidity)
                    VALUES (%s, %s, %s, %s)
                """, env_batch)
                
                # 태양광센서 데이터 삽입
                cur.executemany("""
                    INSERT INTO solar_data (time_stamp, device_id, irradiance)
                    VALUES (%s, %s, %s)
                """, solar_batch)
                
                conn.commit()
                
                batch_count += 1
                total_inserted += len(modbus_batch) + len(env_batch) + len(solar_batch)
                
                print(f"✅ Batch #{batch_count}: Inserted {len(modbus_batch):,} + {len(env_batch):,} + {len(solar_batch):,} records")
                print(f"   Progress: {current_time.strftime('%Y-%m-%d %H:%M:%S')} | Total: {total_inserted:,}")
                
                # 배치 초기화
                modbus_batch = []
                env_batch = []
                solar_batch = []
            
            # 다음 시간으로 이동
            current_time += timedelta(seconds=INTERVAL_SECONDS)
        
        # 남은 데이터 삽입
        if modbus_batch:
            cur.executemany("""
                INSERT INTO modbus_data (
                    time_stamp, device_id,
                    avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
                    sum_line_currents_a, total_active_power_kw,
                    total_reactive_power_kvar, total_apparent_power_kva,
                    total_power_factor, total_active_energy_kwh,
                    total_reactive_energy_kvarh, total_apparent_energy_kvah
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, modbus_batch)
            
            cur.executemany("""
                INSERT INTO env_data (time_stamp, device_id, temperature, humidity)
                VALUES (%s, %s, %s, %s)
            """, env_batch)
            
            cur.executemany("""
                INSERT INTO solar_data (time_stamp, device_id, irradiance)
                VALUES (%s, %s, %s)
            """, solar_batch)
            
            conn.commit()
            total_inserted += len(modbus_batch) + len(env_batch) + len(solar_batch)
            print(f"✅ Final batch: Inserted {len(modbus_batch) + len(env_batch) + len(solar_batch):,} records")
        
        cur.close()
        conn.close()
        
        print()
        print("=" * 80)
        print(f"✅ Data generation completed!")
        print(f"   Total records inserted: {total_inserted:,}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        conn.close()
        raise


if __name__ == "__main__":
    insert_data_batch()
    
    print()
    print("💡 Next steps:")
    print("   1. Run: python -m src.db.bootstrap --migrate")
    print("   2. Check aggregated tables for migrated data")
    print()
