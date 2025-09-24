# src/api/modbus_router.py
"""
Modbus API router
- /data/modbus/query  : 시계열 조회 (이미 존재하던 엔드포인트, 유지)
- /data/modbus/realtime : 최신 단일 레코드 반환 (프론트의 fetchRealtime 사용용)
- /data/modbus/today    : '오늘' 누적 전력량(kWh) 반환 (프론트의 fetchTodayEnergy 사용용)

주의:
- DB의 time_stamp는 TIMESTAMPTZ로 가정.
- 모든 시간 연산은 tz-aware로 처리(UTC 내부 사용, KST 변환은 iso_kst).
- 방어적 코딩: NULL 처리, 컬럼 누락 대비.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from src.db.client import get_cursor
from src.api._utils import make_query_response, iso_kst

router = APIRouter(prefix="/data/modbus", tags=["modbus"])

SERVER_MAX_POINTS = 5000
DEFAULT_POINTS = 500

KST = ZoneInfo("Asia/Seoul")


def parse_iso_flexible(s: str) -> datetime:
    """Flexible ISO parser that accepts trailing 'Z' and returns tz-aware datetime (UTC)."""
    if s is None:
        raise ValueError("empty")
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def resolve_window(preset: Optional[str], start: Optional[str], end: Optional[str]):
    """Resolve requested window to (start_utc, end_utc, bucket_label)."""
    now = datetime.now(timezone.utc)
    if preset and not (start or end):
        if preset == "15m":
            return now - timedelta(minutes=15), now, "1 minute"
        if preset == "1h":
            return now - timedelta(hours=1), now, "5 minutes"
        if preset == "1d":
            return now - timedelta(days=1), now, "1 hour"
        if preset == "1w":
            return now - timedelta(weeks=1), now, "6 hours"
        if preset == "1mo":
            return now - timedelta(days=30), now, "1 day"

    try:
        s = parse_iso_flexible(start) if start else (now - timedelta(hours=1))
        e = parse_iso_flexible(end) if end else now
    except Exception as ex:
        raise ValueError(f"invalid start/end datetime: {ex}")

    # ensure tz-aware UTC
    if s.tzinfo is None:
        s = s.replace(tzinfo=timezone.utc)
    if e.tzinfo is None:
        e = e.replace(tzinfo=timezone.utc)
    return s.astimezone(timezone.utc), e.astimezone(timezone.utc), "1 hour"


# -------------------------
# /query : 기존 시계열 조회
# -------------------------
@router.get("/query")
def query_modbus(
    preset: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    max_points: Optional[int] = Query(None),
    device_id: Optional[int] = Query(None),
    deviceId: Optional[int] = Query(None),
):
    """
    안전한 modbus 시계열 조회.
    반환되는 series:
      avg_line_to_line_volts_v,
      avg_line_to_neutral_volts_v,
      sum_line_currents_a,
      total_active_power_kw,
      total_reactive_power_kvar,
      total_apparent_power_kva,
      total_power_factor,
      total_active_energy_kwh,
      total_reactive_energy_kvarh,
      total_apparent_energy_kvah
    """
    dev_id = device_id if device_id is not None else deviceId

    if max_points is None:
        max_points = DEFAULT_POINTS
    try:
        max_points = int(max_points)
    except Exception:
        max_points = DEFAULT_POINTS
    if max_points < 1:
        max_points = DEFAULT_POINTS
    if max_points > SERVER_MAX_POINTS:
        max_points = SERVER_MAX_POINTS

    try:
        s, e, bucket = resolve_window(preset, start, end)
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))

    try:
        with get_cursor() as cur:
            sql = """
                SELECT time_stamp, device_id,
                       avg_line_to_line_volts_v,
                       avg_line_to_neutral_volts_v,
                       sum_line_currents_a,
                       total_active_power_kw,
                       total_reactive_power_kvar,
                       total_apparent_power_kva,
                       total_power_factor,
                       total_active_energy_kwh,
                       total_reactive_energy_kvarh,
                       total_apparent_energy_kvah
                FROM modbus_data
                WHERE time_stamp >= %s AND time_stamp <= %s
            """
            params: List[Any] = [s, e]
            if dev_id is not None:
                sql += " AND device_id = %s"
                params.append(dev_id)
            sql += " ORDER BY time_stamp DESC LIMIT %s"
            params.append(max_points)

            cur.execute(sql, tuple(params))
            rows: List[Dict[str, Any]] = []
            for (
                ts, dev,
                v_ll, v_ln, sum_i,
                p_kw, q_kvar, s_kva,
                pf,
                e_kwh, e_kvarh, e_kvah
            ) in cur.fetchall():
                rows.append({
                    "bucket": iso_kst(ts) if ts else None,
                    "device_id": dev,
                    "avg_line_to_line_volts_v": v_ll,
                    "avg_line_to_neutral_volts_v": v_ln,
                    "sum_line_currents_a": sum_i,
                    "total_active_power_kw": p_kw,
                    "total_reactive_power_kvar": q_kvar,
                    "total_apparent_power_kva": s_kva,
                    "total_power_factor": pf,
                    "total_active_energy_kwh": e_kwh,
                    "total_reactive_energy_kvarh": e_kvarh,
                    "total_apparent_energy_kvah": e_kvah,
                })

        # compute stats for each numeric series
        series_keys = [
            "avg_line_to_line_volts_v",
            "avg_line_to_neutral_volts_v",
            "sum_line_currents_a",
            "total_active_power_kw",
            "total_reactive_power_kvar",
            "total_apparent_power_kva",
            "total_power_factor",
            "total_active_energy_kwh",
            "total_reactive_energy_kvarh",
            "total_apparent_energy_kvah",
        ]

        stats: Dict[str, Dict[str, Any]] = {}
        for key in series_keys:
            vals = [r[key] for r in rows if r.get(key) is not None]
            stats[key] = {
                "avg": (sum(vals) / len(vals)) if vals else None,
                "max": max(vals) if vals else None,
                "min": min(vals) if vals else None,
                "count": len(vals),
            }

        return make_query_response(s, e, bucket, series_keys, rows, stats)

    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


# ------------------------------------------------
# /realtime : 최신 단일 행을 반환 (프론트용 간편 엔드포인트)
# ------------------------------------------------
@router.get("/realtime")
def modbus_realtime(device_id: Optional[int] = Query(None), deviceId: Optional[int] = Query(None)):
    """
    최신 레코드 한 건을 읽어 프론트가 기대하는 형태로 반환.
    응답 예:
    {
      "device_id": 11,
      "time_stamp": "2025-09-24T10:01:13.111555+09:00",
      "metrics": { "p_kw": 5.97, "e_kwh": 497.812, ... },
      "raw": { ... full row ... }
    }
    """
    dev = device_id if device_id is not None else deviceId
    if dev is None:
        raise HTTPException(status_code=400, detail="device_id is required")

    try:
        with get_cursor() as cur:
            cur.execute("""
                SELECT time_stamp, device_id,
                       avg_line_to_line_volts_v,
                       avg_line_to_neutral_volts_v,
                       sum_line_currents_a,
                       total_active_power_kw,
                       total_reactive_power_kvar,
                       total_apparent_power_kva,
                       total_power_factor,
                       total_active_energy_kwh,
                       total_reactive_energy_kvarh,
                       total_apparent_energy_kvah
                FROM modbus_data
                WHERE device_id = %s
                ORDER BY time_stamp DESC
                LIMIT 1
            """, (dev,))
            row = cur.fetchone()
            if not row:
                return {"device_id": dev, "time_stamp": None, "metrics": {"p_kw": None, "e_kwh": None}, "raw": None}

            ts, dev_id, v_ll, v_ln, sum_i, p_kw, q_kvar, s_kva, pf, e_kwh, e_kvarh, e_kvah = row

            metrics = {
                "p_kw": p_kw,
                "e_kwh": e_kwh,
                "v_avg": (v_ll if v_ll is not None else v_ln),
                "i_sum": sum_i,
                "pf": pf,
            }

            raw = {
                "time_stamp": iso_kst(ts) if ts else None,
                "device_id": dev_id,
                "avg_line_to_line_volts_v": v_ll,
                "avg_line_to_neutral_volts_v": v_ln,
                "sum_line_currents_a": sum_i,
                "total_active_power_kw": p_kw,
                "total_reactive_power_kvar": q_kvar,
                "total_apparent_power_kva": s_kva,
                "total_power_factor": pf,
                "total_active_energy_kwh": e_kwh,
                "total_reactive_energy_kvarh": e_kvarh,
                "total_apparent_energy_kvah": e_kvah,
            }

            return {"device_id": dev_id, "time_stamp": iso_kst(ts) if ts else None, "metrics": metrics, "raw": raw}

    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


# ------------------------------------------------
# /today : 오늘(한국시간) 누적 전력량(kWh) 반환
# ------------------------------------------------
@router.get("/today")
def modbus_today(device_id: Optional[int] = Query(None), deviceId: Optional[int] = Query(None)):
    """
    '오늘' 누적 전력량(kWh)을 계산하여 반환.
    방법:
      - KST 자정(start_of_day)부터 현재까지의 total_active_energy_kwh의 (max - min)을 계산.
      - 값이 존재하지 않으면 kwh: null 반환.
    응답 예:
      { "device_id": 11, "kwh": 12.345, "raw": { "min":..., "max":... } }
    """
    dev = device_id if device_id is not None else deviceId
    if dev is None:
        raise HTTPException(status_code=400, detail="device_id is required")

    try:
        # 현재 시각(UTC)와 KST의 자정 계산
        now_utc = datetime.now(timezone.utc)
        now_kst = now_utc.astimezone(KST)
        start_of_day_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        # SQL 비교를 UTC로
        start_utc = start_of_day_kst.astimezone(timezone.utc)

        with get_cursor() as cur:
            # min/max 범위에서 energy 칼럼이 NULL인 경우를 대비
            cur.execute("""
                SELECT MIN(total_active_energy_kwh) AS mn, MAX(total_active_energy_kwh) AS mx
                FROM modbus_data
                WHERE device_id = %s AND time_stamp >= %s AND time_stamp <= %s
            """, (dev, start_utc, now_utc))
            mn_mx = cur.fetchone()
            if mn_mx is None:
                return {"device_id": dev, "kwh": None, "raw": {}}
            mn, mx = mn_mx
            if mn is None or mx is None:
                return {"device_id": dev, "kwh": None, "raw": {"min": mn, "max": mx}}
            kwh = float(mx) - float(mn)
            return {"device_id": dev, "kwh": kwh, "raw": {"min": mn, "max": mx}}

    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
