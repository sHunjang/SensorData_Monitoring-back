"""
modbus_data 조회 API (연속집계 뷰 지원)
- /realtime: 최신 1건 (raw)
- /query: 기간 조회 (raw or continuous aggregate)
"""
from fastapi import APIRouter, Query
from typing import Optional
from src.db.client import get_cursor

router = APIRouter(prefix="/data/modbus", tags=["modbus"])

RAW_COLUMNS = """
time_stamp, device_id,
avg_power_factor, total_active_power_kW, total_reactive_power_kvar, total_apparent_power_kVA,
sum_line_currents_A, avg_line_to_neutral_volts_V, avg_line_to_line_volts_V, avg_line_current_A,
total_active_energy_kWh, total_reactive_energy_kvarh, total_apparent_energy_kVAh
"""

AGG_COLUMNS = """
bucket, device_id,
avg_pf AS avg_power_factor,
avg_p AS total_active_power_kW,
avg_q AS total_reactive_power_kvar,
avg_s AS total_apparent_power_kVA,
avg_sum_i AS sum_line_currents_A,
avg_v_ln AS avg_line_to_neutral_volts_V,
avg_v_ll AS avg_line_to_line_volts_V,
avg_i_avg AS avg_line_current_A,
delta_e_active AS total_active_energy_kWh,
delta_e_reactive AS total_reactive_energy_kvarh,
delta_e_apparent AS total_apparent_energy_kVAh,
n_samples
"""

INTERVAL_TABLES = {
    "15m": "modbus_agg_15m",
    "1h": "modbus_agg_1h",
    "1d": "modbus_agg_1d",
    "1w": "modbus_agg_1w",
    "1mo": "modbus_agg_1mo",
}

@router.get("/realtime")
def get_realtime(device_id: int = Query(..., description="슬레이브 ID")):
    """특정 장치(device_id)의 최신 Raw 데이터 1건 반환"""
    with get_cursor() as cur:
        cur.execute(f"""
            SELECT {RAW_COLUMNS}
            FROM modbus_data
            WHERE device_id = %s
            ORDER BY time_stamp DESC
            LIMIT 1
        """, (device_id,))
        row = cur.fetchone()
        if not row:
            return {"error": "데이터 없음"}
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

@router.get("/query")
def get_query(
    device_id: int,
    start: str,
    end: str,
    interval: Optional[str] = Query(None, description="15m, 1h, 1d, 1w, 1mo"),
    max_points: Optional[int] = 500
):
    """
    특정 장치(device_id)의 기간별 데이터 조회
    - interval 지정 시 → Continuous Aggregate 뷰 사용
    - interval 미지정 시 → Raw 데이터 직접 조회
    """
    with get_cursor() as cur:
        if interval and interval in INTERVAL_TABLES:
            table = INTERVAL_TABLES[interval]
            cur.execute(f"""
                SELECT {AGG_COLUMNS}
                FROM {table}
                WHERE device_id = %s AND bucket BETWEEN %s AND %s
                ORDER BY bucket ASC
                LIMIT %s
            """, (device_id, start, end, max_points))
        else:
            cur.execute(f"""
                SELECT {RAW_COLUMNS}
                FROM modbus_data
                WHERE device_id = %s AND time_stamp BETWEEN %s AND %s
                ORDER BY time_stamp ASC
                LIMIT %s
            """, (device_id, start, end, max_points))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]
