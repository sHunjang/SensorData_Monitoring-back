"""
solar_router.py
- 일사량 API
- 서비스 계층(solar_service.py) 호출
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
):
    return query_solar_window(
        preset=preset,
        start=start,
        end=end,
        max_points=max_points,
    )
