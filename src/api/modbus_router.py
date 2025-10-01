"""
modbus_router.py - Modbus 데이터 API 라우터 (수정된 버전)

주요 기능:
- 4단계 preset 지원: 1h(1시간), 1d(1일), 1w(1주일), 1mo(1달)
- 1주일/1달 preset에서 날짜별 집계로 X축 라벨 중복 문제 해결
- 기존 client.py의 get_cursor() 사용
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from src.db.client import get_cursor
import logging

router = APIRouter(prefix="/data/modbus", tags=["modbus"])
logger = logging.getLogger(__name__)

@router.get("/query")
async def get_modbus_data(
    deviceid: int = Query(..., description="Device ID (11-15)"),
    preset: str = Query(..., description="Time preset: 1h, 1d, 1w, 1mo"),
    maxpoints: int = Query(100, description="Maximum data points"),
    start: Optional[str] = Query(None, description="Start time (ISO format)"),
    end: Optional[str] = Query(None, description="End time (ISO format)")
) -> Dict[str, Any]:
    """
    Modbus 데이터 조회 API
    """
    
    try:
        # 시간 범위 설정 (동일)
        if start and end:
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
        else:
            end_time = datetime.now(timezone.utc)
            if preset == '1h':
                start_time = end_time - timedelta(hours=1)
            elif preset == '1d':
                start_time = end_time - timedelta(days=1)
            elif preset == '1w':
                start_time = end_time - timedelta(days=7)
            elif preset == '1mo':
                start_time = end_time - timedelta(days=30)
            else:
                raise HTTPException(status_code=400, detail=f"Invalid preset: {preset}")
        
        # 🔧 기존 client.py의 get_cursor() 사용
        with get_cursor() as cursor:
            # preset별 집계 쿼리 (동일)
            if preset in ['1w', '1mo']:
                # 1주일/1달: 날짜별 집계
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
                    MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh) AS totalactiveenergykwh,
                    MAX(total_reactive_energy_kvarh) - MIN(total_reactive_energy_kvarh) AS totalreactiveenergykvarh,
                    MAX(total_apparent_energy_kvah) - MIN(total_apparent_energy_kvah) AS totalapparentenergykvah
                FROM modbus_data
                WHERE device_id = %s 
                    AND time_stamp >= %s 
                    AND time_stamp <= %s
                GROUP BY 1
                ORDER BY 1
                LIMIT %s
                """
            else:
                # 1시간/1일: 원본 또는 분 단위 집계
                if preset == '1h':
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
                        MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh) AS totalactiveenergykwh,
                        MAX(total_reactive_energy_kvarh) - MIN(total_reactive_energy_kvarh) AS totalreactiveenergykvarh,
                        MAX(total_apparent_energy_kvah) - MIN(total_apparent_energy_kvah) AS totalapparentenergykvah
                    FROM modbus_data
                    WHERE device_id = %s 
                        AND time_stamp >= %s 
                        AND time_stamp <= %s
                    GROUP BY 1
                    ORDER BY 1
                    LIMIT %s
                    """
                else:
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
                        total_active_energy_kwh AS totalactiveenergykwh,
                        total_reactive_energy_kvarh AS totalreactiveenergykvarh,
                        total_apparent_energy_kvah AS totalapparentenergykvah
                    FROM modbus_data
                    WHERE device_id = %s 
                        AND time_stamp >= %s 
                        AND time_stamp <= %s
                    ORDER BY time_stamp DESC
                    LIMIT %s
                    """
            
            # 쿼리 실행
            cursor.execute(query, (deviceid, start_time, end_time, maxpoints))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            # 결과 변환
            data = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                if row_dict['bucket']:
                    row_dict['bucket'] = row_dict['bucket'].isoformat()
                data.append(row_dict)
        
        logger.info(f"Modbus 데이터 조회 완료: device={deviceid}, preset={preset}, count={len(data)}")
        
        return {
            "data": data,
            "count": len(data),
            "preset": preset,
            "device_id": deviceid,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
    
    except Exception as e:
        logger.error(f"Modbus 데이터 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
