"""
modbus_router.py
- FastAPI 라우터 (전력량계)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from src.services.modbus_service import query_modbus_window, query_modbus_realtime, normalize_series, resolve_voltage_col

router = APIRouter(prefix="/data/modbus", tags=["modbus"])


@router.get("/realtime")
def get_realtime(device_id: int = Query(..., description="장치 ID")):
    try:
        data = query_modbus_realtime(device_id)
        if not data:
            raise HTTPException(status_code=503, detail="장치에서 데이터 없음")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예상치 못한 오류: {e}")

@router.get("/query")
def get_query(device_id: int = Query(..., description="장치 ID"),
              series: Optional[List[str]] = Query(default=None),
              preset: Optional[str] = "1h",
              start: Optional[str] = None, end: Optional[str] = None):
    try:
        return query_modbus_window(device_id, series or ["power","current","voltage"], preset, start, end)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예상치 못한 오류: {e}")