"""
src/api/solar_router.py

- /data/solar/query 에 device_id 파라미터 전달을 확실히 처리
"""
from fastapi import APIRouter, Query
from typing import Optional

from src.services.solar_service import query_solar_window

router = APIRouter(prefix="/data/solar", tags=["solar"])

@router.get("/query")
def solar_query(
    preset: Optional[str] = Query(default="1d", description="15m|1h|1d|1w|1mo"),
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_points: Optional[int] = Query(default=500, ge=1, le=5000),
    device_id: Optional[int] = Query(default=None, description="장치 ID (선택)")
):
    """
    device_id가 주어지면 해당 장치만 필터링해서 반환.
    """
    return query_solar_window(preset=preset, start=start, end=end, max_points=max_points, device_id=device_id)
