# src/routes/modbus_router.py
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from src.db.client import get_cursor
import logging

router = APIRouter(prefix="/data/modbus", tags=["modbus"])
logger = logging.getLogger(__name__)

ALLOWED_PRESETS = {"10s", "1m", "15m", "1h", "1d", "1w", "1mo"}

@router.get("/query")
async def get_modbus_data(
    deviceid: int = Query(..., description="Device ID (11-15)"),
    preset: str = Query(..., description="Time preset: 10s, 1m, 15m, 1h, 1d, 1w, 1mo"),
    maxpoints: int = Query(100, description="Maximum data points"),
    start: Optional[str] = Query(None, description="Start time (ISO format)"),
    end: Optional[str] = Query(None, description="End time (ISO format)")
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
                SELECT
                    date_trunc('day', time_stamp) AS bucket,
                    AVG(total_active_power_kw) AS totalactivepowerkw,
                    AVG(total_reactive_power_kvar) AS totalreactivepowerkvar,
                    AVG(total_apparent_power_kva) AS totalapparentpowerkva,
                    AVG(avg_line_to_line_volts_v) AS avglinetolinevoltsv,
                    AVG(avg_line_to_neutral_volts_v) AS avglinetoneutralvoltsv,
                    AVG(sum_line_currents_a) AS sumlinecurrentsa,
                    AVG(total_power_factor) AS totalpowerfactor,
                    MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh) AS totalactiveenergykwh
                FROM modbus_data
                WHERE device_id = %s AND time_stamp >= %s AND time_stamp <= %s
                GROUP BY 1
                ORDER BY 1 ASC
                LIMIT %s
                """
            elif preset in ['15m', '1h']:
                query = """
                SELECT
                    date_trunc('minute', time_stamp) AS bucket,
                    AVG(total_active_power_kw) AS totalactivepowerkw,
                    AVG(total_reactive_power_kvar) AS totalreactivepowerkvar,
                    AVG(total_apparent_power_kva) AS totalapparentpowerkva,
                    AVG(avg_line_to_line_volts_v) AS avglinetolinevoltsv,
                    AVG(avg_line_to_neutral_volts_v) AS avglinetoneutralvoltsv,
                    AVG(sum_line_currents_a) AS sumlinecurrentsa,
                    AVG(total_power_factor) AS totalpowerfactor,
                    MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh) AS totalactiveenergykwh
                FROM modbus_data
                WHERE device_id = %s AND time_stamp >= %s AND time_stamp <= %s
                GROUP BY 1
                ORDER BY 1 ASC
                LIMIT %s
                """
            elif preset == '10s':
                # 10초 단위 버킷: epoch를 10초로 나눈 뒤 floor -> to_timestamp
                query = """
                SELECT
                    to_timestamp(floor(EXTRACT(EPOCH FROM time_stamp) / 10) * 10) AT TIME ZONE 'UTC' AS bucket,
                    AVG(total_active_power_kw) AS totalactivepowerkw,
                    AVG(total_reactive_power_kvar) AS totalreactivepowerkvar,
                    AVG(total_apparent_power_kva) AS totalapparentpowerkva,
                    AVG(avg_line_to_line_volts_v) AS avglinetolinevoltsv,
                    AVG(avg_line_to_neutral_volts_v) AS avglinetoneutralvoltsv,
                    AVG(sum_line_currents_a) AS sumlinecurrentsa,
                    AVG(total_power_factor) AS totalpowerfactor,
                    MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh) AS totalactiveenergykwh
                FROM modbus_data
                WHERE device_id = %s AND time_stamp >= %s AND time_stamp <= %s
                GROUP BY 1
                ORDER BY 1 ASC
                LIMIT %s
                """
            else:  # '1d' 원본 레코드
                query = """
                SELECT
                    time_stamp AS bucket,
                    total_active_power_kw AS totalactivepowerkw,
                    total_reactive_power_kvar AS totalreactivepowerkvar,
                    total_apparent_power_kva AS totalapparentpowerkva,
                    avg_line_to_line_volts_v AS avglinetolinevoltsv,
                    avg_line_to_neutral_volts_v AS avglinetoneutralvoltsv,
                    sum_line_currents_a AS sumlinecurrentsa,
                    total_power_factor AS totalpowerfactor,
                    total_active_energy_kwh AS totalactiveenergykwh
                FROM modbus_data
                WHERE device_id = %s AND time_stamp >= %s AND time_stamp <= %s
                ORDER BY time_stamp ASC
                LIMIT %s
                """

            cursor.execute(query, (deviceid, start_time, end_time, maxpoints))
            rows = cursor.fetchall()
            columns = [d[0] for d in cursor.description]

            data = []
            for row in rows:
                rd = dict(zip(columns, row))
                if rd.get('bucket'):
                    try:
                        rd['bucket'] = rd['bucket'].isoformat()
                    except Exception:
                        pass
                data.append(rd)

        logger.info(f"Modbus 조회: device={deviceid}, preset={preset}, count={len(data)}")
        return {"data": data, "count": len(data), "preset": preset, "device_id": deviceid,
                "time_range": {"start": start_time.isoformat(), "end": end_time.isoformat()}}

    except Exception as e:
        logger.error(f"Modbus 에러: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
