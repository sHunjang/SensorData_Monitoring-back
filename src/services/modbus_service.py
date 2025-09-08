"""
Modbus 서비스 레이어
- 기간(window) 계산, 버킷 크기 산출, 데이터 집계 + 통계
- 다중 장치(device_id) 구분 지원
"""
from __future__ import annotations
from typing import Dict, List, Tuple
from datetime import datetime, timedelta, timezone
from math import ceil
from src.db.client import get_cursor

# series 키 → DB 컬럼명 매핑
SERIES_MAP = {
    "voltage": "avg_voltage_V",
    "current": "sum_current_A",
    "p_total": "total_active_kW",
    "q_total": "total_reactive_kvar",
    "s_total": "total_apparent_kVA",
    "pf_total": "total_power_factor",
}

# 프리셋 문자열 → 기간 길이
PRESET_MAP = {
    "15m":  timedelta(minutes=15),
    "1h":   timedelta(hours=1),
    "1d":   timedelta(days=1),
    "1w":   timedelta(weeks=1),
    "1mo":  timedelta(days=30),  # 단순화
}

def resolve_window(preset: str|None, start: str|None, end: str|None) -> Tuple[datetime, datetime]:
    """프리셋 또는 수동 start/end로 조회 구간 결정"""
    now = datetime.now(timezone.utc)
    if start and end:
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end)
        if s.tzinfo is None: s = s.replace(tzinfo=timezone.utc)
        if e.tzinfo is None: e = e.replace(tzinfo=timezone.utc)
        if e <= s:
            raise ValueError("end must be greater than start")
        return s, e
    if preset is None:
        preset = "1h"
    span = PRESET_MAP.get(preset)
    if span is None:
        raise ValueError("invalid preset")
    return now - span, now

def choose_bucket_seconds(start: datetime, end: datetime, max_points: int) -> int:
    """데이터 개수 제한을 넘지 않도록 버킷 크기(초)를 계산"""
    duration = (end - start).total_seconds()
    if duration <= 0:
        raise ValueError("invalid window")
    if max_points <= 0:
        max_points = 100
    secs = ceil(duration / max_points)
    return max(1, min(secs, 24*3600))  # 최소 1초, 최대 1일

def seconds_to_interval_str(secs: int) -> str:
    """TimescaleDB time_bucket 간격 문자열"""
    return f"{int(secs)} seconds"

def query_modbus_window(
    series_keys: List[str],
    preset: str|None,
    start: str|None,
    end: str|None,
    max_points: int = 300,
    device_id: int|None = None,
) -> Dict:
    """조건형 조회 (시리즈 선택 + 기간 + 통계 + 다중 장치 구분)"""
    s, e = resolve_window(preset, start, end)
    bucket_secs = choose_bucket_seconds(s, e, max_points)
    bucket_str = seconds_to_interval_str(bucket_secs)

    # 유효 시리즈만 선택
    cols: List[Tuple[str, str]] = []
    for key in series_keys:
        col = SERIES_MAP.get(key)
        if col:
            cols.append((key, col))
    if not cols:
        cols = [("p_total", "total_active_kW")]

    # SELECT 절 구성
    select_series = ", ".join([f"avg({dbcol}) AS {alias}" for alias, dbcol in cols])

    # device_id 조건 반영
    sql = f"""
        SELECT time_bucket(%s, time_stamp) AS bucket,
               {select_series}
        FROM modbus_data
        WHERE time_stamp >= %s AND time_stamp <= %s
        {"AND device_id = %s" if device_id else ""}
        GROUP BY bucket
        ORDER BY bucket;
    """
    params = [bucket_str, s, e]
    if device_id:
        params.append(device_id)

    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]

    # dict 리스트로 변환
    data: List[Dict] = []
    for r in rows:
        item = {"bucket": r[0].isoformat()}
        for i, name in enumerate(colnames[1:], start=1):
            v = r[i]
            if v is not None:
                item[name] = round(float(v), 3 if name == "pf_total" else 2)
            else:
                item[name] = None
        data.append(item)

    # 포인트 제한
    if len(data) > max_points:
        data = data[-max_points:]

    # 통계 계산
    stats: Dict[str, Dict[str, float|int|None]] = {}
    for alias, _ in cols:
        vals = [d.get(alias) for d in data if d.get(alias) is not None]
        if vals:
            stats[alias] = {
                "avg": round(sum(vals)/len(vals), 3 if alias == "pf_total" else 2),
                "max": round(max(vals),          3 if alias == "pf_total" else 2),
                "min": round(min(vals),          3 if alias == "pf_total" else 2),
                "count": len(vals),
            }
        else:
            stats[alias] = {"avg": None, "max": None, "min": None, "count": 0}

    return {
        "window": {"start": s.isoformat(), "end": e.isoformat()},
        "bucket_seconds": bucket_secs,
        "series": [alias for alias, _ in cols],
        "device_id": device_id,
        "data": data,
        "stats": stats,
    }
