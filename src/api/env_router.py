# src/routes/env_router.py
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from src.db.client import get_cursor
import logging

router = APIRouter(prefix="/data/env", tags=["env"])
logger = logging.getLogger(__name__)

ALLOWED_PRESETS = {"10s", "1m", "15m", "1h", "1d", "1w", "1mo"}

@router.get("/query")
async def get_env_data(
    deviceid: int = Query(..., description="Device ID (21-23)"),
    preset: str = Query(..., description="Time preset: 10s,1m,15m,1h,1d,1w,1mo"),
    maxpoints: int = Query(100, description="Maximum data points"),
    start: Optional[str] = Query(None), end: Optional[str] = Query(None)
) -> Dict[str, Any]:
    if preset not in ALLOWED_PRESETS:
        raise HTTPException(status_code=400, detail=f"Invalid preset: {preset}")

    try:
        if start and end:
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
        else:
            end_time = datetime.now(timezone.utc)
            if preset == '10s':
                start_time = end_time - timedelta(seconds=10)
            elif preset == '1m':
                start_time = end_time - timedelta(minutes=1)
            elif preset == '15m':
                start_time = end_time - timedelta(minutes=15)
            elif preset == '1h':
                start_time = end_time - timedelta(hours=1)
            elif preset == '1d':
                start_time = end_time - timedelta(days=1)
            elif preset == '1w':
                start_time = end_time - timedelta(days=7)
            elif preset == '1mo':
                start_time = end_time - timedelta(days=30)

        with get_cursor() as cursor:
            if preset in ['1w', '1mo']:
                query = """
                SELECT date_trunc('day', time_stamp) AS bucket, AVG(temperature) AS temperature, AVG(humidity) AS humidity
                FROM env_data
                WHERE device_id=%s AND time_stamp >= %s AND time_stamp <= %s
                GROUP BY 1 ORDER BY 1 ASC LIMIT %s
                """
            elif preset in ['15m', '1h']:
                query = """
                SELECT date_trunc('minute', time_stamp) AS bucket, AVG(temperature) AS temperature, AVG(humidity) AS humidity
                FROM env_data
                WHERE device_id=%s AND time_stamp >= %s AND time_stamp <= %s
                GROUP BY 1 ORDER BY 1 ASC LIMIT %s
                """
            elif preset == '10s':
                query = """
                SELECT to_timestamp(floor(EXTRACT(EPOCH FROM time_stamp)/10)*10) AT TIME ZONE 'UTC' AS bucket,
                       AVG(temperature) AS temperature, AVG(humidity) AS humidity
                FROM env_data
                WHERE device_id=%s AND time_stamp >= %s AND time_stamp <= %s
                GROUP BY 1 ORDER BY 1 ASC LIMIT %s
                """
            else:  # '1m' or '1d'
                query = """
                SELECT time_stamp AS bucket, temperature, humidity
                FROM env_data
                WHERE device_id=%s AND time_stamp >= %s AND time_stamp <= %s
                ORDER BY time_stamp ASC LIMIT %s
                """

            cursor.execute(query, (deviceid, start_time, end_time, maxpoints))
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]

            data = []
            for r in rows:
                rd = dict(zip(cols, r))
                if rd.get('bucket'):
                    try:
                        rd['bucket'] = rd['bucket'].isoformat()
                    except Exception:
                        pass
                data.append(rd)

        return {"data": data, "count": len(data), "preset": preset, "device_id": deviceid,
                "time_range": {"start": start_time.isoformat(), "end": end_time.isoformat()}}

    except Exception as e:
        logger.error(f"Env 에러: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
