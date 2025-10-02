# src/sensors/modbus_reader.py
"""
TAC4300 Modbus reader (minimalmodbus 기반, FC=03)
- REGISTER_MAP 정의에 따라 레지스터를 읽고 스케일 적용하여 값을 반환.
- High-word -> Low-word 정렬로 32bit 값을 조립.
- read_summary()는 실패 항목을 None으로 설정하여 호출 쪽에서 방어적으로 처리 가능.
- 변경점 요약:
  * ModbusInstrument에 __getattr__과 serial 프로퍼티 추가.
    -> collector가 inst.instrument 또는 inst.serial에 접근하려는 상황을 안전하게 지원.
  * read/register 읽기 로직은 wrapper의 메서드 호출을 사용하도록 정리.
"""

import logging
import time
import serial
from typing import Dict, Any, Optional
import minimalmodbus

log = logging.getLogger("modbus_reader")

# -----------------------
# REGISTER_MAP (매뉴얼 기반)
# key: (start_address, word_count, signed_flag, scale)
# -----------------------
REGISTER_MAP = {
    "l1_voltage_v":                (0x0000, 2, False, 0.01),
    "l2_voltage_v":                (0x0002, 2, False, 0.01),
    "l3_voltage_v":                (0x0004, 2, False, 0.01),

    "l1_current_a":                (0x0006, 2, False, 0.001),
    "l2_current_a":                (0x0008, 2, False, 0.001),
    "l3_current_a":                (0x000A, 2, False, 0.001),

    "l1_active_power_kw":          (0x000C, 2, True, 0.001),
    "l2_active_power_kw":          (0x000E, 2, True, 0.001),
    "l3_active_power_kw":          (0x0010, 2, True, 0.001),

    "l1_total_energy_kwh":         (0x0420, 2, False, 0.01),
    "l2_total_energy_kwh":         (0x0422, 2, False, 0.01),
    "l3_total_energy_kwh":         (0x0424, 2, False, 0.01),

    "avg_line_to_line_volts_v":    (0x0038, 2, False, 0.01),
    "avg_line_to_neutral_volts_v": (0x0036, 2, False, 0.01),
    "sum_line_currents_a":         (0x0034, 2, False, 0.001),

    "total_active_power_kw":       (0x002C, 2, True, 0.001),
    "total_reactive_power_kvar":   (0x002E, 2, True, 0.001),
    "total_apparent_power_kva":    (0x0030, 2, False, 0.001),

    "total_power_factor":          (0x0032, 1, True, 0.001),

    "total_active_energy_kwh":     (0x0404, 2, True, 0.01),
    "total_reactive_energy_kvarh": (0x040C, 2, True, 0.01),
    "total_apparent_energy_kvah":  (0x0410, 2, False, 0.01),
}

# -----------------------
# 내부 유틸
# -----------------------
DEFAULT_TIMEOUT = 5
DEFAULT_RETRIES = 5


class ModbusInstrument:
    """
    minimalmodbus.Instrument을 래핑.
    - wrapper는 호출자(collector)에서 inst.serial이나 inst.read_registers 호출을 기대할 때
      원활히 동작하도록 __getattr__으로 위임한다.
    - close() 메서드로 serial 포트 닫기 지원.
    """
    def __init__(self, instrument: minimalmodbus.Instrument):
        self.instrument = instrument

    def close(self):
        """내부 시리얼 포트 닫기 시도 (안전하게 처리)"""
        try:
            ser = getattr(self.instrument, "serial", None)
            if ser and getattr(ser, "is_open", False):
                ser.close()
        except Exception as e:
            log.debug("Failed to close instrument: %s", e)

    def __getattr__(self, name):
        """
        래퍼가 갖고 있지 않은 속성/메서드는 내부 instrument로 위임.
        예: inst.read_registers(...) 또는 inst.serial 접근이 가능해짐.
        """
        return getattr(self.instrument, name)

    @property
    def serial(self):
        """직접 serial 접근을 허용 (collector에서 ser = inst.serial 사용 가능)"""
        return getattr(self.instrument, "serial", None)


def create_instrument(
    port: str,
    slave_id: int,
    baudrate: int = 9600,
    parity: str = "N",
    stopbits: int = 1,
    bytesize: int = 8,
    timeout: int = DEFAULT_TIMEOUT,
) -> ModbusInstrument:
    """
    minimalmodbus.Instrument 생성 및 초기 설정 후 ModbusInstrument 래퍼로 반환.
    - close_port_after_each_call=False로 설정해 성능 향상.
    - 예외는 호출자에게 전달.
    """
    try:
        inst = minimalmodbus.Instrument(port, slave_id)
        inst.serial.baudrate = baudrate
        inst.serial.bytesize = bytesize

        if parity.upper() == "N":
            inst.serial.parity = serial.PARITY_NONE
        elif parity.upper() == "E":
            inst.serial.parity = serial.PARITY_EVEN
        elif parity.upper() == "O":
            inst.serial.parity = serial.PARITY_ODD

        inst.serial.stopbits = stopbits
        inst.serial.timeout = timeout

        inst.clear_buffers_before_each_transaction = True
        inst.close_port_after_each_call = False
        inst.debug = False

        log.debug("Created instrument port=%s slave_id=%s", port, slave_id)
        return ModbusInstrument(inst)

    except Exception as e:
        raise ConnectionError(f"Failed to create instrument {port}:{slave_id} - {e}")


def _read_registers_with_retry(inst: ModbusInstrument, addr: int, count: int, retries: int = DEFAULT_RETRIES):
    """
    read_registers 호출을 재시도하며 수행.
    - 실패 시 마지막 예외를 포함한 Exception을 던짐.
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            # wrapper의 __getattr__ 덕분에 inst.read_registers 호출 가능
            result = inst.read_registers(addr, count, functioncode=3)
            if result is not None:
                return result
        except Exception as e:
            last_error = e
            log.debug("read_registers failed addr=0x%04X count=%d attempt=%d err=%s", addr, count, attempt + 1, e)
            if attempt < retries:
                time.sleep(0.05)
    raise Exception(f"failed read_registers addr=0x{addr:04X} count={count} after {retries + 1} attempts: {last_error}")


def _words_to_uint32(high_word: int, low_word: int) -> int:
    return ((high_word & 0xFFFF) << 16) | (low_word & 0xFFFF)


def _words_to_int32(high_word: int, low_word: int) -> int:
    raw = _words_to_uint32(high_word, low_word)
    if raw & 0x80000000:
        return raw - (1 << 32)
    return raw


def _read_32bit(inst: ModbusInstrument, addr: int, signed: bool):
    """2워드(32bit) 읽기 및 signed/unsigned 반환"""
    regs = _read_registers_with_retry(inst, addr, 2)
    if not regs or len(regs) < 2:
        raise ValueError(f"Invalid register data: {regs}")
    hi, lo = regs[0], regs[1]
    return _words_to_int32(hi, lo) if signed else _words_to_uint32(hi, lo)


def read_summary(inst: ModbusInstrument) -> Dict[str, Optional[float]]:
    """
    REGISTER_MAP 전체를 순회하여 값을 읽고 스케일 적용 후 dict로 반환.
    실패한 키는 None으로 채움.
    반환 예:
      {"total_active_power_kw": 1.234, "total_active_energy_kwh": 12345.67, ...}
    """
    out: Dict[str, Optional[float]] = {}

    for key, (addr, word_count, signed, scale) in REGISTER_MAP.items():
        try:
            if word_count == 2:
                raw = _read_32bit(inst, addr, signed)
            else:
                regs = _read_registers_with_retry(inst, addr, 1)
                if not regs:
                    raw = None
                else:
                    raw = regs[0]
                    if signed and raw is not None and (raw & 0x8000):
                        raw = raw - (1 << 16)
            out[key] = (raw * scale) if (raw is not None and scale is not None) else (raw if raw is not None else None)
        except Exception as e:
            log.warning("read_summary failed key=%s addr=0x%04X err=%s", key, addr, e)
            out[key] = None

    return out


def update_register_map(new_map):
    """런타임에 REGISTER_MAP을 덮어씀 (테스트/현장 조정)"""
    global REGISTER_MAP
    REGISTER_MAP = new_map.copy()
    log.info("REGISTER_MAP updated: %s", list(REGISTER_MAP.keys()))
