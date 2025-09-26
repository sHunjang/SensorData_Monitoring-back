# src/sensors/env_reader.py
"""
Env(온·습도) 센서 Modbus RTU 리더 (CWT-XYTH 기준)

요약
- 레지스터: temperature @ 0x0000, humidity @ 0x0001 (각 16-bit).
- 읽기 함수코드: 0x03 (Read Holding Registers). 예제 패킷도 0x03 사용함.
- 스케일/오프셋 (매뉴얼 기준):
    temperature_raw: 0 ~ 1650  -> 온도 -40 ~ 125°C
      => temperature = temperature_raw * 0.1 - 40
    humidity_raw: 0 ~ 1000 -> 0 ~ 100%RH
      => humidity = humidity_raw * 0.1
- 기본 통신 파라미터: 9600,n,8,1
- 참고 매뉴얼(업로드한 PDF). :contentReference[oaicite:0]{index=0}

사용법
- create_instrument(port, slave_id, ...) 로 인스턴스 생성
- read_env_sensor(inst) 호출해 {"temperature": float|None, "humidity": float|None} 반환
"""

from typing import Dict, Optional, Tuple
import time
import logging

import minimalmodbus
import serial

log = logging.getLogger("env_reader")

# 기본 레지스터 맵 (매뉴얼 기준)
# (register_address, decimals_for_minimalmodbus, signed_flag, scale, offset)
# decimals is set to 0 because we read raw integer and apply scale/offset ourselves.
DEFAULT_REGISTER_MAP = {
    "temperature": (0x0000, 0, False, 0.1, -40.0),  # raw 0..1650 -> temp = raw*0.1 - 40
    "humidity":    (0x0001, 0, False, 0.1, 0.0),    # raw 0..1000 -> rh = raw*0.1
}

DEFAULT_TIMEOUT = 1.0   # sec
DEFAULT_RETRIES = 2     # 읽기 재시도 횟수
DEFAULT_MODE = minimalmodbus.MODE_RTU


def create_instrument(
    port: str = "COM8",
    slave_id: int = 21,
    baudrate: int = 9600,
    bytesize: int = 8,
    parity: str = serial.PARITY_NONE,
    stopbits: int = 1,
    timeout: float = DEFAULT_TIMEOUT,
    mode: str = DEFAULT_MODE,
    clear_buffers_before_each_transaction: bool = True,
) -> minimalmodbus.Instrument:
    """
    minimalmodbus.Instrument 생성기.
    - 기본값은 COM8, 9600, timeout=1s (사용자의 .env 설정과 일치시킬 것).
    - 반환 Instrument는 호출자가 사용 후 별도 close 필요 없음.
    """
    inst = minimalmodbus.Instrument(port, slave_id)
    inst.serial.baudrate = baudrate
    inst.serial.bytesize = bytesize
    inst.serial.parity = parity
    inst.serial.stopbits = stopbits
    inst.serial.timeout = timeout
    inst.mode = mode
    inst.clear_buffers_before_each_transaction = clear_buffers_before_each_transaction
    return inst


def _safe_read_register(
    inst: minimalmodbus.Instrument,
    register: int,
    decimals: int,
    signed: bool,
    functioncode: int = 3,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = 0.05,
) -> Optional[int]:
    """
    minimalmodbus read_register 래퍼(재시도 포함).
    - register: Holding register 주소 (0 기반)
    - decimals: minimalmodbus 파라미터 (여기선 0으로 raw 정수 사용)
    - signed: True면 signed 읽기
    - functioncode: 기본 3 (Holding Registers)
    - 반환: 정수 raw 값 또는 None (실패)
    """
    for attempt in range(retries + 1):
        try:
            # minimalmodbus는 decimals 파라미터로 나누기를 수행하므로 decimals=0으로 raw 정수 수신
            raw = inst.read_register(register, decimals, functioncode=functioncode, signed=signed)
            # read_register may return float when decimals>0, but we use decimals=0 -> int/float raw
            return int(raw)
        except Exception as e:
            log.debug("env_reader: read_register failed reg=%s unit=%s attempt=%s err=%s", register, inst.address, attempt, e)
            time.sleep(retry_delay)
    log.warning("env_reader: failed to read register %s unit=%s after %s attempts", register, inst.address, retries + 1)
    return None


def read_env_sensor(inst: minimalmodbus.Instrument, register_map: Dict[str, Tuple[int, int, bool, float, float]] = None) -> Dict[str, Optional[float]]:
    """
    센서에서 온도/습도를 읽어 dict로 반환.
    - register_map 기본값은 DEFAULT_REGISTER_MAP (CWT-XYTH 매뉴얼 기준).
    - 반환:
        {"temperature": float|None, "humidity": float|None}
    - 실패된 키는 None으로 반환.
    """
    if register_map is None:
        register_map = DEFAULT_REGISTER_MAP

    out: Dict[str, Optional[float]] = {"temperature": None, "humidity": None}

    # Temperature
    if "temperature" in register_map:
        reg, decimals, signed, scale, offset = register_map["temperature"]
        raw = _safe_read_register(inst, reg, decimals, signed, functioncode=3)
        if raw is not None:
            try:
                # 매뉴얼: raw 0..1650 -> -40..125  => temp = raw * 0.1 - 40
                out["temperature"] = float(raw) * float(scale) + float(offset)
            except Exception:
                log.exception("env_reader: temperature scale conversion failed raw=%s scale=%s offset=%s", raw, scale, offset)
                out["temperature"] = None

    # Humidity
    if "humidity" in register_map:
        reg, decimals, signed, scale, offset = register_map["humidity"]
        raw = _safe_read_register(inst, reg, decimals, signed, functioncode=3)
        if raw is not None:
            try:
                out["humidity"] = float(raw) * float(scale) + float(offset)
            except Exception:
                log.exception("env_reader: humidity scale conversion failed raw=%s scale=%s offset=%s", raw, scale, offset)
                out["humidity"] = None

    return out


def update_register_map(new_map: Dict[str, Tuple[int, int, bool, float, float]]):
    """
    런타임에 REGISTER_MAP을 덮어쓰기(테스트/현장 조정용).
    new_map 형식: {"temperature": (addr,decimals,signed,scale,offset), ...}
    """
    global DEFAULT_REGISTER_MAP
    DEFAULT_REGISTER_MAP = new_map.copy()
    log.info("env_reader: DEFAULT_REGISTER_MAP updated: %s", DEFAULT_REGISTER_MAP)
