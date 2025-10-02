"""
src/services/solar_service.py

Solar(일사량) 데이터 조회 (집계 자동 선택 포함)
- 반환 데이터의 bucket은 KST tz-aware ISO 문자열
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
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


def query_solar_window(
    preset: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_points: int = 1000,
    device_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Solar 데이터 조회 (집계 자동 선택)
    
    시간 범위에 따라 자동으로 적절한 집계 테이블 선택
    """
    # 1) 시간 범위 계산
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
        s = datetime.fromisoformat(start) if start else now - timedelta(hours=1)
        e = datetime.fromisoformat(end) if end else now
        if s.tzinfo is None:
            s = s.replace(tzinfo=timezone.utc)
        if e.tzinfo is None:
            e = e.replace(tzinfo=timezone.utc)

    # 2) 집계 레벨 자동 선택
    agg_level, bucket_interval = select_aggregation_level(s, e)
    table_suffix = get_table_suffix(agg_level)
    time_col = get_time_column(agg_level)
    avg_prefix, max_prefix, min_prefix = get_column_prefix(agg_level)

    # 테이블 이름 생성 (Solar는 device_id 없음)
    if agg_level == "raw":
        table_name = "solar_data"
    else:
        table_name = f"agg_solar{table_suffix}"

    try:
        # 3) SQL 작성
        if agg_level == "raw":
            # 원천 데이터: 그대로 조회
            if device_id is None:
                sql = f"""
                    SELECT {time_col}, device_id, irradiance
                    FROM {table_name}
                    WHERE {time_col} >= %s AND {time_col} <= %s
                    ORDER BY {time_col} DESC
                    LIMIT %s;
                """
                params = [s, e, max_points]
            else:
                sql = f"""
                    SELECT {time_col}, device_id, irradiance
                    FROM {table_name}
                    WHERE device_id = %s AND {time_col} >= %s AND {time_col} <= %s
                    ORDER BY {time_col} DESC
                    LIMIT %s;
                """
                params = [device_id, s, e, max_points]
        else:
            # 집계 데이터: avg_ prefix 사용
            sql = f"""
                SELECT time_bucket(%s, {time_col}) AS bucket, 
                       {avg_prefix}irradiance AS irradiance
                FROM {table_name}
                WHERE {time_col} >= %s AND {time_col} <= %s
                GROUP BY bucket
                ORDER BY bucket DESC
                LIMIT %s;
            """
            params = [bucket_interval, s, e, max_points]

        with get_cursor() as cur:
            cur.execute(sql, params)
            rows_raw = cur.fetchall()

        # 4) 결과 정규화
        rows: List[Dict[str, Any]] = []
        for row in rows_raw:
            if agg_level == "raw":
                ts, did, solar = row
            else:
                ts, solar = row
                did = device_id

            if ts is not None and ts.tzinfo is None:
                ts = ts.replace(tzinfo=KST)
            
            rows.append({
                "bucket": iso_kst(ts),
                "device_id": did,
                "solar": round(float(solar), 2) if solar is not None else None,
                "aggregation_level": agg_level
            })

        # 통계 계산
        sols = [r["solar"] for r in rows if r["solar"] is not None]
        stats = {
            "solar": {
                "avg": round(sum(sols) / len(sols), 2) if sols else None,
                "max": max(sols) if sols else None,
                "min": min(sols) if sols else None,
                "count": len(sols)
            }
        }

        response = make_query_response(s, e, bucket_interval, ["solar"], rows, stats)
        response["aggregation_level"] = agg_level
        response["table_used"] = table_name
        
        return response
        
    except Exception as ex:
        return make_query_response(
            None, None, "1 hour", ["solar"], [], 
            {"solar": {"avg": None, "max": None, "min": None, "count": 0}},
            error=str(ex)
        )
