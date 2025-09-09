"""
Modbus 서비스 레이어(강화판)
- 장치 그룹(3상3선/3상4선) 정의
- 기간(window) 해석 + 버킷 크기 자동 결정(max_points 상한)
- 지정 컬럼들의 평균/최대/최소/개수 통계 계산
- 장치별 전압 컬럼 분기(v_ll vs v_ln) 지원
"""
from __future__ import annotations
from typing import Dict, List, Tuple
from datetime import datetime, timedelta, timezone
from math import ceil
from src.db.client import get_cursor

# === 3상 구성별 장치 그룹 ===
THREE_WIRE_IDS = {11, 12, 13}  # 3상3선
FOUR_WIRE_IDS  = {14, 15}      # 3상4선
ALL_DEVICE_IDS = THREE_WIRE_IDS | FOUR_WIRE_IDS

# === UI 시리즈 키 → DB 컬럼 매핑 ===
#  - p_total, q_total, s_total, pf_total: 집계 시 사용되는 alias
#  - voltage/current: 구성별 전압/전류 표현을 위한 alias
SERIES_MAP_BASE = {
    "p_total":  "total_active_power_kW",
    "q_total":  "total_reactive_power_kvar",
    "s_total":  "total_apparent_power_kVA",
    "pf_total": "total_power_factor",  # raw 컬럼명: avg_power_factor 또는 total_power_factor 계열
    "current":  "sum_line_currents_A",
}
# 전압은 구성별로 달라짐: 3선=v_ll, 4선=v_ln
def resolve_voltage_col(device_id: int) -> str:
    if device_id in THREE_WIRE_IDS:
        return "avg_line_to_line_volts_V"
    return "avg_line_to_neutral_volts_V"

# === 프리셋 기간 ===
PRESET_MAP: Dict[str, timedelta] = {
    "15m": timedelta(minutes=15),
    "1h":  timedelta(hours=1),
    "1d":  timedelta(days=1),
    "1w":  timedelta(weeks=1),
    "1mo": timedelta(days=30),
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
    if not preset:
        preset = "1h"
    span = PRESET_MAP.get(preset)
    if not span:
        raise ValueError("invalid preset")
    return now - span, now

def choose_bucket_seconds(start: datetime, end: datetime, max_points: int) -> int:
    """
    최대 반환 포인트 개수(max_points)를 넘지 않도록 time_bucket 크기(초)를 산출.
    - PC 성능 보호를 위한 핵심 제어 지점
    """
    duration = max(1, int((end - start).total_seconds()))
    mp = max(50, int(max_points or 300))  # 최소 안전선 50포인트
    secs = ceil(duration / mp)
    return max(1, min(secs, 24*3600))  # 최소 1초, 최대 1일

def seconds_to_interval_str(secs: int) -> str:
    return f"{int(secs)} seconds"

def build_series_select(device_id: int, series_keys: List[str]) -> Tuple[str, List[str]]:
    """
    선택된 series 목록을 SQL SELECT 절용으로 변환.
    - device_id에 따라 voltage 컬럼을 분기한다.
    - avg() 집계로 버킷 단위의 평균값을 냄.
    """
    cols: List[str] = []
    aliases: List[str] = []
    for key in series_keys:
        if key == "voltage":
            dbcol = resolve_voltage_col(device_id)
        else:
            dbcol = SERIES_MAP_BASE.get(key)
        if not dbcol:
            continue
        cols.append(f"avg({dbcol}) AS {key}")
        aliases.append(key)
    if not cols:
        # 기본은 유효전력
        cols = ["avg(total_active_power_kW) AS p_total"]
        aliases = ["p_total"]
    return ", ".join(cols), aliases

def compute_stats(rows: List[Dict], aliases: List[str]) -> Dict[str, Dict]:
    """각 시리즈별 평균/최대/최소/개수 계산"""
    stats: Dict[str, Dict] = {}
    for key in aliases:
        vals = [float(r[key]) for r in rows if r.get(key) is not None]
        if vals:
            stats[key] = {
                "avg": round(sum(vals)/len(vals), 3 if key == "pf_total" else 2),
                "max": round(max(vals),          3 if key == "pf_total" else 2),
                "min": round(min(vals),          3 if key == "pf_total" else 2),
                "count": len(vals),
            }
        else:
            stats[key] = {"avg": None, "max": None, "min": None, "count": 0}
    return stats

def query_modbus_window(
    device_id: int,
    series_keys: List[str],
    preset: str|None,
    start: str|None,
    end: str|None,
    max_points: int = 300,
) -> Dict:
    """
    조건형 조회
    - device_id별 전압 컬럼 분기
    - 기간을 버킷으로 나눠 평균값 반환
    - 통계(평균/최대/최소/개수) 포함
    - 서버측 max_points 강제 → bucket_seconds로 노출
    """
    if device_id not in ALL_DEVICE_IDS:
        raise ValueError("unknown device_id")

    s, e = resolve_window(preset, start, end)
    bucket_secs = choose_bucket_seconds(s, e, max_points)
    bucket_str = seconds_to_interval_str(bucket_secs)

    select_series, aliases = build_series_select(device_id, series_keys)

    sql = f"""
        SELECT time_bucket(%s, time_stamp) AS bucket,
               {select_series}
        FROM modbus_data
        WHERE device_id = %s
          AND time_stamp >= %s AND time_stamp <= %s
        GROUP BY bucket
        ORDER BY bucket;
    """
    params = [bucket_str, device_id, s, e]

    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        colnames = [d[0] for d in cur.description]

    # dict 변환
    out_rows: List[Dict] = []
    for r in rows:
        item = {"bucket": r[0].isoformat()}
        for idx, name in enumerate(colnames[1:], start=1):
            v = r[idx]
            item[name] = round(float(v), 3) if v is not None else None
        out_rows.append(item)

    stats = compute_stats(out_rows, aliases)
    limited = len(out_rows) > max_points  # 이론상 bucket_secs가 이를 방지하지만 플래그 제공
    if limited:
        out_rows = out_rows[-max_points:]

    return {
        "window": {"start": s.isoformat(), "end": e.isoformat()},
        "bucket_seconds": bucket_secs,
        "limited": limited,
        "device_id": device_id,
        "series": aliases,
        "data": out_rows,
        "stats": stats,
    }
