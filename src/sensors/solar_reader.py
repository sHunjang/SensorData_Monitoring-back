# src/sensors/solar_reader.py
"""
CWT-SI 일사량 센서(Modbus RTU) 리더
- 매뉴얼 기반 반영:
  - 읽기 레지스터: 0x0000 (1 워드, 16bit) -> irradiance (W/m^2), 분해능 1 W/m^2.
  - 기본 통신: 4800, N, 8, 1 (매뉴얼 기본값). 기본 슬레이브 ID는 센서 설정에 따름.
  - 읽기 함수코드: 0x03 (Read Holding Registers). 쓰기(보정) 예: 0x06.
  - 매뉴얼: CWT-SI Solar irradiance sensor manual (RS485). :contentReference[oaicite:1]{index=1}
- 동작:
  - minimalmodbus 사용.
  - 재시도/타임아웃/로깅 포함.
  - read_solar_sensor(inst) -> {"irradiance_w_m2": float|None, "module_temp_c": float|None}
  - write_calibration(inst, value) : 보정값(정수 W/m^2) 쓰기(레지스터 0x0052, function 0x06)
"""

from typing import Dict, Optional, Tuple
import time
import logging

import minimalmodbus
import serial

log = logging.getLogger("solar_reader")

# 기본 레지스터 맵 (매뉴얼 기준)
# (register_address, decimals_for_minimalmodbus, signed_flag, scale, offset)
# - irradiance: reg 0x0000, 16-bit unsigned, scale 1.0 (단위 W/m^2)
# - calibration: reg 0x0052, 16-bit unsigned, scale 1.0 (설정 쓰기용)
DEFAULT_REGISTER_MAP = {
    "irradiance": (0x0000, 0, False, 1.0, 0.0),
    "calibration": (0x0052, 0, False, 1.0, 0.0),
}

# 기본 통신/재시도 설정 (매뉴얼 기본 baud 4800)
DEFAULT_TIMEOUT = 1.0   # seconds
DEFAULT_RETRIES = 2
DEFAULT_BAUDRATE = 9600
DEFAULT_MODE = minimalmodbus.MODE_RTU


def create_instrument(
    port: str = "COM8",
    slave_id: int = 1,
    baudrate: int = DEFAULT_BAUDRATE,
    bytesize: int = 8,
    parity: str = serial.PARITY_NONE,
    stopbits: int = 1,
    timeout: float = DEFAULT_TIMEOUT,
    mode: str = DEFAULT_MODE,
    clear_buffers_before_each_transaction: bool = True,
) -> minimalmodbus.Instrument:
    """
    minimalmodbus.Instrument 생성기.
    - 기본값은 매뉴얼 권장값(baud=4800)으로 설정.
    - 반환된 Instrument로 read_solar_sensor / write_calibration 호출.
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
    - decimals: 0 사용 권장 (raw int), signed: False (irradiance unsigned)
    - 반환: raw int 또는 None (실패)
    """
    for attempt in range(retries + 1):
        try:
            raw = inst.read_register(register, decimals, functioncode=functioncode, signed=signed)
            return int(raw)
        except Exception as e:
            log.debug("solar_reader: read_register failed reg=0x%04X unit=%s attempt=%s err=%s", register, inst.address, attempt, e)
            time.sleep(retry_delay)
    log.warning("solar_reader: failed to read register 0x%04X unit=%s after %s attempts", register, inst.address, retries + 1)
    return None


def read_solar_sensor(inst: minimalmodbus.Instrument, register_map: Dict[str, Tuple[int, int, bool, float, float]] = None) -> Dict[str, Optional[float]]:
    """
    센서에서 일사량을 읽어 반환.
    - 반환: {"irradiance_w_m2": float|None}
    - 만약 센서가 모듈 온도를 제공하면 추가 필드(module_temp_c)를 반환할 수 있음(기본 맵엔 없음).
    """
    if register_map is None:
        register_map = DEFAULT_REGISTER_MAP

    out: Dict[str, Optional[float]] = {"irradiance_w_m2": None}

    # 읽기: irradiance (reg 0x0000)
    if "irradiance" in register_map:
        reg, decimals, signed, scale, offset = register_map["irradiance"]
        raw = _safe_read_register(inst, reg, decimals, signed, functioncode=3)
        if raw is not None:
            try:
                # manual: raw value is directly W/m^2 (resolution 1 W/m^2)
                out["irradiance_w_m2"] = float(raw) * float(scale) + float(offset)
            except Exception:
                log.exception("solar_reader: conversion failed raw=%s scale=%s offset=%s", raw, scale, offset)
                out["irradiance_w_m2"] = None

    return out


def write_calibration(inst: minimalmodbus.Instrument, cal_value: int) -> bool:
    """
    센서 보정값(레지스터 0x0052)에 쓰기.
    - cal_value: 정수 W/m^2 (매뉴얼 예: 0x000A => 10 W/m^2)
    - 사용 예: write_calibration(inst, 10)
    - 반환: True(성공)/False(실패)
    """
    reg, decimals, signed, scale, offset = DEFAULT_REGISTER_MAP["calibration"]
    try:
        # minimalmodbus write_register uses functioncode 6 by default for single register writes
        inst.write_register(reg, int(cal_value), number_of_decimals=0, functioncode=6)
        log.info("solar_reader: wrote calibration %s to reg=0x%04X unit=%s", cal_value, reg, inst.address)
        return True
    except Exception as e:
        log.exception("solar_reader: write_calibration failed reg=0x%04X unit=%s val=%s err=%s", reg, inst.address, cal_value, e)
        return False


def update_register_map(new_map: Dict[str, Tuple[int, int, bool, float, float]]):
    """
    런타임에 DEFAULT_REGISTER_MAP 덮어쓰기(테스트/현장 조정용).
    """
    global DEFAULT_REGISTER_MAP
    DEFAULT_REGISTER_MAP = new_map.copy()
    log.info("solar_reader: DEFAULT_REGISTER_MAP updated: %s", DEFAULT_REGISTER_MAP)
