"""
modbus_service.py
- modbus_data 조회 및 집계
- 컬럼명/스케일 프런트 대응
- KST 윈도우 계산 및 표시(ISO 문자열)
"""
from typing import List, Dict, Union, Callable
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from src.db.client import get_cursor

# 장치 타입(쿼리 전압 컬럼 선택에 사용)
THREE_WIRE_IDS = [11, 12, 13]  # 3상 3선 → LL
FOUR_WIRE_IDS  = [14, 15]      # 3상 4선 → LN

def resolve_voltage_col(device_id: int) -> str:
    return "avg_line_to_line_volts_v" if device_id in THREE_WIRE_IDS else "avg_line_to_neutral_volts_v"

# 집계 버킷(초기 운영 값)
BUCKET_MAP = {
    "15m": "1 minute",
    "1h":  "5 minutes",
    "1d":  "1 hour",
    "1w":  "6 hours",
    "1mo": "1 day",
}

# 프론트 키 ↔ DB 컬럼
SERIES_MAP: Dict[str, Union[str, Callable[[int], str]]] = {
    "voltage": resolve_voltage_col,
    "current": "sum_line_currents_a",
    "power":   "total_active_power_kw",
    "energy":  "total_active_energy_kwh",
}

def resolve_window(preset, start, end):
    """
    질의 윈도우 해석.
    - 내부 연산은 UTC로 통일.
    - start/end ISO가 있으면 우선.
    """
    now = datetime.now(timezone.utc)
    if preset and not (start or end):
        if preset == "15m": return now - timedelta(minutes=15), now
        if preset == "1h":  return now - timedelta(hours=1), now
        if preset == "1d":  return now - timedelta(days=1), now
        if preset == "1w":  return now - timedelta(weeks=1), now
        if preset == "1mo": return now - timedelta(days=30), now
    s = datetime.fromisoformat(start).astimezone(timezone.utc) if start else now - timedelta(hours=1)
    e = datetime.fromisoformat(end).astimezone(timezone.utc)   if end   else now
    return s, e

def normalize_series(device_id: int, series: List[str]) -> Dict[str, str]:
    """
    프론트 series 목록을 DB 컬럼으로 매핑.
    - callable이면 device_id에 따라 컬럼 결정
    """
    mapping = {}
    for s in series:
        if s in SERIES_MAP:
            val = SERIES_MAP[s]
            mapping[s] = val(device_id) if callable(val) else val
        else:
            mapping[s] = s
    return mapping

def query_modbus_window(device_id: int, series: List[str], preset=None, start=None, end=None):
    """
    윈도우 구간 집계.
    - time_bucket 사용(타임스케일 확장)
    - 응답 시간은 KST로 ISO 문자열로 반환
    """
    s, e = resolve_window(preset, start, end)
    bucket_str = BUCKET_MAP.get(preset, "1 hour")
    mapping = normalize_series(device_id, series)

    select_cols = [f'avg({db_col}) AS "{front_key}"' for front_key, db_col in mapping.items()]
    sql = f"""
      SELECT time_bucket(%s, time_stamp) AT TIME ZONE 'Asia/Seoul' AS bucket_kst, {",".join(select_cols)}
      FROM modbus_data
      WHERE device_id=%s AND time_stamp BETWEEN %s AND %s
      GROUP BY bucket_kst
      ORDER BY bucket_kst;
    """
    params = [bucket_str, device_id, s, e]

    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        colnames = [d[0] for d in cur.description]

    data = []
    for r in rows:
        item = {"bucket": r[0].isoformat()}  # KST naive → ISO 문자열
        for idx, name in enumerate(colnames[1:], start=1):
            v = r[idx]
            item[name] = round(float(v), 2) if v is not None else None
        data.append(item)

    stats = _compute_stats(data, list(mapping.keys()))
    # 응답 메타 시간도 KST로 표기
    kst = ZoneInfo("Asia/Seoul")
    return {
        "window": {"start": s.astimezone(kst).isoformat(), "end": e.astimezone(kst).isoformat()},
        "bucket": bucket_str,
        "device_id": device_id,
        "series": list(mapping.keys()),
        "data": data,
        "stats": stats,
    }

def query_modbus_realtime(device_id: int):
    """
    실시간 최신 1개 레코드 조회.
    - 시간은 KST로 반환
    - 전압은 LL/LN 둘 다 제공하여 프론트 판단 여지 제공
    """
    sql = """
        SELECT
            (time_stamp AT TIME ZONE 'Asia/Seoul') AS time_kst,
            device_id,
            total_active_power_kw,
            sum_line_currents_a,
            avg_line_to_line_volts_v,
            avg_line_to_neutral_volts_v,
            total_active_energy_kwh
        FROM modbus_data
        WHERE device_id=%s
        ORDER BY time_stamp DESC
        LIMIT 1;
    """
    with get_cursor() as cur:
        cur.execute(sql, [device_id])
        row = cur.fetchone()
        if not row:
            return None
        return {
            "time_stamp": row[0].isoformat(),
            "device_id":  row[1],
            "power":      row[2],
            "current":    row[3],
            "voltage_ll": row[4],
            "voltage_ln": row[5],
            "energy":     row[6],
        }

def _compute_stats(rows: List[Dict], keys: List[str]) -> Dict[str, Dict]:
    stats = {}
    for k in keys:
        vals = [float(r[k]) for r in rows if r.get(k) is not None]
        stats[k] = {
            "avg": round(sum(vals) / len(vals), 2),
            "max": round(max(vals), 2),
            "min": round(min(vals), 2),
            "count": len(vals),
        } if vals else {"avg": None, "max": None, "min": None, "count": 0}
    return stats
