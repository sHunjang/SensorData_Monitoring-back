"""
modbus_router.py
- 전력량계 API 라우터
"""

from fastapi import APIRouter, Query
from typing import Optional, List
from src.services.modbus_service import (
    query_modbus_window,
    query_modbus_realtime,
    resolve_voltage_col,
    normalize_series
)

router = APIRouter(prefix="/data/modbus", tags=["modbus"])

@router.get("/realtime")
def get_realtime(device_id: int = Query(..., description="장치 ID")):
    """
    전력량계 실시간 값 조회 (가장 최근 row)
    """
    return query_modbus_realtime(device_id)

@router.get("/query")
def get_query(
    device_id: int = Query(..., description="장치 ID"),
    series: Optional[List[str]] = Query(default=None, description="조회할 컬럼 시리즈"),
    preset: Optional[str] = Query(default="1h", description="15m|1h|1d|1w|1mo"),
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    """
    전력량계 기간별 집계 조회
    - series 파라미터 없으면 기본값: [power, current, voltage]
    - 프론트에서 간단 키(voltage, current, power, energy)를 보내면
      DB 실제 컬럼명으로 변환됨
    """
    if not series:
        # 기본 시리즈 = 유효전력, 전류합, 전압
        v_col = resolve_voltage_col(device_id)
        series = ["total_active_power_kW", "sum_line_currents_A", v_col]
    else:
        # 프론트 요청 키를 DB 실제 컬럼명으로 변환
        series = normalize_series(device_id, series)

    return query_modbus_window(
        device_id=device_id,
        series=series,
        preset=preset,
        start=start,
        end=end,
    )
