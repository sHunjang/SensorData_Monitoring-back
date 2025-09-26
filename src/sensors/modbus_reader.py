# src/sensors/modbus_reader.py
"""
TAC4300 Modbus reader (integer-format, FC=03, Holding Registers)
- REGISTER_MAP에 TAC4300의 레지스터 주소, 워드 개수(주로 2), signed 여부, scale을 명시.
- 데이터 정렬: High-word -> Low-word (매뉴얼 표기). 32bit 값은 2워드 읽어 결합.
- 스케일: 전압 0.01, 전류 0.001, 전력 0.001, 에너지 0.01 (매뉴얼 기준). :contentReference[oaicite:2]{index=2}
- read_summary()는 REGISTER_MAP을 순회하여 dict를 반환. 실패 시 해당 키는 None으로 설정.
- 의존: pymodbus 설치 필요 (pip install pymodbus)
"""

import logging
import time
from typing import Tuple, Dict
from pymodbus.client.sync import ModbusSerialClient
from pymodbus.exceptions import ModbusException

log = logging.getLogger("modbus_reader")

# -----------------------
# REGISTER_MAP (매뉴얼 기반)
# key: (start_address, word_count, signed_flag, scale)
# - start_address는 16진수 표기 예시를 참고하세요 (0x0000 형태)
# - word_count: 2 -> 32bit (High-word, Low-word)
# - signed_flag: True면 signed 32bit 처리
# - scale: 곱해줘야 실제 단위가 됨
#
# 주소/스케일 출처(매뉴얼):
# - TAC4300CT 메뉴얼 정리 (레지스터 주소 예시 및 스케일). :contentReference[oaicite:3]{index=3}
# - 3상_TAC4300_MODBUS_프로토콜 (레지스터 표 전체/예시). :contentReference[oaicite:4]{index=4}
# -----------------------
REGISTER_MAP = {
    # Phase-level (L1/L2/L3) - 전압/전류/유효전력/전력량
    "l1_voltage_v":                (0x0000, 2, False, 0.01),  # L1 line voltage (2 words, unsigned) *0.01 V. :contentReference[oaicite:5]{index=5}
    "l2_voltage_v":                (0x0002, 2, False, 0.01),  # L2
    "l3_voltage_v":                (0x0004, 2, False, 0.01),  # L3

    "l1_current_a":                (0x0006, 2, False, 0.001), # L1 current *0.001 A. :contentReference[oaicite:6]{index=6}
    "l2_current_a":                (0x0008, 2, False, 0.001), # L2
    "l3_current_a":                (0x000A, 2, False, 0.001), # L3

    "l1_active_power_kw":          (0x000C, 2, True, 0.001),  # L1 active power signed *0.001 kW. :contentReference[oaicite:7]{index=7}
    "l2_active_power_kw":          (0x000E, 2, True, 0.001),  # L2
    "l3_active_power_kw":          (0x0010, 2, True, 0.001),  # L3

    # Phase energy (per-phase total energy addresses)
    "l1_total_energy_kwh":         (0x0420, 2, False, 0.01),  # L1 total energy *0.01 kWh. :contentReference[oaicite:8]{index=8}
    "l2_total_energy_kwh":         (0x0422, 2, False, 0.01),  # L2
    "l3_total_energy_kwh":         (0x0424, 2, False, 0.01),  # L3

    # System-level aggregated values
    "avg_line_to_line_volts_v":    (0x0038, 2, False, 0.01),  # Avg L-L voltage *0.01 V. :contentReference[oaicite:9]{index=9}
    "avg_line_to_neutral_volts_v": (0x0036, 2, False, 0.01),  # Avg L-N voltage *0.01 V. :contentReference[oaicite:10]{index=10}
    "sum_line_currents_a":         (0x0034, 2, False, 0.001), # Sum of line currents *0.001 A. :contentReference[oaicite:11]{index=11}

    "total_active_power_kw":       (0x002C, 2, True, 0.001),  # System active power signed *0.001 kW. :contentReference[oaicite:12]{index=12}
    "total_reactive_power_kvar":   (0x002E, 2, True, 0.001),  # System reactive power signed *0.001 kvar. :contentReference[oaicite:13]{index=13}
    "total_apparent_power_kva":    (0x0030, 2, False, 0.001), # System apparent power *0.001 kVA. :contentReference[oaicite:14]{index=14}

    # Power factor stored as 16-bit signed (scale 0.001). 매뉴얼에 0.001 표기. :contentReference[oaicite:15]{index=15}
    "total_power_factor":          (0x0032, 1, True, 0.001),

    # System total energies (addresses in 0x0400 range)
    "total_active_energy_kwh":     (0x0404, 2, True, 0.01),  # Total active energy (signed LONG) *0.01 kWh. :contentReference[oaicite:16]{index=16}
    "total_reactive_energy_kvarh": (0x040C, 2, True, 0.01),  # Total reactive energy *0.01 kvarh. :contentReference[oaicite:17]{index=17}
    "total_apparent_energy_kvah":  (0x0410, 2, False, 0.01), # Total apparent energy *0.01 kVAh. :contentReference[oaicite:18]{index=18}

    # (선택) Demand / THD / 기타 항목들은 float 형식 또는 4워드 등의 복수 워드가 있으므로
    # 필요 시 REGISTER_MAP에 추가. 전체 목록은 3상_TAC4300_MODBUS_프로토콜.pdf 참조. :contentReference[oaicite:19]{index=19}
}

# -----------------------
# 내부 유틸
# -----------------------
DEFAULT_TIMEOUT = 1  # sec
DEFAULT_RETRIES = 2  # 재시도 횟수


class ModbusInstrument:
    """시리얼 클라이언트 래퍼"""
    def __init__(self, client: ModbusSerialClient, unit: int):
        self.client = client
        self.unit = unit

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass


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
    시리얼 연결 생성 및 연결 확인.
    예외 발생 시 호출자에서 처리.
    """
    client = ModbusSerialClient(
        method="rtu",
        port=port,
        baudrate=baudrate,
        parity=parity,
        stopbits=stopbits,
        bytesize=bytesize,
        timeout=timeout,
    )
    if not client.connect():
        raise ConnectionError(f"Failed to open serial port {port}")
    return ModbusInstrument(client=client, unit=slave_id)


def _read_holding(inst: ModbusInstrument, addr: int, count: int, retries: int = DEFAULT_RETRIES):
    """Holding registers 읽기 래퍼 (재시도 포함)"""
    for attempt in range(retries + 1):
        try:
            rr = inst.client.read_holding_registers(address=addr, count=count, unit=inst.unit)
            if hasattr(rr, "registers") and rr.registers is not None:
                return rr.registers
            raise ModbusException(f"empty response addr=0x{addr:04X} unit={inst.unit} attempt={attempt}")
        except Exception as e:
            log.debug("read_holding_registers failed addr=0x%04X unit=%s attempt=%s err=%s", addr, inst.unit, attempt, e)
            time.sleep(0.05)
    raise ModbusException(f"failed read_holding_registers addr=0x{addr:04X} unit={inst.unit} after {retries+1} attempts")


def _words_to_uint32(high_word: int, low_word: int) -> int:
    return ((high_word & 0xFFFF) << 16) | (low_word & 0xFFFF)


def _words_to_int32(high_word: int, low_word: int) -> int:
    raw = _words_to_uint32(high_word, low_word)
    if raw & 0x80000000:
        return raw - (1 << 32)
    return raw


def _read_32bit(inst: ModbusInstrument, addr: int, signed: bool):
    """2워드(32bit) 읽어 signed/unsigned 반환"""
    regs = _read_holding(inst, addr, 2)
    hi, lo = regs[0], regs[1]
    return _words_to_int32(hi, lo) if signed else _words_to_uint32(hi, lo)


def read_summary(inst: ModbusInstrument) -> Dict[str, float]:
    """
    REGISTER_MAP을 순회하며 값을 읽어 dict로 반환.
    실패 항목은 None으로 둡니다.
    반환 예:
      {
        "total_active_power_kw": 1.234,
        "total_active_energy_kwh": 12345.67,
        ...
      }
    """
    out: Dict[str, float] = {}
    for key, (addr, word_count, signed, scale) in REGISTER_MAP.items():
        try:
            if word_count == 2:
                raw = _read_32bit(inst, addr, signed)
            else:
                # 1워드(16bit) 처리: signed 여부에 따라 기본 Modbus read 방식과 호환 필요.
                regs = _read_holding(inst, addr, 1)
                raw = regs[0] if regs else None
                if signed and raw is not None and raw & 0x8000:
                    raw = raw - (1 << 16)
            if raw is None:
                out[key] = None
            else:
                out[key] = (raw * scale) if scale is not None else raw
        except Exception as e:
            log.warning("read_summary failed key=%s addr=0x%04X unit=%s err=%s", key, addr, inst.unit, e)
            out[key] = None
    return out


def update_register_map(new_map):
    """런타임에 REGISTER_MAP을 덮어쓸 수 있음 (테스트/현장 조정용)"""
    global REGISTER_MAP
    REGISTER_MAP = new_map.copy()
    log.info("REGISTER_MAP updated: %s", list(REGISTER_MAP.keys()))
