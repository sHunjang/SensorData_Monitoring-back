"""
src/services/modbus_service.py

Modbus(전력량계) 관련 서비스 함수
- query_modbus_window: 집계(히스토리) 쿼리 반환 (집계 자동 선택 포함)
- query_modbus_realtime: 최신 1건 조회 (dict)
- 반환되는 모든 시간(bucket/time_stamp)은 KST tz-aware ISO 문자열로 통일
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo

from src.db.client import get_cursor
from src.api._utils import iso_kst, make_query_response
from src.utils.aggregation_selector import (
    select_aggregation_level,
    get_table_suffix,
    get_time_column,
    get_column_prefix
)

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
    """간단 통계(avg/max/min/count) 계산"""
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
    윈도우 쿼리 수행 (집계 자동 선택)
    
    - device_id: 장치 ID
    - series: 프론트 키 목록 (예: ["power","energy"])
    - preset 또는 start/end 사용
    - 시간 범위에 따라 자동으로 적절한 집계 테이블 선택
    - 반환: make_query_response 포맷
    """
    # 1) window 계산 (UTC 기준 내부 계산)
    now = datetime.now(timezone.utc)
    if preset and not (start or end):
        if preset == "15m":
            s, e = now - timedelta(minutes=15), now
        elif preset == "1h":
            s, e = now - timedelta(hours=1), now
        elif preset == "1d":
            s, e = now - timedelta(days=1), now
        elif preset == "1w":
            s, e = now - timedelta(weeks=1), now
        else:
            s, e = now - timedelta(days=30), now
    else:
        e = datetime.fromisoformat(end) if end else now
        s = datetime.fromisoformat(start) if start else (e - timedelta(hours=1))
        # ensure tz-aware UTC
        if s.tzinfo is None:
            s = s.replace(tzinfo=timezone.utc)
        if e.tzinfo is None:
            e = e.replace(tzinfo=timezone.utc)

    # 2) 집계 레벨 자동 선택
    agg_level, bucket_interval = select_aggregation_level(s, e)
    table_suffix = get_table_suffix(agg_level)
    time_col = get_time_column(agg_level)
    avg_prefix, max_prefix, min_prefix = get_column_prefix(agg_level)

    # 테이블 이름 생성
    if agg_level == "raw":
        table_name = f"modbus_data_{device_id}"
    else:
        table_name = f"agg_modbus_{device_id}{table_suffix}"

    # 3) SQL 작성: time_bucket 기반 집계
    mapping = {k: SERIES_MAP.get(k, k) for k in series}
    
    # 컬럼 선택 (집계 레벨에 따라 avg_ prefix 추가)
    if agg_level == "raw":
        # 원천 데이터: 그대로 사용
        select_cols = [f'{db_col} AS "{front_key}"' for front_key, db_col in mapping.items()]
    else:
        # 집계 데이터: avg_ prefix 사용
        select_cols = [f'{avg_prefix}{db_col} AS "{front_key}"' for front_key, db_col in mapping.items()]

    sql = f"""
      SELECT time_bucket(%s, {time_col}) AS bucket, {', '.join(select_cols)}
      FROM {table_name}
      WHERE {time_col} BETWEEN %s AND %s
      GROUP BY bucket
      ORDER BY bucket DESC
      LIMIT %s;
    """
    params = [bucket_interval, s, e, max_points]

    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        colnames = [d[0] for d in cur.description]  # first is bucket

    # 4) 결과 정규화: bucket -> KST ISO, 소수 반올림
    data: List[Dict[str, Any]] = []
    for r in rows:
        bucket_ts = r[0]
        if bucket_ts is not None and bucket_ts.tzinfo is None:
            bucket_ts = bucket_ts.replace(tzinfo=KST)
        item: Dict[str, Any] = {
            "bucket": iso_kst(bucket_ts),
            "aggregation_level": agg_level  # 프론트에 전달
        }
        for idx, name in enumerate(colnames[1:], start=1):
            v = r[idx]
            item[name] = round(float(v), 2) if v is not None else None
        data.append(item)

    stats = _compute_stats(data, list(mapping.keys()))
    
    response = make_query_response(s, e, bucket_interval, list(mapping.keys()), data, stats)
    response["aggregation_level"] = agg_level  # 응답에 집계 레벨 추가
    response["table_used"] = table_name  # 디버깅용
    
    return response


def query_modbus_realtime(device_id: int) -> Optional[Dict[str, Any]]:
    """
    최신 1건 반환 (원천 데이터에서)
    - 반환 dict 형태(시간은 KST ISO)
    - None 반환 시 호출자에서 503 처리 권장
    """
    sql = f"""
        SELECT time_stamp, device_id,
               total_active_power_kw, sum_line_currents_a,
               avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
               total_active_energy_kwh
        FROM modbus_data_{device_id}
        ORDER BY time_stamp DESC
        LIMIT 1;
    """
    with get_cursor() as cur:
        cur.execute(sql)
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
    """
    # compute KST today 00:00 and next day 00:00, then convert to UTC
    now_kst = datetime.now(KST)
    today_kst_start = datetime.combine(now_kst.date(), time(0, 0, 0), tzinfo=KST)
    tomorrow_kst_start = datetime.combine(now_kst.date(), time(0, 0, 0), tzinfo=KST) + timedelta(days=1)

    start_utc = today_kst_start.astimezone(timezone.utc)
    end_utc = tomorrow_kst_start.astimezone(timezone.utc)

    with get_cursor() as cur:
        # 원천 테이블에서 조회
        cur.execute(f"""
            SELECT MIN(total_active_energy_kwh) AS mn, MAX(total_active_energy_kwh) AS mx
            FROM modbus_data_{device_id}
            WHERE time_stamp >= %s AND time_stamp < %s
        """, (start_utc, end_utc))
        mn_mx = cur.fetchone()
        if mn_mx and (mn_mx[0] is not None or mn_mx[1] is not None):
            mn, mx = mn_mx
            if mn is None or mx is None:
                return None
            return float(mx) - float(mn)

    return None
