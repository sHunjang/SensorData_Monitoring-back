# src/collectors/modbus_collector.py
"""
Modbus 수집기 (TAC4300 전력계 대상)
- 역할: 시리얼(또는 설정된 포트)로 장치별 전력 요약값을 주기적으로 읽어
        DB(modbus_data) 테이블에 정규화하여 저장한다.
- 특징:
  * 장치별 Instrument(시리얼 핸들)를 캐시하여 포트 재오픈 비용과 잠금 문제를 줄임.
  * read_summary()에서 반환되는 다양한 키 변형을 DB 컬럼명으로 정규화하여 저장.
  * 연속 실패가 지정값을 넘으면 해당 장치는 스킵(운영에서 알람 필요).
  * 시그널(SIGINT, SIGTERM)을 받아 graceful shutdown 지원.
  * DB 삽입 전 숫자 강제 변환 및 None 처리로 안전성 향상.
- 전제:
  * src.sensors.modbus_reader.create_instrument 및 read_summary가 존재.
  * src.db.client.get_cursor()가 컨텍스트 매니저로 DB 커서(또는 커넥션)를 제공.
  * settings에 시리얼 및 장치 리스트, 폴링 주기 등이 정의됨.
"""

import time
import logging
import signal
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Optional, Any

from src.config.settings import settings
from src.db.client import get_cursor
from src.sensors.modbus_reader import create_instrument, read_summary

log = logging.getLogger("modbus_collector")
KST = ZoneInfo("Asia/Seoul")

# ------------------------------------------------------------------
# 런타임 상태 변수 및 캐시
# ------------------------------------------------------------------
_inst_cache: Dict[int, Any] = {}  # device_id -> Instrument (serial wrapper)
_shutdown = False  # 시그널 발생 시 True로 바뀌어 루프 종료 유도

# ------------------------------------------------------------------
# 시그널 처리: Ctrl-C나 시스템 종료 시 graceful하게 종료하도록 설정
# ------------------------------------------------------------------
def _signal_handler(signum, frame):
    """
    시그널 핸들러: 외부에서 SIGINT/SIGTERM이 오면 _shutdown 플래그를 세운다.
    main 루프는 이 플래그를 체크하여 안전하게 종료한다.
    """
    global _shutdown
    log.info("signal %s received, shutting down", signum)
    _shutdown = True

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# ------------------------------------------------------------------
# DB 스키마 보장 함수
# ------------------------------------------------------------------
def ensure_table():
    """
    테이블과 인덱스를 생성(존재하지 않으면).
    - DB 컬럼명은 반드시 고정된 이름을 사용한다.
    - 인덱스는 device/time 검색 성능 개선을 위해 추가.
    """
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                avg_line_to_line_volts_v DOUBLE PRECISION,
                avg_line_to_neutral_volts_v DOUBLE PRECISION,
                sum_line_currents_a DOUBLE PRECISION,
                total_active_power_kw DOUBLE PRECISION,
                total_reactive_power_kvar DOUBLE PRECISION,
                total_apparent_power_kva DOUBLE PRECISION,
                total_power_factor DOUBLE PRECISION,
                total_active_energy_kwh DOUBLE PRECISION,
                total_reactive_energy_kvarh DOUBLE PRECISION,
                total_apparent_energy_kvah DOUBLE PRECISION
            )
        """)
        # device/time 조합으로 자주 조회할 경우를 대비한 간단 인덱스
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_modbus_device_time ON modbus_data (device_id, time_stamp DESC)
        """)

# ------------------------------------------------------------------
# 유틸리티: payload 키 선택, 숫자 강제 변환
# ------------------------------------------------------------------
def _first_non_none(payload: Dict[str, Any], keys):
    """
    payload 딕셔너리에서 keys 목록을 순서대로 확인하여
    첫 번째로 None이 아닌 값을 반환한다.
    0도 유효값으로 취급한다(==> `or` 사용 금지).
    """
    for k in keys:
        if k in payload and payload[k] is not None:
            return payload[k]
    return None

def _coerce_number(v: Any) -> Optional[float]:
    """
    값을 안전하게 float로 변환한다. 변환 불가 시 None 반환.
    - 문자열 숫자, int, float 모두 처리.
    - "nan"/불가능한 타입은 None으로 처리.
    """
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None

# ------------------------------------------------------------------
# 정규화: 센서가 반환한 다양한 키들을 DB 컬럼명으로 매핑
# ------------------------------------------------------------------
def normalize_to_db_columns(payload: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """
    read_summary()가 반환할 수 있는 여러 변형 키들을
    DB 스키마(고정 컬럼명)으로 정규화하여 반환한다.

    반환 키(항상 DB 컬럼명):
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
    return {
        "avg_line_to_line_volts_v": _coerce_number(
            _first_non_none(payload, [
                "avg_line_to_line_volts_v", "avg_voltage_llv", "avg_voltage_ll_v", "avg_voltage_ll", "avg_voltage_ll_v"
            ])
        ),
        "avg_line_to_neutral_volts_v": _coerce_number(
            _first_non_none(payload, [
                "avg_line_to_neutral_volts_v", "avg_voltage_lnv", "avg_voltage_ln_v", "avg_voltage_ln"
            ])
        ),
        "sum_line_currents_a": _coerce_number(
            _first_non_none(payload, ["sum_line_currents_a", "sum_i", "sum_line_current_a", "sum_currents_a"])
        ),
        "total_active_power_kw": _coerce_number(
            _first_non_none(payload, [
                "total_active_power_kw", "total_active_kw", "p_kw", "p_kW", "total_active_power_kW", "total_active_kw"
            ])
        ),
        "total_reactive_power_kvar": _coerce_number(
            _first_non_none(payload, ["total_reactive_power_kvar", "q_kvar", "total_reactive_kvar", "q_kVAr"])
        ),
        "total_apparent_power_kva": _coerce_number(
            _first_non_none(payload, ["total_apparent_power_kva", "s_kva", "total_apparent_kva", "s_kV A"])
        ),
        "total_power_factor": _coerce_number(
            _first_non_none(payload, ["total_power_factor", "pf", "power_factor"])
        ),
        "total_active_energy_kwh": _coerce_number(
            _first_non_none(payload, ["total_active_energy_kwh", "e_kwh", "total_energy_kwh", "energy_kwh"])
        ),
        "total_reactive_energy_kvarh": _coerce_number(
            _first_non_none(payload, ["total_reactive_energy_kvarh", "e_reactive", "total_reactive_kvarh"])
        ),
        "total_apparent_energy_kvah": _coerce_number(
            _first_non_none(payload, ["total_apparent_energy_kvah", "e_apparent", "total_apparent_kvah"])
        ),
    }

# ------------------------------------------------------------------
# DB 삽입 함수: normalize 후 고정된 DB 컬럼명으로 삽입
# ------------------------------------------------------------------
def insert_row(device_id: int, payload: Dict[str, Any]):
    """
    payload를 정규화하여 modbus_data 테이블에 insert.
    DB 컬럼명은 절대 변경하지 않는다(요구사항).
    """
    now_kst = datetime.now(KST)
    norm = normalize_to_db_columns(payload)

    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO modbus_data (
                    time_stamp, device_id,
                    avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
                    sum_line_currents_a, total_active_power_kw,
                    total_reactive_power_kvar, total_apparent_power_kva,
                    total_power_factor, total_active_energy_kwh,
                    total_reactive_energy_kvarh, total_apparent_energy_kvah
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                now_kst, device_id,
                norm["avg_line_to_line_volts_v"],
                norm["avg_line_to_neutral_volts_v"],
                norm["sum_line_currents_a"],
                norm["total_active_power_kw"],
                norm["total_reactive_power_kvar"],
                norm["total_apparent_power_kva"],
                norm["total_power_factor"],
                norm["total_active_energy_kwh"],
                norm["total_reactive_energy_kvarh"],
                norm["total_apparent_energy_kvah"],
            ))
    except Exception:
        # 삽입 실패 시 전체 payload가 아닌 정규화된 dict로 로깅하여 디버깅 용이
        log.exception("DB insert failed for device=%s payload(normalized)=%s", device_id, norm)

# ------------------------------------------------------------------
# Instrument(시리얼 장치) 캐시 및 생성
# ------------------------------------------------------------------
def _get_instrument(device_id: int):
    """
    장치별 Instrument를 캐시해서 반환.
    - 최초 호출 시 create_instrument을 호출하여 생성하고 캐시.
    - 생성 실패 시 None 반환. 호출자는 재시도/오류처리 담당.
    - 캐시된 instrument가 내부적으로 문제가 있다고 판단되면 호출자에서 캐시 제거 가능.
    """
    inst = _inst_cache.get(device_id)
    if inst:
        return inst
    try:
        inst = create_instrument(
            port=settings.MODBUS_PORT,
            slave_id=device_id,
            baudrate=settings.MODBUS_BAUDRATE,
            parity=settings.MODBUS_PARITY,
            stopbits=settings.MODBUS_STOPBITS,
            bytesize=settings.MODBUS_BYTESIZE,
        )
        _inst_cache[device_id] = inst
        return inst
    except Exception:
        log.exception("create_instrument failed for device=%s", device_id)
        return None

# ------------------------------------------------------------------
# 장치 읽기 시도
# ------------------------------------------------------------------
def run_once_for_device(device_id: int, fail_counts: dict):
    """
    단일 장치에서 read_summary를 호출하여 읽고 DB에 저장한다.
    실패 시 fail_counts[device_id]를 증가시킨다.
    - 성공 시 fail_counts[device_id] = 0으로 리셋.
    - 실패 시 캐시된 Instrument를 닫고 캐시에서 제거하여 다음 시도에서 재생성되게 함.
    """
    inst = _get_instrument(device_id)
    if inst is None:
        fail_counts[device_id] = fail_counts.get(device_id, 0) + 1
        log.warning("No instrument for device=%s (count=%s)", device_id, fail_counts[device_id])
        return

    try:
        # read_summary는 장치별 레지스터 읽고 스케일 적용하여 dict 반환
        data = read_summary(inst)
        if not isinstance(data, dict):
            raise RuntimeError(f"read_summary returned non-dict: {data!r}")

        # DB 컬럼명으로 정규화 후 삽입
        insert_row(device_id, data)
        log.info("modbus: device=%s stored p=%s e=%s", device_id, data.get("total_active_kw"), data.get("total_active_energy_kwh"))
        fail_counts[device_id] = 0
    except Exception as e:
        # 실패 시 시리얼 리소스 닫기를 시도하고 캐시에서 제거.
        try:
            ser = getattr(inst, "serial", None)
            if ser:
                try:
                    ser.close()
                except Exception:
                    pass
        except Exception:
            pass

        _inst_cache.pop(device_id, None)
        fail_counts[device_id] = fail_counts.get(device_id, 0) + 1
        log.warning("modbus read fail device=%s count=%s err=%s", device_id, fail_counts[device_id], e)

# ------------------------------------------------------------------
# 메인 루프
# ------------------------------------------------------------------
def main():
    """
    메인 진입점.
    - settings에서 3W/4W ID를 합쳐 device list를 구성.
    - 각 장치를 순회하면서 run_once_for_device를 호출.
    - 연속 실패가 max_fails를 넘으면 해당 장치 스킵.
    - interval은 settings.MODBUS_POLL_INTERVAL (초).
    - 프로그램 종료 시 열린 시리얼 포트를 닫음.
    """
    log.info("starting modbus_collector mode=%s", getattr(settings, "MODE", "real"))

    ensure_table()

    ids_3w = getattr(settings, "MODBUS_3W_IDS", []) or []
    ids_4w = getattr(settings, "MODBUS_4W_IDS", []) or []
    device_ids = list(dict.fromkeys(ids_3w + ids_4w))  # 중복 제거
    interval = getattr(settings, "MODBUS_POLL_INTERVAL", 60)
    max_fails = getattr(settings, "MODBUS_MAX_FAILS", 3)

    log.info("modbus_collector config: port=%s devices=%s interval=%s", settings.MODBUS_PORT, device_ids, interval)

    # 실패 카운트 맵 초기화
    fail_counts = {sid: 0 for sid in device_ids}

    try:
        while not _shutdown:
            for sid in device_ids:
                if _shutdown:
                    break
                if fail_counts.get(sid, 0) >= max_fails:
                    # 연속 실패가 충분히 쌓이면 스킵. 실제 운영에서는 여기서 알람 트리거 권장.
                    log.warning("device %s disabled after %s consecutive fails", sid, max_fails)
                    continue
                run_once_for_device(sid, fail_counts)

            # interval 동안 1초 단위로 깨어나는 형태로 sleep.
            # 이렇게 하면 시그널이 와도 최대 interval 초간 기다리지 않고 빠르게 종료 가능.
            for _ in range(int(max(1, interval))):
                if _shutdown:
                    break
                time.sleep(1)
    except Exception as e:
        log.exception("modbus_collector fatal error: %s", e)
    finally:
        # 종료 시 자원 정리: 캐시된 Instrument의 시리얼 포트 닫기
        log.info("modbus_collector exiting, closing instruments")
        for inst in list(_inst_cache.values()):
            try:
                ser = getattr(inst, "serial", None)
                if ser:
                    try:
                        ser.close()
                    except Exception:
                        pass
            except Exception:
                pass

# 모듈을 직접 실행하면 main 실행
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
