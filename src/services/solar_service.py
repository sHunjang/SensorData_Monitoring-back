"""
태양광(일사량) 센서 서비스 모듈

주요 기능:
- 시간 해상도별 데이터 조회 (1일/1주/1달/1년)
- 실시간 데이터 조회
- 일사량 통계 계산

데이터 소스:
- 실시간: solar_data (원시 데이터)
- 1일 그래프: solar_1min (1분 집계)
- 1주 그래프: solar_15min (15분 집계)
- 1달 그래프: solar_1hour (1시간 집계)
- 1년 그래프: solar_1day (1일 집계)
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
    
    ✅ 수정: preset이 있으면 해당 해상도 고정, start/end와 함께 사용
    
    Args:
        preset: "1day", "1week", "1month", "1year"
        start: 시작 시각 (ISO format)
        end: 종료 시각 (ISO format)
        
    Returns:
        (start_dt, end_dt, resolution)
        resolution: "1min", "15min", "1hour", "1day"
    """
    now = datetime.now(KST)
    
    # ✅ 헬퍼 함수: ISO 문자열을 KST datetime으로 변환
    def parse_iso_to_kst(iso_str: str) -> datetime:
        """ISO 8601 문자열을 KST datetime으로 변환"""
        # ✅ .000Z 포맷 제거 (Python 3.11+ 호환)
        iso_str = iso_str.replace('.000Z', 'Z').replace('Z', '+00:00')
        
        dt = datetime.fromisoformat(iso_str)
        
        # UTC → KST 변환
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        else:
            dt = dt.astimezone(KST)
        
        return dt
    
    # ✅ preset이 있으면 해당 해상도 고정
    if preset:
        if preset == "1day":
            if start and end:
                start_dt = parse_iso_to_kst(start)
                end_dt = parse_iso_to_kst(end)
            else:
                start_dt = datetime.combine(now.date(), time(0, 0, 0), tzinfo=KST)
                end_dt = start_dt + timedelta(days=1)
            
            resolution = "1min"
            
        elif preset == "1week":
            if start and end:
                start_dt = parse_iso_to_kst(start)
                end_dt = parse_iso_to_kst(end)
            else:
                start_dt = now - timedelta(days=7)
                end_dt = now
            
            resolution = "15min"
            
        elif preset == "1month":
            if start and end:
                start_dt = parse_iso_to_kst(start)
                end_dt = parse_iso_to_kst(end)
            else:
                start_dt = now - timedelta(days=30)
                end_dt = now
            
            resolution = "1hour"
            
        elif preset == "1year":
            if start and end:
                start_dt = parse_iso_to_kst(start)
                end_dt = parse_iso_to_kst(end)
            else:
                start_dt = now - timedelta(days=365)
                end_dt = now
            
            resolution = "1day"
            
        else:
            # 기본값: 1일
            start_dt = datetime.combine(now.date(), time(0, 0, 0), tzinfo=KST)
            end_dt = start_dt + timedelta(days=1)
            resolution = "1min"
    
    elif start and end:
        # preset 없이 직접 시간 범위 지정
        start_dt = parse_iso_to_kst(start)
        end_dt = parse_iso_to_kst(end)
        
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

def query_solar_data(
    device_id: int,
    preset: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_points: int = 1440
) -> Dict[str, Any]:
    """
    태양광 센서 데이터 조회 (시간 해상도 자동 선택)
    
    Args:
        device_id: 디바이스 ID (31)
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
                    "avg_irradiance": float,
                    "min_irradiance": float,
                    "max_irradiance": float
                },
                ...
            ]
        }
    """
    # 1. 시간 범위 및 해상도 결정
    start_dt, end_dt, resolution = _determine_resolution_and_range(preset, start, end)
    
    # 2. 테이블명 결정
    table_name = f"solar_{resolution}"
    
    # 3. 쿼리 작성
    sql = f"""
        SELECT
            bucket,
            avg_irradiance,
            min_irradiance,
            max_irradiance,
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
            "avg_irradiance": round(row[1], 2) if row[1] is not None else None,
            "min_irradiance": round(row[2], 2) if row[2] is not None else None,
            "max_irradiance": round(row[3], 2) if row[3] is not None else None,
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

def query_solar_realtime(device_id: int) -> Optional[Dict[str, Any]]:
    """
    최신 원시 데이터 1건 조회 (실시간 모니터링용)
    
    Args:
        device_id: 디바이스 ID
        
    Returns:
        dict 또는 None
        {
            "time_stamp": ISO string (KST),
            "device_id": int,
            "irradiance": float (W/m²)
        }
    """
    sql = """
        SELECT
            time_stamp,
            device_id,
            irradiance
        FROM solar_data
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
        "irradiance": round(row[2], 2) if row[2] is not None else None,
    }


# ============================================================
# 통계 계산
# ============================================================

def get_solar_statistics(device_id: int, days: int = 7) -> Dict[str, Any]:
    """
    태양광 센서 통계 계산 (최근 N일간)
    
    Args:
        device_id: 디바이스 ID
        days: 통계 기간 (일)
        
    Returns:
        dict: {
            "avg_irradiance": float,
            "max_irradiance": float,
            "total_solar_hours": float (일사량 > 100 W/m² 시간),
            "period_days": int
        }
    """
    now_kst = datetime.now(KST)
    start_dt = now_kst - timedelta(days=days)
    
    table_name = "solar_1day"
    
    sql = f"""
        SELECT
            AVG(avg_irradiance) AS avg_irr,
            MAX(max_irradiance) AS max_irr
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
            "avg_irradiance": None,
            "max_irradiance": None,
            "period_days": days,
        }
    
    # 일조 시간 계산 (1시간 단위로 100 W/m² 이상인 시간 합산)
    table_1hour = "solar_1hour"
    sql_hours = f"""
        SELECT COUNT(*)
        FROM {table_1hour}
        WHERE device_id = %s
          AND bucket >= %s
          AND bucket < %s
          AND avg_irradiance >= 100;
    """
    
    with get_cursor() as cur:
        cur.execute(sql_hours, (device_id, start_dt, now_kst))
        hours_row = cur.fetchone()
        solar_hours = float(hours_row[0]) if hours_row and hours_row[0] else 0.0
    
    return {
        "avg_irradiance": round(float(row[0]), 2) if row[0] else None,
        "max_irradiance": round(float(row[1]), 2) if row[1] else None,
        "total_solar_hours": solar_hours,
        "period_days": days,
    }


# ============================================================
# 발전 효율 추정
# ============================================================

def estimate_solar_efficiency(device_id: int) -> Dict[str, Any]:
    """
    태양광 발전 효율 추정
    
    기준:
        - 1000 W/m² = 100% (STC 표준 조건)
        - 현재 일사량 기준 상대 효율 계산
    
    Args:
        device_id: 디바이스 ID
        
    Returns:
        dict: {
            "current_irradiance": float (W/m²),
            "efficiency_percent": float (%),
            "status": "excellent" | "good" | "fair" | "poor" | "none"
        }
    """
    realtime = query_solar_realtime(device_id)
    
    if not realtime or realtime["irradiance"] is None:
        return {
            "current_irradiance": None,
            "efficiency_percent": None,
            "status": "unknown",
        }
    
    irr = realtime["irradiance"]
    
    # 효율 계산 (STC 1000 W/m² 기준)
    efficiency = (irr / 1000.0) * 100.0
    
    # 상태 판정
    if irr < 50:
        status = "none"  # 발전 거의 없음
    elif irr < 300:
        status = "poor"  # 흐림/실내
    elif irr < 600:
        status = "fair"  # 부분 흐림
    elif irr < 900:
        status = "good"  # 맑음
    else:
        status = "excellent"  # 매우 맑음
    
    return {
        "current_irradiance": round(irr, 2),
        "efficiency_percent": round(efficiency, 2),
        "status": status,
    }


# ============================================================
# 오늘 일사량 적산값 계산
# ============================================================

def get_today_solar_energy(device_id: int) -> Optional[float]:
    """
    오늘(KST 기준 00:00~현재) 일사량 적산값 계산
    
    Args:
        device_id: 디바이스 ID
        
    Returns:
        float (Wh/m²) 또는 None
        
    계산:
        - 1시간 집계 테이블에서 평균 일사량을 합산
        - avg_irradiance (W/m²) × 1시간 = Wh/m²
    """
    now_kst = datetime.now(KST)
    today_start = datetime.combine(now_kst.date(), time(0, 0, 0), tzinfo=KST)
    tomorrow_start = today_start + timedelta(days=1)
    
    table_name = "solar_1hour"
    
    sql = f"""
        SELECT SUM(avg_irradiance)
        FROM {table_name}
        WHERE device_id = %s
          AND bucket >= %s
          AND bucket < %s;
    """
    
    with get_cursor() as cur:
        cur.execute(sql, (device_id, today_start, tomorrow_start))
        row = cur.fetchone()
        if row and row[0] is not None:
            # 합산값 = Wh/m² (1시간 평균 × 시간 수)
            return round(float(row[0]), 2)
    
    return None
