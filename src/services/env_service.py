"""
환경센서(온습도) 서비스 모듈

주요 기능:
- 시간 해상도별 데이터 조회 (1일/1주/1달/1년)
- 실시간 데이터 조회
- 온도/습도 통계 계산

데이터 소스:
- 실시간: env_data (원시 데이터)
- 1일 그래프: env_1min (1분 집계)
- 1주 그래프: env_15min (15분 집계)
- 1달 그래프: env_1hour (1시간 집계)
- 1년 그래프: env_1day (1일 집계)

*** 주요 수정 사항 ***
✅ 집계 테이블 사용: 원시 env_data 대신 env_1min, env_15min, env_1hour, env_1day 테이블에서 조회​

✅ 자동 해상도 선택: preset에 따라 적절한 집계 테이블 자동 선택

✅ min/max 값 제공: 집계 테이블에서 최소/최대 온도/습도 제공

✅ 실시간 조회: query_env_realtime() - 원시 데이터에서 최신 1건 조회

✅ 통계 함수: get_env_statistics() - 최근 N일 통계

✅ 쾌적도 지수: get_comfort_index() - 온도/습도 기반 쾌적도 계산 (추가 기능)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo

from src.db.client import get_cursor

KST = ZoneInfo("Asia/Seoul")


# ============================================================
# 시간 범위 및 해상도 결정
# ============================================================

def _determine_resolution_and_range(
    preset: Optional[str],
    start: Optional[str],
    end: Optional[str]
) -> tuple:
    """
    요청 파라미터로부터 시간 범위와 조회할 해상도 결정
    
    Args:
        preset: "1day", "1week", "1month", "1year"
        start: 시작 시각 (ISO format)
        end: 종료 시각 (ISO format)
        
    Returns:
        (start_dt, end_dt, resolution)
        resolution: "1min", "15min", "1hour", "1day"
    """
    now = datetime.now(KST)
    
    if preset:
        if preset == "1day":
            # 하루 단위: 오늘 00:00 ~ 23:59, 1분 집계 사용
            start_dt = datetime.combine(now.date(), time(0, 0, 0), tzinfo=KST)
            end_dt = start_dt + timedelta(days=1)
            resolution = "1min"
            
        elif preset == "1week":
            # 1주 단위: 최근 7일, 15분 집계 사용
            start_dt = now - timedelta(days=7)
            end_dt = now
            resolution = "15min"
            
        elif preset == "1month":
            # 1달 단위: 최근 30일, 1시간 집계 사용
            start_dt = now - timedelta(days=30)
            end_dt = now
            resolution = "1hour"
            
        elif preset == "1year":
            # 1년 단위: 최근 365일, 1일 집계 사용
            start_dt = now - timedelta(days=365)
            end_dt = now
            resolution = "1day"
            
        else:
            # 기본값: 1일
            start_dt = datetime.combine(now.date(), time(0, 0, 0), tzinfo=KST)
            end_dt = start_dt + timedelta(days=1)
            resolution = "1min"
    
    elif start and end:
        # 직접 시간 범위 지정
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        
        # timezone 처리
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=KST)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=KST)
        
        # 범위에 따라 자동으로 해상도 결정
        delta = end_dt - start_dt
        if delta <= timedelta(days=1):
            resolution = "1min"
        elif delta <= timedelta(days=7):
            resolution = "15min"
        elif delta <= timedelta(days=31):
            resolution = "1hour"
        else:
            resolution = "1day"
    
    else:
        # 기본값: 오늘 하루
        start_dt = datetime.combine(now.date(), time(0, 0, 0), tzinfo=KST)
        end_dt = start_dt + timedelta(days=1)
        resolution = "1min"
    
    return start_dt, end_dt, resolution


# ============================================================
# 메인 조회 함수
# ============================================================

def query_env_data(
    device_id: int,
    preset: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_points: int = 1440
) -> Dict[str, Any]:
    """
    환경센서 데이터 조회 (시간 해상도 자동 선택)
    
    Args:
        device_id: 디바이스 ID (21~23)
        preset: "1day", "1week", "1month", "1year"
        start: 시작 시각 (ISO format)
        end: 종료 시각 (ISO format)
        max_points: 최대 데이터 포인트 (기본 1440)
        
    Returns:
        dict: {
            "device_id": int,
            "resolution": "1min" | "15min" | "1hour" | "1day",
            "start": ISO string (KST),
            "end": ISO string (KST),
            "data_points": int,
            "data": [
                {
                    "bucket": ISO string (KST),
                    "avg_temperature": float,
                    "min_temperature": float,
                    "max_temperature": float,
                    "avg_humidity": float,
                    "min_humidity": float,
                    "max_humidity": float
                },
                ...
            ]
        }
    """
    # 1. 시간 범위 및 해상도 결정
    start_dt, end_dt, resolution = _determine_resolution_and_range(preset, start, end)
    
    # 2. 테이블명 결정
    table_name = f"env_{resolution}"
    
    # 3. 쿼리 작성
    sql = f"""
        SELECT
            bucket,
            avg_temperature,
            min_temperature,
            max_temperature,
            avg_humidity,
            min_humidity,
            max_humidity,
            data_points
        FROM {table_name}
        WHERE device_id = %s
          AND bucket >= %s
          AND bucket < %s
        ORDER BY bucket ASC
        LIMIT %s;
    """
    
    # 4. 쿼리 실행
    with get_cursor() as cur:
        cur.execute(sql, (device_id, start_dt, end_dt, max_points))
        rows = cur.fetchall()
    
    # 5. 결과 포맷팅
    data = []
    for row in rows:
        bucket_ts = row[0]
        if bucket_ts and bucket_ts.tzinfo is None:
            bucket_ts = bucket_ts.replace(tzinfo=KST)
        
        data.append({
            "bucket": bucket_ts.isoformat() if bucket_ts else None,
            "avg_temperature": round(row[1], 2) if row[1] is not None else None,
            "min_temperature": round(row[2], 2) if row[2] is not None else None,
            "max_temperature": round(row[3], 2) if row[3] is not None else None,
            "avg_humidity": round(row[4], 2) if row[4] is not None else None,
            "min_humidity": round(row[5], 2) if row[5] is not None else None,
            "max_humidity": round(row[6], 2) if row[6] is not None else None,
        })
    
    # 6. 응답 구성
    return {
        "device_id": device_id,
        "resolution": resolution,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "data_points": len(data),
        "data": data,
    }


# ============================================================
# 실시간 데이터 조회
# ============================================================

def query_env_realtime(device_id: int) -> Optional[Dict[str, Any]]:
    """
    최신 원시 데이터 1건 조회 (실시간 모니터링용)
    
    Args:
        device_id: 디바이스 ID
        
    Returns:
        dict 또는 None
        {
            "time_stamp": ISO string (KST),
            "device_id": int,
            "temperature": float,
            "humidity": float
        }
    """
    sql = """
        SELECT
            time_stamp,
            device_id,
            temperature,
            humidity
        FROM env_data
        WHERE device_id = %s
        ORDER BY time_stamp DESC
        LIMIT 1;
    """
    
    with get_cursor() as cur:
        cur.execute(sql, (device_id,))
        row = cur.fetchone()
    
    if not row:
        return None
    
    ts = row[0]
    if ts and ts.tzinfo is None:
        ts = ts.replace(tzinfo=KST)
    
    return {
        "time_stamp": ts.isoformat() if ts else None,
        "device_id": row[1],
        "temperature": round(row[2], 2) if row[2] is not None else None,
        "humidity": round(row[3], 2) if row[3] is not None else None,
    }


# ============================================================
# 통계 계산
# ============================================================

def get_env_statistics(device_id: int, days: int = 7) -> Dict[str, Any]:
    """
    환경센서 통계 계산 (최근 N일간)
    
    Args:
        device_id: 디바이스 ID
        days: 통계 기간 (일)
        
    Returns:
        dict: {
            "avg_temperature": float,
            "min_temperature": float,
            "max_temperature": float,
            "avg_humidity": float,
            "min_humidity": float,
            "max_humidity": float,
            "period_days": int
        }
    """
    now_kst = datetime.now(KST)
    start_dt = now_kst - timedelta(days=days)
    
    table_name = "env_1day"
    
    sql = f"""
        SELECT
            AVG(avg_temperature) AS avg_temp,
            MIN(min_temperature) AS min_temp,
            MAX(max_temperature) AS max_temp,
            AVG(avg_humidity) AS avg_hum,
            MIN(min_humidity) AS min_hum,
            MAX(max_humidity) AS max_hum
        FROM {table_name}
        WHERE device_id = %s
          AND bucket >= %s
          AND bucket < %s;
    """
    
    with get_cursor() as cur:
        cur.execute(sql, (device_id, start_dt, now_kst))
        row = cur.fetchone()
    
    if not row:
        return {
            "avg_temperature": None,
            "min_temperature": None,
            "max_temperature": None,
            "avg_humidity": None,
            "min_humidity": None,
            "max_humidity": None,
            "period_days": days,
        }
    
    return {
        "avg_temperature": round(float(row[0]), 2) if row[0] else None,
        "min_temperature": round(float(row[1]), 2) if row[1] else None,
        "max_temperature": round(float(row[2]), 2) if row[2] else None,
        "avg_humidity": round(float(row[3]), 2) if row[3] else None,
        "min_humidity": round(float(row[4]), 2) if row[4] else None,
        "max_humidity": round(float(row[5]), 2) if row[5] else None,
        "period_days": days,
    }


# ============================================================
# 쾌적도 계산
# ============================================================

def get_comfort_index(device_id: int) -> Dict[str, Any]:
    """
    현재 쾌적도 지수 계산
    
    쾌적 범위:
        - 온도: 18~26°C
        - 습도: 40~60%RH
    
    Args:
        device_id: 디바이스 ID
        
    Returns:
        dict: {
            "temperature": float,
            "humidity": float,
            "temp_status": "low" | "comfortable" | "high",
            "humidity_status": "low" | "comfortable" | "high",
            "overall_comfort": "uncomfortable" | "comfortable"
        }
    """
    realtime = query_env_realtime(device_id)
    
    if not realtime:
        return {
            "temperature": None,
            "humidity": None,
            "temp_status": "unknown",
            "humidity_status": "unknown",
            "overall_comfort": "unknown",
        }
    
    temp = realtime["temperature"]
    hum = realtime["humidity"]
    
    # 온도 상태 판정
    if temp is None:
        temp_status = "unknown"
    elif temp < 18:
        temp_status = "low"
    elif temp <= 26:
        temp_status = "comfortable"
    else:
        temp_status = "high"
    
    # 습도 상태 판정
    if hum is None:
        humidity_status = "unknown"
    elif hum < 40:
        humidity_status = "low"
    elif hum <= 60:
        humidity_status = "comfortable"
    else:
        humidity_status = "high"
    
    # 종합 쾌적도
    if temp_status == "comfortable" and humidity_status == "comfortable":
        overall = "comfortable"
    else:
        overall = "uncomfortable"
    
    return {
        "temperature": temp,
        "humidity": hum,
        "temp_status": temp_status,
        "humidity_status": humidity_status,
        "overall_comfort": overall,
    }
