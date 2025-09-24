"""
src/services/modbus_service.py

Modbus(전력량계) 관련 서비스 함수
- query_modbus_window: 집계(히스토리) 쿼리 반환 (make_query_response 형태)
- query_modbus_realtime: 최신 1건 조회 (dict)
- 반환되는 모든 시간(bucket/time_stamp)은 KST tz-aware ISO 문자열로 통일
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo

from src.db.client import get_cursor
from src.api._utils import iso_kst, make_query_response

KST = ZoneInfo("Asia/Seoul")

# 프론트 시리즈 키 -> DB 컬럼 매핑
SERIES_MAP = {
    "power": "total_active_power_kw",
    "current": "sum_line_currents_a",
    "voltage": "avg_line_to_line_volts_v",
    "energy": "total_active_energy_kwh",
    "pf": "total_power_factor"
}


def _compute_stats(rows: List[Dict[str, Any]], keys: List[str]) -> Dict[str, Dict]:
    """
    간단 통계(avg/max/min/count) 계산
    """
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


def query_modbus_window(device_id: int,
                        series: List[str],
                        preset: Optional[str] = None,
                        start: Optional[str] = None,
                        end: Optional[str] = None,
                        max_points: int = 1000) -> Dict[str, Any]:
    """
    윈도우 쿼리 수행
    - device_id: 장치 ID
    - series: 프론트 키 목록 (예: ["power","energy"])
    - preset 또는 start/end 사용
    - 반환: make_query_response 포맷
    """
    # 1) window 계산 (UTC 기준 내부 계산)
    now = datetime.now(timezone.utc)
    if preset and not (start or end):
        if preset == "15m":
            s, e, bucket = now - timedelta(minutes=15), now, "1 minute"
        elif preset == "1h":
            s, e, bucket = now - timedelta(hours=1), now, "5 minutes"
        elif preset == "1d":
            s, e, bucket = now - timedelta(days=1), now, "1 hour"
        elif preset == "1w":
            s, e, bucket = now - timedelta(weeks=1), now, "6 hours"
        else:
            s, e, bucket = now - timedelta(days=30), now, "1 day"
    else:
        e = datetime.fromisoformat(end) if end else now
        s = datetime.fromisoformat(start) if start else (e - timedelta(hours=1))
        # ensure tz-aware UTC
        if s.tzinfo is None:
            s = s.replace(tzinfo=timezone.utc)
        if e.tzinfo is None:
            e = e.replace(tzinfo=timezone.utc)
        bucket = "1 hour"

    # 2) SQL 작성: time_bucket 기반 집계 (단순화)
    mapping = {k: SERIES_MAP.get(k, k) for k in series}
    select_cols = [f'avg({db_col}) AS "{front_key}"' for front_key, db_col in mapping.items()]

    sql = f"""
      SELECT time_bucket(%s, time_stamp) AS bucket, {', '.join(select_cols)}
      FROM modbus_data
      WHERE device_id = %s AND time_stamp BETWEEN %s AND %s
      GROUP BY bucket
      ORDER BY bucket DESC
      LIMIT %s;
    """
    params = [bucket, device_id, s, e, max_points]

    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        colnames = [d[0] for d in cur.description]  # first is bucket

    # 3) 결과 정규화: bucket -> KST ISO, 소수 반올림
    data: List[Dict[str, Any]] = []
    for r in rows:
        bucket_ts = r[0]
        if bucket_ts is not None and bucket_ts.tzinfo is None:
            # DB 드라이버가 naive timestamp를 줄 수 있음. KST로 간주하여 tz 부착
            bucket_ts = bucket_ts.replace(tzinfo=KST)
        item: Dict[str, Any] = {"bucket": iso_kst(bucket_ts)}
        for idx, name in enumerate(colnames[1:], start=1):
            v = r[idx]
            item[name] = round(float(v), 2) if v is not None else None
        data.append(item)

    stats = _compute_stats(data, list(mapping.keys()))
    return make_query_response(s, e, bucket, list(mapping.keys()), data, stats)


def query_modbus_realtime(device_id: int) -> Optional[Dict[str, Any]]:
    """
    최신 1건 반환
    - 반환 dict 형태(시간은 KST ISO)
    - None 반환 시 호출자에서 503 처리 권장
    """
    sql = """
        SELECT time_stamp, device_id,
               total_active_power_kw, sum_line_currents_a,
               avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
               total_active_energy_kwh
        FROM modbus_data
        WHERE device_id = %s
        ORDER BY time_stamp DESC
        LIMIT 1;
    """
    with get_cursor() as cur:
        cur.execute(sql, [device_id])
        row = cur.fetchone()
        if not row:
            return None

        ts = row[0]
        if ts is not None and ts.tzinfo is None:
            ts = ts.replace(tzinfo=KST)

        return {
            "time_stamp": iso_kst(ts),
            "device_id": row[1],
            "power": row[2],
            "current": row[3],
            "voltage_ll": row[4],
            "voltage_ln": row[5],
            "energy": row[6],
        }

def get_today_energy_kwh(device_id: int):
    """
    device_id의 '오늘'(KST 기준) 누적 에너지 차이 계산.
    반환: float (kWh) 또는 None (데이터 없음)
    동작:
      - KST의 00:00:00 ~ 다음날 00:00:00 범위를 UTC로 변환하여 DB 조회
      - DB에서 해당 컬럼의 min/max를 읽어 delta 계산
      - 컬럼이 비어있으면 e_kwh 같은 대체 이름도 시도
    """
    # compute KST today 00:00 and next day 00:00, then convert to UTC for timestamptz query
    now_kst = datetime.now(KST)
    today_kst_start = datetime.combine(now_kst.date(), time(0, 0, 0), tzinfo=KST)
    tomorrow_kst_start = datetime.combine(now_kst.date(), time(0, 0, 0), tzinfo=KST) + timedelta(days=1)

    # convert to UTC for querying timestamptz
    start_utc = today_kst_start.astimezone(timezone.utc)
    end_utc = tomorrow_kst_start.astimezone(timezone.utc)

    with get_cursor() as cur:
        # try primary column name first
        cur.execute("""
            SELECT MIN(total_active_energy_kwh) AS mn, MAX(total_active_energy_kwh) AS mx
            FROM modbus_data
            WHERE device_id=%s AND time_stamp >= %s AND time_stamp < %s
        """, (device_id, start_utc, end_utc))
        mn_mx = cur.fetchone()
        if mn_mx and (mn_mx[0] is not None or mn_mx[1] is not None):
            mn, mx = mn_mx
            if mn is None or mx is None:
                return None
            return float(mx) - float(mn)

        # fallback: try alternate column name e_kwh
        cur.execute("""
            SELECT MIN(total_active_energy_kwh) AS mn, MAX(total_active_energy_kwh) AS mx
            FROM modbus_data
            WHERE device_id=%s AND time_stamp >= %s AND time_stamp < %s
        """, (device_id, start_utc, end_utc))
        mn_mx2 = cur.fetchone()
        if mn_mx2 and (mn_mx2[0] is not None or mn_mx2[1] is not None):
            mn, mx = mn_mx2
            if mn is None or mx is None:
                return None
            return float(mx) - float(mn)

    return None