# src/api/modbus_router.py
"""
/data/modbus/*
- /query  : 시계열 조회 (기존)
- /realtime : 단일 장치의 최신값(프론트에서 실시간 대시보드용)
- /today    : 장치별 당일 누적 전력량(kWh) (KST 기준 자정~현재)

설계 원칙:
- DB의 time_stamp 컬럼은 TIMESTAMPTZ로 가정.
- 프론트와의 호환성을 위해 realtime 응답에 'metrics' 객체를 포함.
- 날짜/시간 처리: 입력 ISO는 flexible 처리(Z 포함 가능). 내부 연산은 UTC 기준으로 수행하되
  반환되는 'bucket' 또는 'time_stamp'는 iso_kst()로 KST tz-aware ISO 문자열로 만든다.
- 안전성: 입력 검증, DB 조회 결과 없는 경우를 방어적으로 처리.
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
    """
    유연한 ISO 파서
    - 입력이 "2025-09-24T01:00:00Z" 처럼 Z로 끝나면 +00:00으로 변환
    - fromisoformat으로 파싱 후 tz가 없으면 UTC로 지정
    """
    if s is None:
        raise ValueError("empty datetime")
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def resolve_window(preset: Optional[str], start: Optional[str], end: Optional[str]):
    """
    preset 또는 start/end로 조회 윈도우 계산 (UTC tz-aware 반환)
    - preset 우선: '15m','1h','1d','1w','1mo' 지원
    - start/end가 주어지면 parse_iso_flexible 사용
    - 반환: (start_utc, end_utc, bucket_label)
    """
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

    # ensure tz-aware and normalized to UTC
    if s.tzinfo is None:
        s = s.replace(tzinfo=timezone.utc)
    if e.tzinfo is None:
        e = e.replace(tzinfo=timezone.utc)
    return s.astimezone(timezone.utc), e.astimezone(timezone.utc), "1 hour"


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
    (기존 구현을 유지)
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

        # make_query_response 재사용 (통일된 응답 포맷)
        return make_query_response(s, e, bucket, series_keys, rows, stats)

    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


# ------------------------------
# /realtime : 최신 한 건(장치별)
# ------------------------------
@router.get("/realtime")
def realtime_modbus(device_id: Optional[int] = Query(None), deviceId: Optional[int] = Query(None)):
    """
    최신 한 건을 반환한다 (프론트 realtime 뷰에서 사용).
    반환 예시:
    {
      "device_id": 11,
      "time_stamp": "2025-09-24T10:01:13.111555+09:00",
      "metrics": {
         "p_kw": 1.23,
         "total_active_energy_kwh": 1234.5,
         ...
      },
      "raw": { ... }  # 선택적: DB 행을 그대로 노출(디버깅용)
    }
    """
    dev_id = device_id if device_id is not None else deviceId
    if dev_id is None:
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
            """, (dev_id,))
            row = cur.fetchone()

            if not row:
                # 존재하지 않는 경우, 빈 metrics 반환 (프론트에서 방어적 처리)
                return {
                    "device_id": dev_id,
                    "time_stamp": None,
                    "metrics": {},
                    "raw": None
                }

            (ts, dev,
             v_ll, v_ln, sum_i,
             p_kw, q_kvar, s_kva,
             pf,
             e_kwh, e_kvarh, e_kvah) = row

            # metrics 객체: 프론트가 p_kw 등의 필드를 기대하므로 친숙한 키도 함께 넣음
            metrics = {
                # 전력(실시간)
                "p_kw": p_kw,
                "total_active_power_kw": p_kw,
                # 에너지(누적)
                "e_kwh": e_kwh,
                "total_active_energy_kwh": e_kwh,
                # 기타 원시 필드
                "avg_line_to_line_volts_v": v_ll,
                "avg_line_to_neutral_volts_v": v_ln,
                "sum_line_currents_a": sum_i,
                "total_reactive_power_kvar": q_kvar,
                "total_apparent_power_kva": s_kva,
                "total_power_factor": pf,
                "total_reactive_energy_kvarh": e_kvarh,
                "total_apparent_energy_kvah": e_kvah,
            }

            return {
                "device_id": dev,
                "time_stamp": iso_kst(ts) if ts else None,
                "metrics": metrics,
                "raw": {
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
                }
            }
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


# ------------------------------
# /today : KST 자정 기준 당일 누적 전력량 계산
# ------------------------------
@router.get("/today")
def today_energy(device_id: Optional[int] = Query(None), deviceId: Optional[int] = Query(None)):
    """
    device_id(또는 deviceId)가 필요.
    계산 방법:
      - KST(Asia/Seoul) 기준 오늘 자정(start_of_day_kst)부터 현재까지의
        total_active_energy_kwh 컬럼의 MIN/MAX 차이를 당일 전력량으로 반환.
      - DB에 누적 계량값이 저장되는 설정에서 동작하도록 설계됨.
    응답:
      { "device_id": 11, "kwh": 12.34 }
    """
    dev_id = device_id if device_id is not None else deviceId
    if dev_id is None:
        raise HTTPException(status_code=400, detail="device_id is required")

    try:
        # KST 자정 계산: 현재 KST의 자정 -> UTC로 변환하여 DB 타임스탬프 범위를 만듦
        now_kst = datetime.now(KST)
        start_of_day_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        # DB에 저장된 timestamptz는 타임존 정보를 포함하므로 UTC로 변환해서 질의
        start_utc = start_of_day_kst.astimezone(timezone.utc)
        end_utc = datetime.now(timezone.utc)

        with get_cursor() as cur:
            # MIN/MAX으로 당일 누적 사용량 계산
            cur.execute("""
                SELECT MIN(total_active_energy_kwh) AS mn, MAX(total_active_energy_kwh) AS mx
                FROM modbus_data
                WHERE device_id = %s AND time_stamp >= %s AND time_stamp <= %s
            """, (dev_id, start_utc, end_utc))
            res = cur.fetchone()
            if not res:
                return {"device_id": dev_id, "kwh": None}
            mn, mx = res
            if mn is None or mx is None:
                return {"device_id": dev_id, "kwh": None}
            # 보정: 음수 방지
            kwh = mx - mn
            if kwh < 0:
                # 누적 카운터가 리셋된 경우(재시작 등) 음수 발생 가능 -> None 으로 처리하거나 0으로 처리
                return {"device_id": dev_id, "kwh": None}
            return {"device_id": dev_id, "kwh": float(kwh)}

    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
