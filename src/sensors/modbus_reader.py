"""
TAC4300CT 요약값 수집 (Function Code 03, Integer format).
- 평균 전압, 전류 합, 전체 P/Q/S, PF, 누적 에너지(Active/Reactive/Apparent)
- 32bit 조합은 High Word 먼저, 그 다음 Low Word.
"""
import minimalmodbus, serial
from typing import Dict
from src.config.settings import settings

# ---- 저수준 레지스터 읽기 도우미 ----
def _read_u32(inst: minimalmodbus.Instrument, addr: int) -> int:
    hi, lo = inst.read_registers(addr, 2, functioncode=3)
    return (hi << 16) | lo

def _read_s32(inst: minimalmodbus.Instrument, addr: int) -> int:
    raw = _read_u32(inst, addr)
    return raw - 0x100000000 if (raw & 0x80000000) else raw

def _read_s16(inst: minimalmodbus.Instrument, addr: int) -> int:
    return inst.read_register(addr, 0, functioncode=3, signed=True)

# ---- 계측기 초기화 ----
def create_instrument() -> minimalmodbus.Instrument:
    s = settings.serial
    inst = minimalmodbus.Instrument(s.port, s.slave_id)
    inst.serial.baudrate = s.baudrate
    inst.serial.bytesize = 8
    inst.serial.parity   = {
        "N": serial.PARITY_NONE,
        "E": serial.PARITY_EVEN,
        "O": serial.PARITY_ODD,
    }.get(s.parity.upper(), serial.PARITY_NONE)
    inst.serial.stopbits = s.stopbits
    inst.serial.timeout  = s.timeout_s
    inst.clear_buffers_before_each_transaction = True  # 노이즈 회피
    return inst

# ---- 요약값 읽기 ----
def read_summary(inst: minimalmodbus.Instrument) -> Dict[str, float]:
    """
    레지스터 매핑 (FC=03):
      0x0036 평균전압×0.01V (U32)
      0x0034 전류합×0.001A (U32)
      0x002C 전체유효P×0.001kW (S32)
      0x002E 전체무효Q×0.001kvar (S32)
      0x0030 전체피상S×0.001kVA (U32)
      0x0032 전체PF×0.001 (S16)
      0x0404 전체Active E×0.01kWh (S32)
      0x040C 전체Reactive E×0.01kvarh (S32)
      0x0410 전체Apparent E×0.01kVAh (U32)
    """
    v_avg = _read_u32(inst, 0x0036) * 0.01
    i_sum = _read_u32(inst, 0x0034) * 0.001
    p_tot = _read_s32(inst, 0x002C) * 0.001
    q_tot = _read_s32(inst, 0x002E) * 0.001
    s_tot = _read_u32(inst, 0x0030) * 0.001
    pf    = _read_s16(inst, 0x0032) * 0.001
    e_act = _read_s32(inst, 0x0404) * 0.01
    e_rea = _read_s32(inst, 0x040C) * 0.01
    e_app = _read_u32(inst, 0x0410) * 0.01

    return {
        "avg_voltage_V": v_avg,
        "sum_current_A": i_sum,
        "total_active_kW": p_tot,
        "total_reactive_kvar": q_tot,
        "total_apparent_kVA": s_tot,
        "total_power_factor": pf,
        "total_active_energy_kWh": e_act,
        "total_reactive_energy_kvarh": e_rea,
        "total_apparent_energy_kVAh": e_app,
    }
