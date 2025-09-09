"""
modbus_data 조회 API
- /realtime: 장치 최신 1건(raw)
- /query: 기간 집계 + 통계 + 버킷 정보
- 장치 5대(11~15) 및 3상3선/4선 전압 분기 반영
"""
from fastapi import APIRouter, Query
from typing import Optional, List
from src.db.client import get_cursor
from src.services.modbus_service import (
    query_modbus_window, THREE_WIRE_IDS, FOUR_WIRE_IDS, resolve_voltage_col
)

router = APIRouter(prefix="/data/modbus", tags=["modbus"])

router = APIRouter(prefix="/data/modbus", tags=["modbus"])

def _has_column(table: str, col: str) -> bool:
    sql = """
      SELECT 1
      FROM information_schema.columns
      WHERE table_name = %s AND column_name = %s
      LIMIT 1
    """
    with get_cursor() as cur:
        cur.execute(sql, (table, col))
        return cur.fetchone() is not None

def _build_raw_columns() -> str:
    base = [
        "time_stamp", "device_id",
        # 역률 컬럼은 동적으로 삽입
        "total_active_power_kW",
        "total_reactive_power_kvar",
        "total_apparent_power_kVA",
        "sum_line_currents_A",
        "avg_line_to_neutral_volts_V",
        "avg_line_to_line_volts_V",
        "avg_line_current_A",
        "total_active_energy_kWh",
        "total_reactive_energy_kvarh",
        "total_apparent_energy_kVAh",
    ]
    # power_factor 계열 존재 확인
    pf_col = None
    if _has_column("modbus_data", "total_power_factor"):
        pf_col = "total_power_factor"
    elif _has_column("modbus_data", "avg_power_factor"):
        pf_col = "avg_power_factor"

    if pf_col:
        base.insert(2, pf_col)  # time_stamp, device_id 다음에 삽입

    return ", ".join(base)

@router.get("/realtime")
def get_realtime(device_id: int = Query(..., description="슬레이브 ID(11~15)")):
    """
    특정 장치 최신 Raw 1건
    - 존재하는 역률 컬럼만 선택(없으면 미포함)
    - voltage 필드는 구성에 맞는 전압(avg L-L or L-N)으로 통일
    """
    raw_cols = _build_raw_columns()
    with get_cursor() as cur:
        cur.execute(f"""
            SELECT {raw_cols}
            FROM modbus_data
            WHERE device_id = %s
            ORDER BY time_stamp DESC
            LIMIT 1
        """, (device_id,))
        row = cur.fetchone()
        if not row:
            return {"error": "데이터 없음"}

        cols = [d[0] for d in cur.description]
        out = dict(zip(cols, row))

    # 전압 통일 필드
    v_col = resolve_voltage_col(device_id)
    out["voltage"] = out.get(v_col)
    out["phase_config"] = "3P3W" if device_id in THREE_WIRE_IDS else "3P4W"
    return out

@router.get("/query")
def get_query(
    device_id: int,
    # 시리즈 키 선택: p_total, q_total, s_total, pf_total, voltage, current
    series: Optional[List[str]] = Query(default=["p_total", "voltage", "current"]),
    preset: Optional[str] = Query(default="1d", description="15m|1h|1d|1w|1mo"),
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_points: Optional[int] = Query(default=500, ge=50, le=5000),
):
    """
    기간 집계 + 통계 반환
    - 서버가 bucket_seconds로 포인트 수를 제어
    - 통계: 평균/최대/최소/개수(stats.*)
    """
    result = query_modbus_window(
        device_id=device_id,
        series_keys=series or ["p_total"],
        preset=preset,
        start=start,
        end=end,
        max_points=max_points or 500,
    )
    return result
