"""
src/api/solar_router.py

FastAPI 라우터: /data/solar
- /query: 일사량 시계열 조회
- 서비스에서 이미 make_query_response 포맷을 반환함
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
    일사량 쿼리 엔드포인트
    - device_id 파라미터는 현재 서비스 레이어에 전달 가능(필요 시 서비스 확장)
    """
    return query_solar_window(preset=preset, start=start, end=end, max_points=max_points)
