"""
Modbus(전력량계) API 라우터
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any
import logging

from src.services import modbus_service

router = APIRouter(prefix="/data/modbus", tags=["modbus"])
logger = logging.getLogger(__name__)


@router.get("/query")
async def get_modbus_data(
    deviceid: int = Query(..., description="Device ID (11-15)", alias="deviceid"),
    preset: Optional[str] = Query(None, description="Time preset: 1day, 1week, 1month, 1year"),
    start: Optional[str] = Query(None, description="Start time (ISO format)"),
    end: Optional[str] = Query(None, description="End time (ISO format)"),
    maxpoints: int = Query(1440, description="Maximum data points")
) -> Dict[str, Any]:
    """
    Modbus 시계열 데이터 조회 (그래프용)
    """
    try:
        if deviceid not in range(11, 16):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 11-15"
            )
        
        # ✅ 올바른 파라미터명 사용
        result = modbus_service.query_modbus_data(
            device_id=deviceid,
            preset=preset,
            start=start,  # start_iso → start
            end=end,      # end_iso → end
            max_points=maxpoints
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="No data found")
        
        logger.info(
            f"Modbus 조회 성공: device={deviceid}, preset={preset or 'custom'}, "
            f"resolution={result.get('resolution')}, points={result.get('data_points')}"
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Modbus 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/realtime")
async def get_modbus_realtime(
    deviceid: int = Query(..., description="Device ID (11-15)", alias="deviceid")
) -> Dict[str, Any]:
    """
    ✅ Modbus 실시간 데이터 조회 (최신 1건) - 단일 객체 반환
    """
    try:
        if deviceid not in range(11, 16):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 11-15"
            )
        
        # ✅ 실시간 전용 함수 호출 (단일 객체 반환)
        result = modbus_service.query_modbus_realtime(device_id=deviceid)
        
        if not result:
            return {
                "time_stamp": None,
                "device_id": deviceid,
                "voltage": None,
                "current": None,
                "power": None,
                "energy": None,
                "message": "No data available"
            }
        
        logger.info(f"Modbus 실시간 조회 성공: device={deviceid}, power={result.get('power')} kW")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Modbus 실시간 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/today-energy")
async def get_today_energy(
    deviceid: int = Query(..., description="Device ID (11-15)", alias="deviceid")
) -> Dict[str, Any]:
    """
    오늘 누적 에너지 조회
    """
    try:
        if deviceid not in range(11, 16):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 11-15"
            )
        
        # ✅ 올바른 함수명 사용
        energy_kwh = modbus_service.get_today_energy_kwh(device_id=deviceid)
        
        if energy_kwh is None:
            raise HTTPException(status_code=404, detail="No data found")
        
        # ✅ 응답 형식 맞추기
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
        
        result = {
            "device_id": deviceid,
            "date": now_kst.strftime("%Y-%m-%d"),
            "energy_kwh": energy_kwh,
            "wire_type": "4wire" if modbus_service._is_4wire(deviceid) else "3wire"
        }
        
        logger.info(f"오늘 에너지 조회 성공: device={deviceid}, energy={energy_kwh} kWh")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"오늘 에너지 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/statistics")
async def get_statistics(
    deviceid: int = Query(..., description="Device ID (11-15)", alias="deviceid"),
    days: int = Query(7, description="Number of days")
) -> Dict[str, Any]:
    """
    통계 조회 (최근 N일)
    """
    try:
        if deviceid not in range(11, 16):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 11-15"
            )
        
        result = modbus_service.get_device_statistics(device_id=deviceid, days=days)
        
        # ✅ wire_type 추가
        result["device_id"] = deviceid
        result["wire_type"] = "4wire" if modbus_service._is_4wire(deviceid) else "3wire"
        
        logger.info(f"통계 조회 성공: device={deviceid}, days={days}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"통계 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
