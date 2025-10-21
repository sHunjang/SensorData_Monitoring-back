"""
Modbus(전력량계) 서비스 모듈


주요 기능:
- 시간 해상도별 데이터 조회 (1일/1주/1달/1년)
- 3상 4선식 / 3상 3선식 자동 구분
- 실시간 데이터 조회 (원시 데이터 우선, 1분 집계 fallback)
- 오늘 누적 에너지 계산
- **커스텀 시간 범위 지원 (ISO 8601 형식: .000Z 포함)**
- **총 누적 전력량 그래프 지원 (energy_end_kwh) - 모든 해상도**


데이터 소스:
- 실시간: modbus_data (원시 데이터) → modbus_*wire_1min (fallback)
- 1일 그래프: modbus_*wire_1min (1분 집계)
- 1주 그래프: modbus_*wire_15min (15분 집계)
- 1달 그래프: modbus_*wire_1hour (1시간 집계)
- 1년 그래프: modbus_*wire_1day (1일 집계)


*** 최종 수정 사항 ***
✅ ISO 8601 파싱 개선: .000Z, Z, +09:00 모두 지원
✅ 커스텀 범위 우선 처리: start/end가 있으면 preset 무시
✅ 실시간 데이터 fallback: 원시 데이터가 없으면 1분 집계 테이블 최신 데이터 사용
✅ 집계 테이블 사용: modbus_4wire_*, modbus_3wire_* 테이블에서 조회
✅ 자동 해상도 선택: preset 또는 범위에 따라 적절한 집계 테이블 자동 선택
✅ 3선/4선 자동 구분: settings.is_4wire_device() 활용
✅ 피크 전력 지원: 15분 이후 해상도에서 피크 전력 제공
✅ 에너지 delta: 구간별 소비량 제공 (energy_delta_kwh)
✅ 통계 함수 추가: get_device_statistics() - 최근 N일 통계
✅ 총 누적 전력량 추가: energy_end_kwh → total_energy (모든 해상도 지원!)
"""


from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo


from src.db.client import get_cursor
from src.config.settings import settings


KST = ZoneInfo("Asia/Seoul")



# ============================================================
# 헬퍼 함수
# ============================================================


def _is_4wire(device_id: int) -> bool:
    """디바이스가 3상 4선식인지 확인"""
    return settings.is_4wire_device(device_id)



def _is_3wire(device_id: int) -> bool:
    """디바이스가 3상 3선식인지 확인"""
    return settings.is_3wire_device(device_id)



def _get_table_and_columns(device_id: int, resolution: str) -> tuple:
    """
    디바이스 타입과 해상도에 맞는 테이블명과 컬럼 반환
    
    Args:
        device_id: 디바이스 ID
        resolution: "1min", "15min", "1hour", "1day"
        
    Returns:
        (table_name, voltage_col, energy_col_available)
    """
    is_4w = _is_4wire(device_id)
    wire_type = "4wire" if is_4w else "3wire"
    table_name = f"modbus_{wire_type}_{resolution}"
    
    # 전압 컬럼 (3상 4선 vs 3상 3선)
    voltage_col = "avg_voltage_ll_v" if is_4w else "avg_voltage_ln_v"
    
    # 에너지 데이터 가용성 (모든 해상도에서 사용 가능)
    energy_available = True
    
    return table_name, voltage_col, energy_available



def _parse_iso_datetime(iso_str: str) -> datetime:
    """
    ISO 8601 형식 파싱 (Python 3.10+ 호환)
    
    지원 형식:
    - 2025-10-14T08:20:00.000Z
    - 2025-10-14T08:20:00Z
    - 2025-10-14T08:20:00+09:00
    - 2025-10-14T08:20:00
    
    Args:
        iso_str: ISO 8601 형식 문자열
        
    Returns:
        KST 타임존의 datetime 객체
    """
    # 1. 'Z'를 '+00:00'으로 변환 (UTC 표시)
    if iso_str.endswith('Z'):
        iso_str = iso_str[:-1] + '+00:00'
    
    # 2. datetime 파싱
    try:
        dt = datetime.fromisoformat(iso_str)
    except ValueError as e:
        # Python 3.10에서도 실패할 경우 (예: 이상한 포맷)
        raise ValueError(f"Invalid ISO format: {iso_str}") from e
    
    # 3. 타임존 처리
    if dt.tzinfo is None:
        # 타임존 없음 -> KST로 간주
        dt = dt.replace(tzinfo=KST)
    else:
        # 다른 타임존 -> KST로 변환
        dt = dt.astimezone(KST)
    
    return dt



# ============================================================
# 시간 범위 및 해상도 결정
# ============================================================


def _determine_resolution_and_range(
    preset: Optional[str],
    start: Optional[str],
    end: Optional[str]
) -> tuple:
    """
    요청 파라미터로부터 시간 범위와 조회할 해상도 결정
    
    **우선순위**:
    1. start/end가 있으면 커스텀 범위 (preset 무시)
    2. preset이 있으면 고정 범위
    3. 둘 다 없으면 오늘 (기본값)
    
    Args:
        preset: "1day", "1week", "1month", "1year"
        start: 시작 시각 (ISO format)
        end: 종료 시각 (ISO format)
        
    Returns:
        (start_dt, end_dt, resolution)
        resolution: "1min", "15min", "1hour", "1day"
    """
    now = datetime.now(KST)
    
    # ==========================================
    # 1. 커스텀 범위 우선 (start/end가 있으면)
    # ==========================================
    if start and end:
        start_dt = _parse_iso_datetime(start)
        end_dt = _parse_iso_datetime(end)
        
        # 범위에 따라 해상도 자동 결정
        delta = end_dt - start_dt
        
        if delta <= timedelta(hours=6):
            resolution = "1min"
        elif delta <= timedelta(days=1):
            resolution = "1min"
        elif delta <= timedelta(days=7):
            resolution = "15min"
        elif delta <= timedelta(days=31):
            resolution = "1hour"
        else:
            resolution = "1day"
        
        return start_dt, end_dt, resolution
    
    # ==========================================
    # 2. Preset 모드 (start/end가 없을 때만)
    # ==========================================
    if preset:
        if preset == "1day":
            # 오늘 00:00 ~ 23:59
            start_dt = datetime.combine(now.date(), time(0, 0, 0), tzinfo=KST)
            end_dt = start_dt + timedelta(days=1)
            resolution = "1min"
            
        elif preset == "1week":
            # 이번 주 월요일 00:00 ~ 일요일 23:59
            today = now.date()
            weekday = today.weekday()  # 0=월요일, 6=일요일
            monday = today - timedelta(days=weekday)
            start_dt = datetime.combine(monday, time(0, 0, 0), tzinfo=KST)
            sunday = monday + timedelta(days=6)
            end_dt = datetime.combine(sunday, time(23, 59, 59), tzinfo=KST)
            resolution = "15min"
            
        elif preset == "1month":
            # 이번 달 1일 00:00 ~ 말일 23:59
            year = now.year
            month = now.month
            start_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=KST)
            
            # 말일 계산
            if month == 12:
                next_month = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=KST)
            else:
                next_month = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=KST)
            
            last_day = (next_month - timedelta(days=1)).day
            end_dt = datetime(year, month, last_day, 23, 59, 59, tzinfo=KST)
            resolution = "1hour"
            
        elif preset == "1year":
            # 올해 1월 1일 ~ 12월 31일
            year = now.year
            start_dt = datetime(year, 1, 1, 0, 0, 0, tzinfo=KST)
            end_dt = datetime(year, 12, 31, 23, 59, 59, tzinfo=KST)
            resolution = "1day"
            
        else:
            # 알 수 없는 preset -> 오늘
            start_dt = datetime.combine(now.date(), time(0, 0, 0), tzinfo=KST)
            end_dt = start_dt + timedelta(days=1)
            resolution = "1min"
    else:
        # 기본값: 오늘
        start_dt = datetime.combine(now.date(), time(0, 0, 0), tzinfo=KST)
        end_dt = start_dt + timedelta(days=1)
        resolution = "1min"
    
    return start_dt, end_dt, resolution



# ============================================================
# 메인 조회 함수
# ============================================================


def query_modbus_data(
    device_id: int,
    preset: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_points: int = 1440
) -> Dict[str, Any]:
    """
    Modbus 데이터 조회 (시간 해상도 자동 선택)
    
    ✅ 수정: 모든 해상도에서 total_energy 지원
    """
    start_dt, end_dt, resolution = _determine_resolution_and_range(preset, start, end)
    table_name, voltage_col, energy_available = _get_table_and_columns(device_id, resolution)
    
    if resolution == "1min":
        sql = f"""
            SELECT
                bucket,
                {voltage_col} AS voltage,
                avg_current_a AS current,
                avg_active_power_kw AS power,
                energy_delta_kwh AS energy_delta,
                avg_reactive_power_kvar AS reactive_power,
                avg_apparent_power_kva AS apparent_power,
                avg_power_factor AS power_factor,
                data_points,
                energy_end_kwh AS total_energy
            FROM {table_name}
            WHERE device_id = %s
              AND bucket >= %s
              AND bucket < %s
            ORDER BY bucket ASC
            LIMIT %s;
        """
    else:
        # ✅ 수정: 15분/1시간/1일도 energy_end_kwh 조회
        sql = f"""
            SELECT
                bucket,
                NULL AS voltage,
                NULL AS current,
                peak_power_kw AS power,
                energy_delta_kwh AS energy_delta,
                peak_power_kw AS peak_power,
                NULL AS reactive_power,
                NULL AS apparent_power,
                NULL AS power_factor,
                data_points,
                energy_end_kwh AS total_energy
            FROM {table_name}
            WHERE device_id = %s
              AND bucket >= %s
              AND bucket < %s
            ORDER BY bucket ASC
            LIMIT %s;
        """
    
    with get_cursor() as cur:
        cur.execute(sql, (device_id, start_dt, end_dt, max_points))
        rows = cur.fetchall()
    
    data = []
    for row in rows:
        bucket_ts = row[0]
        if bucket_ts and bucket_ts.tzinfo is None:
            bucket_ts = bucket_ts.replace(tzinfo=KST)
        
        item = {
            "bucket": bucket_ts.isoformat() if bucket_ts else None,
            "voltage": round(row[1], 2) if row[1] is not None else None,
            "current": round(row[2], 2) if row[2] is not None else None,
            "power": round(row[3], 2) if row[3] is not None else None,
            "energy_delta": round(row[4], 3) if row[4] is not None else None,
        }
        
        if resolution == "1min":
            item["reactive_power"] = round(row[5], 2) if row[5] is not None else None
            item["apparent_power"] = round(row[6], 2) if row[6] is not None else None
            item["power_factor"] = round(row[7], 3) if row[7] is not None else None
            item["total_energy"] = round(row[9], 3) if row[9] is not None else None
        else:
            # ✅ 15분 이상도 total_energy 추가
            item["peak_power"] = round(row[5], 2) if row[5] is not None else None
            item["total_energy"] = round(row[10], 3) if row[10] is not None else None
        
        data.append(item)
    
    return {
        "device_id": device_id,
        "wire_type": "4wire" if _is_4wire(device_id) else "3wire",
        "resolution": resolution,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "data_points": len(data),
        "data": data,
    }



# ============================================================
# 실시간 데이터 조회 (✅ 수정: fallback 추가)
# ============================================================


def query_modbus_realtime(device_id: int) -> Optional[Dict[str, Any]]:
    """
    최신 데이터 1건 조회 (실시간 모니터링용)
    
    ✅ 수정: 무효전력, 피상전력, 역률 추가
    """
    # 1차 시도: 원시 데이터 (modbus_data)
    voltage_col_raw = "avg_line_to_line_volts_v" if _is_4wire(device_id) else "avg_line_to_neutral_volts_v"
    
    sql_raw = f"""
        SELECT
            time_stamp,
            device_id,
            {voltage_col_raw} AS voltage,
            sum_line_currents_a AS current,
            total_active_power_kw AS power,
            total_active_energy_kwh AS energy,
            total_reactive_power_kvar AS reactive_power,
            total_apparent_power_kva AS apparent_power,
            total_power_factor AS power_factor,
            total_reactive_energy_kvarh AS reactive_energy,
            total_apparent_energy_kvah AS apparent_energy
        FROM modbus_data
        WHERE device_id = %s
        ORDER BY time_stamp DESC
        LIMIT 1;
    """
    
    with get_cursor() as cur:
        cur.execute(sql_raw, (device_id,))
        row = cur.fetchone()
    
    if row and row[0]:
        ts = row[0]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=KST)
        
        return {
            "time_stamp": ts.isoformat(),
            "device_id": row[1],
            "voltage": round(row[2], 2) if row[2] is not None else None,
            "current": round(row[3], 2) if row[3] is not None else None,
            "power": round(row[4], 2) if row[4] is not None else None,
            "energy": round(row[5], 3) if row[5] is not None else None,
            # ✅ 추가 데이터
            "reactive_power": round(row[6], 2) if row[6] is not None else None,
            "apparent_power": round(row[7], 2) if row[7] is not None else None,
            "power_factor": round(row[8], 3) if row[8] is not None else None,
            "reactive_energy": round(row[9], 3) if row[9] is not None else None,
            "apparent_energy": round(row[10], 3) if row[10] is not None else None,
        }
    
    # 2차 시도: 1분 집계 테이블 (무효전력, 피상전력 포함)
    wire_type = "4wire" if _is_4wire(device_id) else "3wire"
    table_1min = f"modbus_{wire_type}_1min"
    voltage_col_agg = "avg_voltage_ll_v" if _is_4wire(device_id) else "avg_voltage_ln_v"
    
    sql_1min = f"""
        SELECT
            bucket,
            {voltage_col_agg} AS voltage,
            avg_current_a AS current,
            avg_active_power_kw AS power,
            avg_reactive_power_kvar AS reactive_power,
            avg_apparent_power_kva AS apparent_power,
            avg_power_factor AS power_factor
        FROM {table_1min}
        WHERE device_id = %s
        ORDER BY bucket DESC
        LIMIT 1;
    """
    
    with get_cursor() as cur:
        cur.execute(sql_1min, (device_id,))
        row = cur.fetchone()
    
    if not row or not row[0]:
        return None
    
    ts = row[0]
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=KST)
    
    return {
        "time_stamp": ts.isoformat(),
        "device_id": device_id,
        "voltage": round(row[1], 2) if row[1] is not None else None,
        "current": round(row[2], 2) if row[2] is not None else None,
        "power": round(row[3], 2) if row[3] is not None else None,
        "energy": None,  # 1분 집계에는 누적 에너지 없음
        # ✅ 추가 데이터
        "reactive_power": round(row[4], 2) if row[4] is not None else None,
        "apparent_power": round(row[5], 2) if row[5] is not None else None,
        "power_factor": round(row[6], 3) if row[6] is not None else None,
        "reactive_energy": None,
        "apparent_energy": None,
    }




# ============================================================
# 오늘 누적 에너지 계산
# ============================================================


def get_today_energy_kwh(device_id: int) -> Optional[float]:
    """
    오늘(KST 기준 00:00~현재) 누적 에너지 소비량 계산
    """
    now_kst = datetime.now(KST)
    today_start = datetime.combine(now_kst.date(), time(0, 0, 0), tzinfo=KST)
    tomorrow_start = today_start + timedelta(days=1)
    wire_type = "4wire" if _is_4wire(device_id) else "3wire"
    
    # 1차 시도: 1분 집계 테이블에서 오늘 데이터 합산
    table_1min = f"modbus_{wire_type}_1min"
    sql_1min = f"""
        SELECT SUM(energy_delta_kwh)
        FROM {table_1min}
        WHERE device_id = %s
          AND bucket >= %s
          AND bucket < %s;
    """
    
    with get_cursor() as cur:
        cur.execute(sql_1min, (device_id, today_start, tomorrow_start))
        row = cur.fetchone()
        if row and row[0] is not None:
            return round(float(row[0]), 3)
    
    # 2차 시도: 15분 집계 테이블 합산
    table_15min = f"modbus_{wire_type}_15min"
    sql_15min = f"""
        SELECT SUM(energy_delta_kwh)
        FROM {table_15min}
        WHERE device_id = %s
          AND bucket >= %s
          AND bucket < %s;
    """
    
    with get_cursor() as cur:
        cur.execute(sql_15min, (device_id, today_start, tomorrow_start))
        row = cur.fetchone()
        if row and row[0] is not None:
            return round(float(row[0]), 3)
    
    return None



# ============================================================
# 통계 계산
# ============================================================


def get_device_statistics(device_id: int, days: int = 7) -> Dict[str, Any]:
    """
    디바이스 통계 계산 (최근 N일간)
    """
    now_kst = datetime.now(KST)
    start_dt = now_kst - timedelta(days=days)
    
    wire_type = "4wire" if _is_4wire(device_id) else "3wire"
    table_name = f"modbus_{wire_type}_1day"
    
    sql = f"""
        SELECT
            SUM(energy_delta_kwh) AS total_energy,
            AVG(peak_power_kw) AS avg_power,
            MAX(peak_power_kw) AS peak_power
        FROM {table_name}
        WHERE device_id = %s
          AND bucket >= %s
          AND bucket < %s;
    """
    
    with get_cursor() as cur:
        cur.execute(sql, (device_id, start_dt, now_kst))
        row = cur.fetchone()
    
    if not row:
        return {
            "total_energy_kwh": 0.0,
            "avg_power_kw": 0.0,
            "peak_power_kw": 0.0,
            "period_days": days,
        }
    
    return {
        "total_energy_kwh": round(float(row[0]), 3) if row[0] else 0.0,
        "avg_power_kw": round(float(row[1]), 2) if row[1] else 0.0,
        "peak_power_kw": round(float(row[2]), 2) if row[2] else 0.0,
        "period_days": days,
    }


def get_total_energy(device_id: int) -> Dict[str, Any]:
    """
    총 누적 전력량 조회 (전력량계 시작부터 현재까지)
    modbus_data 테이블에서 최신 total_active_energy_kwh 값 반환
    """
    with get_cursor() as cur:
        # 최신 total_active_energy_kwh 값 조회
        cur.execute("""
            SELECT 
                time_stamp,
                total_active_energy_kwh,
                total_reactive_energy_kvarh,
                total_apparent_energy_kvah
            FROM modbus_data
            WHERE device_id = %s
            ORDER BY time_stamp DESC
            LIMIT 1
        """, (device_id,))
        
        row = cur.fetchone()
        
        if row:
            time_stamp, total_active, total_reactive, total_apparent = row
            
            # 타임존 처리
            if time_stamp.tzinfo is None:
                time_stamp = time_stamp.replace(tzinfo=KST)
            
            return {
                "device_id": device_id,
                "time_stamp": time_stamp.isoformat(),
                "total_active_energy_kwh": round(float(total_active), 3) if total_active else 0.0,
                "total_reactive_energy_kvarh": round(float(total_reactive), 3) if total_reactive else 0.0,
                "total_apparent_energy_kvah": round(float(total_apparent), 3) if total_apparent else 0.0,
                "wire_type": "4wire" if _is_4wire(device_id) else "3wire"
            }
        else:
            # 데이터가 없는 경우
            return {
                "device_id": device_id,
                "time_stamp": None,
                "total_active_energy_kwh": 0.0,
                "total_reactive_energy_kvarh": 0.0,
                "total_apparent_energy_kvah": 0.0,
                "wire_type": "4wire" if _is_4wire(device_id) else "3wire"
            }
