# src/sensors/modbus_reader.py
"""
TAC4300 Modbus reader (minimalmodbus 기반, FC=03, Holding Registers)
- REGISTER_MAP에 TAC4300의 레지스터 주소, 워드 개수(주로 2), signed 여부, scale을 명시.
- 데이터 정렬: High-word -> Low-word (매뉴얼 표기). 32bit 값은 2워드 읽어 결합.
- 스케일: 전압 0.01, 전류 0.001, 전력 0.001, 에너지 0.01 (매뉴얼 기준).
- read_summary()는 REGISTER_MAP을 순회하여 dict를 반환. 실패 시 해당 키는 None으로 설정.
- 의존: minimalmodbus 설치 필요 (pip install minimalmodbus)
"""

import logging
import time
import serial
from typing import Dict
import minimalmodbus

log = logging.getLogger("modbus_reader")

# -----------------------
# REGISTER_MAP (매뉴얼 기반)
# key: (start_address, word_count, signed_flag, scale)
# - start_address는 16진수 표기 예시를 참고하세요 (0x0000 형태)
# - word_count: 2 -> 32bit (High-word, Low-word)
# - signed_flag: True면 signed 32bit 처리
# - scale: 곱해줘야 실제 단위가 됨
# -----------------------
REGISTER_MAP = {
    # Phase-level (L1/L2/L3) - 전압/전류/유효전력/전력량
    "l1_voltage_v":                (0x0000, 2, False, 0.01),  # L1 line voltage (2 words, unsigned) *0.01 V
    "l2_voltage_v":                (0x0002, 2, False, 0.01),  # L2
    "l3_voltage_v":                (0x0004, 2, False, 0.01),  # L3

    "l1_current_a":                (0x0006, 2, False, 0.001), # L1 current *0.001 A
    "l2_current_a":                (0x0008, 2, False, 0.001), # L2
    "l3_current_a":                (0x000A, 2, False, 0.001), # L3

    "l1_active_power_kw":          (0x000C, 2, True, 0.001),  # L1 active power signed *0.001 kW
    "l2_active_power_kw":          (0x000E, 2, True, 0.001),  # L2
    "l3_active_power_kw":          (0x0010, 2, True, 0.001),  # L3

    # Phase energy (per-phase total energy addresses)
    "l1_total_energy_kwh":         (0x0420, 2, False, 0.01),  # L1 total energy *0.01 kWh
    "l2_total_energy_kwh":         (0x0422, 2, False, 0.01),  # L2
    "l3_total_energy_kwh":         (0x0424, 2, False, 0.01),  # L3

    # System-level aggregated values
    "avg_line_to_line_volts_v":    (0x0038, 2, False, 0.01),  # Avg L-L voltage *0.01 V
    "avg_line_to_neutral_volts_v": (0x0036, 2, False, 0.01),  # Avg L-N voltage *0.01 V
    "sum_line_currents_a":         (0x0034, 2, False, 0.001), # Sum of line currents *0.001 A

    "total_active_power_kw":       (0x002C, 2, True, 0.001),  # System active power signed *0.001 kW
    "total_reactive_power_kvar":   (0x002E, 2, True, 0.001),  # System reactive power signed *0.001 kvar
    "total_apparent_power_kva":    (0x0030, 2, False, 0.001), # System apparent power *0.001 kVA

    # Power factor stored as 16-bit signed (scale 0.001)
    "total_power_factor":          (0x0032, 1, True, 0.001),

    # System total energies (addresses in 0x0400 range)
    "total_active_energy_kwh":     (0x0404, 2, True, 0.01),  # Total active energy (signed LONG) *0.01 kWh
    "total_reactive_energy_kvarh": (0x040C, 2, True, 0.01),  # Total reactive energy *0.01 kvarh
    "total_apparent_energy_kvah":  (0x0410, 2, False, 0.01), # Total apparent energy *0.01 kVAh
}

# -----------------------
# 내부 유틸
# -----------------------
DEFAULT_TIMEOUT = 1  # minimalmodbus 권장값
DEFAULT_RETRIES = 5  # 재시도 횟수

class ModbusInstrument:
    """minimalmodbus Instrument 래퍼"""
    def __init__(self, instrument: minimalmodbus.Instrument):
        self.instrument = instrument

    def close(self):
        """연결 종료"""
        try:
            if hasattr(self.instrument.serial, 'close') and self.instrument.serial.is_open:
                self.instrument.serial.close()
        except Exception as e:
            log.debug("Failed to close instrument: %s", e)

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
    minimalmodbus Instrument 생성 및 설정
    """
    try:
        inst = minimalmodbus.Instrument(port, slave_id)
        inst.serial.baudrate = baudrate
        inst.serial.bytesize = bytesize
        
        # 패리티 설정
        if parity.upper() == "N":
            inst.serial.parity = serial.PARITY_NONE
        elif parity.upper() == "E":
            inst.serial.parity = serial.PARITY_EVEN
        elif parity.upper() == "O":
            inst.serial.parity = serial.PARITY_ODD
        
        inst.serial.stopbits = stopbits
        inst.serial.timeout = timeout
        
        # minimalmodbus 권장 설정
        inst.clear_buffers_before_each_transaction = True
        inst.close_port_after_each_call = False  # 성능 향상
        inst.debug = False
        
        log.debug("Created instrument port=%s slave_id=%s", port, slave_id)
        return ModbusInstrument(inst)
        
    except Exception as e:
        raise ConnectionError(f"Failed to create instrument {port}:{slave_id} - {e}")

def _read_registers_with_retry(inst: ModbusInstrument, addr: int, count: int, retries: int = DEFAULT_RETRIES):
    """레지스터 읽기 (재시도 포함)"""
    last_error = None
    
    for attempt in range(retries + 1):
        try:
            # minimalmodbus는 read_registers 메서드 사용
            result = inst.instrument.read_registers(addr, count, functioncode=3)
            if result is not None:
                return result
        except Exception as e:
            last_error = e
            log.debug("read_registers failed addr=0x%04X count=%d attempt=%d err=%s", 
                     addr, count, attempt + 1, e)
            if attempt < retries:
                time.sleep(0.05)
    
    raise Exception(f"failed read_registers addr=0x{addr:04X} count={count} after {retries + 1} attempts: {last_error}")

def _words_to_uint32(high_word: int, low_word: int) -> int:
    """2워드를 32비트 unsigned 정수로 변환"""
    return ((high_word & 0xFFFF) << 16) | (low_word & 0xFFFF)

def _words_to_int32(high_word: int, low_word: int) -> int:
    """2워드를 32비트 signed 정수로 변환"""
    raw = _words_to_uint32(high_word, low_word)
    if raw & 0x80000000:
        return raw - (1 << 32)
    return raw

def _read_32bit(inst: ModbusInstrument, addr: int, signed: bool):
    """2워드(32bit) 읽어 signed/unsigned 반환"""
    regs = _read_registers_with_retry(inst, addr, 2)
    if not regs or len(regs) < 2:
        raise ValueError(f"Invalid register data: {regs}")
    
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
                # 32비트 값 읽기
                raw = _read_32bit(inst, addr, signed)
            else:
                # 16비트 값 읽기
                regs = _read_registers_with_retry(inst, addr, 1)
                if not regs:
                    raw = None
                else:
                    raw = regs[0]
                    # 16비트 signed 처리
                    if signed and raw is not None and raw & 0x8000:
                        raw = raw - (1 << 16)
            
            # 스케일 적용
            if raw is None:
                out[key] = None
            else:
                out[key] = (raw * scale) if scale is not None else raw
                
        except Exception as e:
            log.warning("read_summary failed key=%s addr=0x%04X err=%s", key, addr, e)
            out[key] = None
    
    return out

def update_register_map(new_map):
    """런타임에 REGISTER_MAP을 덮어쓸 수 있음 (테스트/현장 조정용)"""
    global REGISTER_MAP
    REGISTER_MAP = new_map.copy()
    log.info("REGISTER_MAP updated: %s", list(REGISTER_MAP.keys()))
