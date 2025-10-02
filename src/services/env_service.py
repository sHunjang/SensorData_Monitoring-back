"""
env_service.py
- env_data 시간창 집계 조회 (집계 자동 선택 포함)
- 예외 시에도 200 + 빈 payload 반환
- 버킷과 window는 KST ISO 문자열로 반환
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from src.db.client import get_cursor
from src.utils.aggregation_selector import (
    select_aggregation_level,
    get_table_suffix,
    get_time_column,
    get_column_prefix
)

KST = ZoneInfo("Asia/Seoul")


def _compute_stats(rows: List[Dict], keys: List[str]) -> Dict[str, Dict]:
    stats: Dict[str, Dict] = {}
    for k in keys:
        vals = [float(r[k]) for r in rows if r.get(k) is not None]
        stats[k] = {
            "avg": round(sum(vals) / len(vals), 2),
            "max": round(max(vals), 2),
            "min": round(min(vals), 2),
            "count": len(vals),
        } if vals else {"avg": None, "max": None, "min": None, "count": 0}
    return stats


def query_env_window(
    device_id: int,
    preset: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_points: int = 1000,
) -> Dict[str, Any]:
    """
    Env 센서 데이터 조회 (집계 자동 선택)
    
    시간 범위에 따라 자동으로 적절한 집계 테이블 선택
    """
    try:
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

        # 테이블 이름 생성
        if agg_level == "raw":
            table_name = f"env_data_{device_id}"
        else:
            table_name = f"agg_env_{device_id}{table_suffix}"

        # 3) SQL 작성
        if agg_level == "raw":
            # 원천 데이터
            select_cols = "temperature, humidity"
        else:
            # 집계 데이터
            select_cols = f"{avg_prefix}temperature AS temperature, {avg_prefix}humidity AS humidity"

        sql = f"""
            SELECT time_bucket(%s, {time_col}) AT TIME ZONE 'Asia/Seoul' AS bucket_kst,
                   {select_cols}
            FROM {table_name}
            WHERE {time_col} >= %s AND {time_col} <= %s
            GROUP BY bucket_kst
            ORDER BY bucket_kst DESC
            LIMIT %s;
        """
        params = [bucket_interval, s, e, max_points]

        with get_cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            colnames = [d[0] for d in cur.description]

        # 4) 결과 정규화
        data: List[Dict] = []
        for r in rows:
            item = {
                "bucket": r[0].isoformat(),  # KST naive → ISO
                "aggregation_level": agg_level
            }
            for idx, name in enumerate(colnames[1:], start=1):
                v = r[idx]
                item[name] = round(float(v), 2) if v is not None else None
            data.append(item)

        stats = _compute_stats(data, ["temperature", "humidity"])
        
        return {
            "window": {
                "start": s.astimezone(KST).isoformat(),
                "end": e.astimezone(KST).isoformat()
            },
            "bucket": bucket_interval,
            "aggregation_level": agg_level,
            "table_used": table_name,
            "series": ["temperature", "humidity"],
            "data": data,
            "stats": stats,
        }
        
    except Exception as ex:
        # 503 대신 빈 payload
        return {
            "window": None,
            "bucket": "1 hour",
            "aggregation_level": "raw",
            "series": ["temperature", "humidity"],
            "data": [],
            "stats": {
                "temperature": {"avg": None, "max": None, "min": None, "count": 0},
                "humidity": {"avg": None, "max": None, "min": None, "count": 0},
            },
            "error": f"env query failed: {str(ex)}",
        }
