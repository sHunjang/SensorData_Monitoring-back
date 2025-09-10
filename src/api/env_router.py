"""
env_router.py
- 온습도 API
- 서비스 계층(env_service.py) 호출
"""

from fastapi import APIRouter, Query
from typing import Optional
from src.services.env_service import query_env_window

router = APIRouter(prefix="/data/env", tags=["environment"])

@router.get("/query")
def env_query(
    preset: Optional[str] = Query(default="1h", description="15m|1h|1d|1w|1mo"),
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_points: Optional[int] = Query(default=500, ge=1, le=5000),
):
    """
    온습도 기간별 집계 조회
    - 기본적으로 temperature, humidity 두 시리즈를 반환
    - preset 또는 start/end 로 기간 선택 가능
    """
    return query_env_window(
        preset=preset,
        start=start,
        end=end,
        max_points=max_points,
    )
