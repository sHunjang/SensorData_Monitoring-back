"""
modbus_service.py
- 전력량계(modbus_data) 조회 및 통계 계산 로직
- 프론트에서는 series=voltage|current|power|energy 같은 단순 키만 사용
"""

from typing import List, Dict, Optional, Union, Callable
from datetime import datetime, timedelta
from src.db.client import get_cursor

# TAC4300 장치 ID 구분
THREE_WIRE_IDS = [11, 12, 13]  # 3상 3선
FOUR_WIRE_IDS  = [14, 15]      # 3상 4선

def resolve_voltage_col(device_id: int) -> str:
    """장치 ID에 따라 전압 컬럼명을 반환"""
    if device_id in THREE_WIRE_IDS:
        return "avg_line_to_line_volts_V"
    if device_id in FOUR_WIRE_IDS:
        return "avg_line_to_neutral_volts_V"
    return "avg_line_to_line_volts_V"

# 프리셋별 버킷 단위 매핑
BUCKET_MAP = {
    "15m": "1 minute",
    "1h": "5 minutes",
    "1d": "1 hour",
    "1w": "6 hours",
    "1mo": "1 day",
}

# 프론트 단순 키 → DB 실제 컬럼명 매핑
SERIES_MAP: Dict[str, Union[str, Callable[[int], str]]] = {
    "voltage": resolve_voltage_col,
    "current": "sum_line_currents_A",
    "power": "total_active_power_kW",
    "energy": "total_active_energy_kWh",
}

def resolve_window(preset: Optional[str], start: Optional[str], end: Optional[str]) -> tuple[datetime, datetime]:
    """기간 프리셋 또는 직접 지정 기간을 기준으로 start/end 계산"""
    now = datetime.utcnow()
    if preset and not (start or end):
        if preset == "15m":
            return now - timedelta(minutes=15), now
        if preset == "1h":
            return now - timedelta(hours=1), now
        if preset == "1d":
            return now - timedelta(days=1), now
        if preset == "1w":
            return now - timedelta(weeks=1), now
        if preset == "1mo":
            return now - timedelta(days=30), now
    # 직접 지정
    s = datetime.fromisoformat(start) if start else now - timedelta(hours=1)
    e = datetime.fromisoformat(end) if end else now
    return s, e

def normalize_series(device_id: int, series: List[str]) -> Dict[str, str]:
    """
    프론트에서 보낸 series 키를 DB 실제 컬럼명으로 변환
    반환: {프론트키 → DB컬럼명}
    """
    mapping: Dict[str, str] = {}
    for s in series:
        if s in SERIES_MAP:
            val = SERIES_MAP[s]
            mapping[s] = val(device_id) if callable(val) else val
        else:
            mapping[s] = s
    return mapping

def query_modbus_window(
    device_id: int,
    series: List[str],
    preset: Optional[str],
    start: Optional[str],
    end: Optional[str],
) -> Dict:
    """기간별 집계 조회"""
    s, e = resolve_window(preset, start, end)
    bucket_str = BUCKET_MAP.get(preset, "1 hour")

    mapping = normalize_series(device_id, series)

    # SELECT 동적 생성 (항상 alias를 프론트 단순 키로 고정)
    select_cols = []
    for front_key, db_col in mapping.items():
        select_cols.append(f'avg({db_col}) AS "{front_key}"')
    select_sql = ", ".join(select_cols)

    sql = f"""
        SELECT time_bucket(%s, time_stamp) AS bucket,
               {select_sql}
        FROM modbus_data
        WHERE device_id=%s AND time_stamp >= %s AND time_stamp <= %s
        GROUP BY bucket
        ORDER BY bucket;
    """
    params = [bucket_str, device_id, s, e]

    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        colnames = [d[0] for d in cur.description]

    data: List[Dict] = []
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
        "series": list(mapping.keys()),  # ✅ 프론트 단순 키 그대로 반환
        "data": data,
        "stats": stats,
    }

def query_modbus_realtime(device_id: int) -> Optional[Dict]:
    """modbus_data 테이블에서 가장 최근 1개 레코드를 반환"""
    sql = """
        SELECT time_stamp, device_id,
               total_active_power_kW,
               sum_line_currents_A,
               avg_line_to_line_volts_V,
               avg_line_to_neutral_volts_V,
               total_active_energy_kWh
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
            "power": row[2],    # ✅ alias 단순 키
            "current": row[3],
            "voltage_ll": row[4],  # 참고용
            "voltage_ln": row[5],  # 참고용
            "energy": row[6],
        }

def _compute_stats(rows: List[Dict], keys: List[str]) -> Dict[str, Dict]:
    """통계값 계산 (평균, 최대, 최소, 데이터 개수)"""
    stats: Dict[str, Dict] = {}
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
