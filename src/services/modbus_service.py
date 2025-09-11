"""
modbus_service.py
- modbus_data 테이블에서 조회 및 집계
"""

from typing import List, Dict, Union, Callable
from datetime import datetime, timedelta
from src.db.client import get_cursor

# 장치 타입 구분
THREE_WIRE_IDS = [11, 12, 13]
FOUR_WIRE_IDS = [14, 15]

def resolve_voltage_col(device_id: int) -> str:
    if device_id in [11, 12, 13]:
        return "avg_line_to_line_volts_v"
    elif device_id in [14, 15]:
        return "avg_line_to_neutral_volts_v"
    return "avg_line_to_line_volts_v"

BUCKET_MAP = {
    "15m": "1 minute",
    "1h": "5 minutes",
    "1d": "1 hour",
    "1w": "6 hours",
    "1mo": "1 day",
}

# 프론트에서 사용할 키 → DB 컬럼 매핑
SERIES_MAP: Dict[str, Union[str, Callable[[int], str]]] = {
    "voltage": resolve_voltage_col,
    "current": "sum_line_currents_a",
    "power": "total_active_power_kw",
    "energy": "total_active_energy_kWh",
}

def resolve_window(preset, start, end):
    now = datetime.utcnow()
    if preset and not (start or end):
        if preset == "15m": return now - timedelta(minutes=15), now
        if preset == "1h": return now - timedelta(hours=1), now
        if preset == "1d": return now - timedelta(days=1), now
        if preset == "1w": return now - timedelta(weeks=1), now
        if preset == "1mo": return now - timedelta(days=30), now
    s = datetime.fromisoformat(start) if start else now - timedelta(hours=1)
    e = datetime.fromisoformat(end) if end else now
    return s, e

def normalize_series(device_id: int, series: List[str]) -> Dict[str, str]:
    mapping = {}
    for s in series:
        if s in SERIES_MAP:
            val = SERIES_MAP[s]
            mapping[s] = val(device_id) if callable(val) else val
        else:
            mapping[s] = s
    return mapping

def query_modbus_window(device_id: int, series: List[str], preset=None, start=None, end=None):
    s, e = resolve_window(preset, start, end)
    bucket_str = BUCKET_MAP.get(preset, "1 hour")
    mapping = normalize_series(device_id, series)

    select_cols = [f'avg({db_col}) AS "{front_key}"' for front_key, db_col in mapping.items()]
    sql = f"""
      SELECT time_bucket(%s, time_stamp) AS bucket, {",".join(select_cols)}
      FROM modbus_data
      WHERE device_id=%s AND time_stamp BETWEEN %s AND %s
      GROUP BY bucket ORDER BY bucket;
    """
    params = [bucket_str, device_id, s, e]

    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        colnames = [d[0] for d in cur.description]

    data = []
    for r in rows:
        item = {"bucket": r[0].isoformat()}
        for idx, name in enumerate(colnames[1:], start=1):
            v = r[idx]
            item[name] = round(float(v), 2) if v is not None else None
        data.append(item)

    stats = _compute_stats(data, list(mapping.keys()))
    return {
        "window": {"start": s.isoformat(), "end": e.isoformat()},
        "bucket": bucket_str,
        "device_id": device_id,
        "series": list(mapping.keys()),
        "data": data,
        "stats": stats,
    }

def query_modbus_realtime(device_id: int):
    """실시간 최신 1개 레코드 조회"""
    sql = """
        SELECT time_stamp, device_id,
               total_active_power_kw, sum_line_currents_a,
               avg_line_to_line_volts_v, total_active_energy_kWh
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
            "device_id": row[1],
            "power": row[2],    # total_active_power_kw
            "current": row[3],  # sum_line_currents_a
            "voltage": row[4],  # avg_line_to_line_volts_v
            "energy": row[5],   # total_active_energy_kWh
        }


def _compute_stats(rows: List[Dict], keys: List[str]) -> Dict[str, Dict]:
    stats = {}
    for k in keys:
        vals = [float(r[k]) for r in rows if r.get(k) is not None]
        if vals:
            stats[k] = {
                "avg": round(sum(vals) / len(vals), 2),
                "max": round(max(vals), 2),
                "min": round(min(vals), 2),
                "count": len(vals),
            }
        else:
            stats[k] = {"avg": None, "max": None, "min": None, "count": 0}
    return stats
