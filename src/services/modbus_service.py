"""
Modbus(전력량계) 서비스 모듈

주요 기능:
- 시간 해상도별 데이터 조회 (1일/1주/1달/1년)
- 3상 4선식 / 3상 3선식 자동 구분
- 실시간 데이터 조회
- 오늘 누적 에너지 계산

데이터 소스:
- 실시간: modbus_data (원시 데이터)
- 1일 그래프: modbus_*wire_1min (1분 집계)
- 1주 그래프: modbus_*wire_15min (15분 집계)
- 1달 그래프: modbus_*wire_1hour (1시간 집계)
- 1년 그래프: modbus_*wire_1day (1일 집계)

*** 주요 수정 사항 ***
    ✅ 집계 테이블 사용: 원시 modbus_data 대신 modbus_4wire_*, modbus_3wire_* 테이블에서 조회​

    ✅ 자동 해상도 선택: preset에 따라 적절한 집계 테이블 자동 선택

    1day → 1분 테이블

    1week → 15분 테이블

    1month → 1시간 테이블

    1year → 1일 테이블

    ✅ 3선/4선 자동 구분: settings.is_4wire_device() 활용

    ✅ 피크 전력 지원: 15분 이후 해상도에서 피크 전력 제공

    ✅ 에너지 delta: 구간별 소비량 제공 (energy_delta_kwh)

    ✅ 통계 함수 추가: get_device_statistics() - 최근 N일 통계

"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo

from src.db.client import get_cursor
from src.config.settings import settings

KST = ZoneInfo("Asia/Seoul")


# ============================================================
# 헬퍼 함수
# ============================================================

def _is_4wire(device_id: int) -> bool:
    """디바이스가 3상 4선식인지 확인"""
    return settings.is_4wire_device(device_id)


def _is_3wire(device_id: int) -> bool:
    """디바이스가 3상 3선식인지 확인"""
    return settings.is_3wire_device(device_id)


def _get_table_and_columns(device_id: int, resolution: str) -> tuple:
    """
    디바이스 타입과 해상도에 맞는 테이블명과 컬럼 반환
    
    Args:
        device_id: 디바이스 ID
        resolution: "1min", "15min", "1hour", "1day"
        
    Returns:
        (table_name, voltage_col, energy_col_available)
    """
    is_4w = _is_4wire(device_id)
    wire_type = "4wire" if is_4w else "3wire"
    table_name = f"modbus_{wire_type}_{resolution}"
    
    # 전압 컬럼 (3상 4선 vs 3상 3선)
    voltage_col = "avg_voltage_ll_v" if is_4w else "avg_voltage_ln_v"
    
    # 에너지 데이터 가용성 (모든 해상도에서 사용 가능)
    energy_available = True
    
    return table_name, voltage_col, energy_available


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

def query_modbus_data(
    device_id: int,
    preset: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_points: int = 1440
) -> Dict[str, Any]:
    """
    Modbus 데이터 조회 (시간 해상도 자동 선택)
    
    Args:
        device_id: 디바이스 ID (11~15)
        preset: "1day", "1week", "1month", "1year"
        start: 시작 시각 (ISO format)
        end: 종료 시각 (ISO format)
        max_points: 최대 데이터 포인트 (기본 1440)
        
    Returns:
        dict: {
            "device_id": int,
            "wire_type": "4wire" | "3wire",
            "resolution": "1min" | "15min" | "1hour" | "1day",
            "start": ISO string (KST),
            "end": ISO string (KST),
            "data_points": int,
            "data": [
                {
                    "bucket": ISO string (KST),
                    "voltage": float,
                    "current": float,
                    "power": float,
                    "energy_delta": float,  # kWh (구간 소비량)
                    "peak_power": float (15분 이후만)
                },
                ...
            ]
        }
    """
    # 1. 시간 범위 및 해상도 결정
    start_dt, end_dt, resolution = _determine_resolution_and_range(preset, start, end)
    
    # 2. 테이블 및 컬럼 결정
    table_name, voltage_col, energy_available = _get_table_and_columns(device_id, resolution)
    
    # 3. 쿼리 작성 (해상도별 분기)
    if resolution == "1min":
        # 1분 집계: 전압/전류/전력/에너지 모두 사용 가능
        sql = f"""
            SELECT
                bucket,
                {voltage_col} AS voltage,
                avg_current_a AS current,
                avg_active_power_kw AS power,
                energy_delta_kwh AS energy_delta,
                data_points
            FROM {table_name}
            WHERE device_id = %s
              AND bucket >= %s
              AND bucket < %s
            ORDER BY bucket ASC
            LIMIT %s;
        """
    else:
        # 15분/1시간/1일 집계: 에너지와 피크 전력만 사용 가능
        sql = f"""
            SELECT
                bucket,
                NULL AS voltage,
                NULL AS current,
                peak_power_kw AS power,
                energy_delta_kwh AS energy_delta,
                peak_power_kw AS peak_power,
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
        
        item = {
            "bucket": bucket_ts.isoformat() if bucket_ts else None,
            "voltage": round(row[1], 2) if row[1] is not None else None,
            "current": round(row[2], 2) if row[2] is not None else None,
            "power": round(row[3], 2) if row[3] is not None else None,
            "energy_delta": round(row[4], 3) if row[4] is not None else None,
        }
        
        # 15분 이후 해상도에서는 peak_power 추가
        if resolution != "1min" and len(row) > 5:
            item["peak_power"] = round(row[5], 2) if row[5] is not None else None
        
        data.append(item)
    
    # 6. 응답 구성
    return {
        "device_id": device_id,
        "wire_type": "4wire" if _is_4wire(device_id) else "3wire",
        "resolution": resolution,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "data_points": len(data),
        "data": data,
    }


# ============================================================
# 실시간 데이터 조회
# ============================================================

def query_modbus_realtime(device_id: int) -> Optional[Dict[str, Any]]:
    """
    최신 원시 데이터 1건 조회 (실시간 모니터링용)
    
    Args:
        device_id: 디바이스 ID
        
    Returns:
        dict 또는 None
        {
            "time_stamp": ISO string (KST),
            "device_id": int,
            "voltage": float,
            "current": float,
            "power": float,
            "energy": float (누적값)
        }
    """
    # 디바이스 타입에 따라 전압 컬럼 선택
    voltage_col = "avg_line_to_line_volts_v" if _is_4wire(device_id) else "avg_line_to_neutral_volts_v"
    
    sql = f"""
        SELECT
            time_stamp,
            device_id,
            {voltage_col} AS voltage,
            sum_line_currents_a AS current,
            total_active_power_kw AS power,
            total_active_energy_kwh AS energy
        FROM modbus_data
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
        "voltage": round(row[2], 2) if row[2] is not None else None,
        "current": round(row[3], 2) if row[3] is not None else None,
        "power": round(row[4], 2) if row[4] is not None else None,
        "energy": round(row[5], 3) if row[5] is not None else None,
    }


# ============================================================
# 오늘 누적 에너지 계산
# ============================================================

def get_today_energy_kwh(device_id: int) -> Optional[float]:
    """
    오늘(KST 기준 00:00~현재) 누적 에너지 소비량 계산
    
    Args:
        device_id: 디바이스 ID
        
    Returns:
        float (kWh) 또는 None
        
    동작:
        - modbus_*wire_1day 테이블에서 오늘 날짜의 energy_delta_kwh 조회
        - 데이터가 없으면 modbus_*wire_1hour 테이블에서 합산
        - 그래도 없으면 None 반환
    """
    now_kst = datetime.now(KST)
    today_start = datetime.combine(now_kst.date(), time(0, 0, 0), tzinfo=KST)
    
    # 테이블명 결정
    wire_type = "4wire" if _is_4wire(device_id) else "3wire"
    
    # 1차 시도: 1일 집계 테이블에서 조회
    table_1day = f"modbus_{wire_type}_1day"
    sql_1day = f"""
        SELECT energy_delta_kwh
        FROM {table_1day}
        WHERE device_id = %s
          AND bucket = %s
        LIMIT 1;
    """
    
    with get_cursor() as cur:
        cur.execute(sql_1day, (device_id, today_start))
        row = cur.fetchone()
        if row and row[0] is not None:
            return round(float(row[0]), 3)
    
    # 2차 시도: 1시간 집계 테이블에서 합산
    table_1hour = f"modbus_{wire_type}_1hour"
    tomorrow_start = today_start + timedelta(days=1)
    sql_1hour = f"""
        SELECT SUM(energy_delta_kwh)
        FROM {table_1hour}
        WHERE device_id = %s
          AND bucket >= %s
          AND bucket < %s;
    """
    
    with get_cursor() as cur:
        cur.execute(sql_1hour, (device_id, today_start, tomorrow_start))
        row = cur.fetchone()
        if row and row[0] is not None:
            return round(float(row[0]), 3)
    
    return None


# ============================================================
# 통계 계산
# ============================================================

def get_device_statistics(device_id: int, days: int = 7) -> Dict[str, Any]:
    """
    디바이스 통계 계산 (최근 N일간)
    
    Args:
        device_id: 디바이스 ID
        days: 통계 기간 (일)
        
    Returns:
        dict: {
            "total_energy_kwh": float,
            "avg_power_kw": float,
            "peak_power_kw": float,
            "period_days": int
        }
    """
    now_kst = datetime.now(KST)
    start_dt = now_kst - timedelta(days=days)
    
    wire_type = "4wire" if _is_4wire(device_id) else "3wire"
    table_name = f"modbus_{wire_type}_1day"
    
    sql = f"""
        SELECT
            SUM(energy_delta_kwh) AS total_energy,
            AVG(peak_power_kw) AS avg_power,
            MAX(peak_power_kw) AS peak_power
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
            "total_energy_kwh": 0.0,
            "avg_power_kw": 0.0,
            "peak_power_kw": 0.0,
            "period_days": days,
        }
    
    return {
        "total_energy_kwh": round(float(row[0]), 3) if row[0] else 0.0,
        "avg_power_kw": round(float(row[1]), 2) if row[1] else 0.0,
        "peak_power_kw": round(float(row[2]), 2) if row[2] else 0.0,
        "period_days": days,
    }
