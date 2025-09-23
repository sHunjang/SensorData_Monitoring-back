"""
modbus_reader.py
- TAC4300 Modbus 레지스터 읽기
- 정수 포맷(FC=03) 기반. 스케일 적용.
- LL(0x0038), LN(0x0036) 모두 계산해 반환.
"""
import minimalmodbus, serial
from typing import Dict, List, Tuple

def create_instrument(port: str = "COM7", slave_id: int = 11):
    inst = minimalmodbus.Instrument(port, slave_id)
    inst.serial.baudrate = 9600
    inst.serial.bytesize = 8
    inst.serial.parity = serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout = 2
    inst.clear_buffers_before_each_transaction = True
    return inst

def _read2(inst, addr: int) -> Tuple[int, int]:
    regs: List[int] = inst.read_registers(addr, 2, functioncode=3)  # FC=03
    if len(regs) != 2:
        raise RuntimeError(f"addr=0x{addr:04X} expects 2 regs, got {regs}")
    return regs[0], regs[1]  # hi, lo

def _u32(inst, addr: int) -> int:
    hi, lo = _read2(inst, addr)
    return (hi << 16) | lo

def _s32(inst, addr: int) -> int:
    v = _u32(inst, addr)
    return v - 0x100000000 if (v & 0x80000000) else v

def _s16(inst, addr: int) -> int:
    return inst.read_register(addr, 0, functioncode=3, signed=True)

def read_summary(inst) -> Dict[str, float]:
    """
    TAC4300 Integer-format map (자료: 메뉴얼)
    - Avg L-N volts: 0x0036 * 0.01 V
    - Avg L-L volts: 0x0038 * 0.01 V
    - Sum line currents: 0x0034 * 0.001 A
    - Total active power: 0x002C * 0.001 kW (signed)
    - Total reactive power: 0x002E * 0.001 kvar (signed)
    - Total apparent power: 0x0030 * 0.001 kVA
    - Total power factor: 0x0032 * 0.001
    - Total active energy: 0x0404 * 0.01 kWh (signed)
    - Total reactive energy: 0x040C * 0.01 kvarh (signed)
    - Total apparent energy: 0x0410 * 0.01 kVAh
    """
    v_avg_ln = _u32(inst, 0x0036) * 0.01
    v_avg_ll = _u32(inst, 0x0038) * 0.01
    i_sum    = _u32(inst, 0x0034) * 0.001
    p_tot    = _s32(inst, 0x002C) * 0.001
    q_tot    = _s32(inst, 0x002E) * 0.001
    s_tot    = _u32(inst, 0x0030) * 0.001
    pf       = _s16(inst, 0x0032) * 0.001
    e_act    = _s32(inst, 0x0404) * 0.01
    e_rea    = _s32(inst, 0x040C) * 0.01
    e_app    = _u32(inst, 0x0410) * 0.01

    return {
        "avg_voltage_ln_v": round(v_avg_ln, 2),
        "avg_voltage_ll_v": round(v_avg_ll, 2),
        "sum_line_currents_a": round(i_sum, 2),
        "total_active_kw": round(p_tot, 2),
        "total_reactive_power_kvar": round(q_tot, 2),
        "total_apparent_power_kva": round(s_tot, 2),
        "total_power_factor": round(pf, 3),
        "total_active_energy_kwh": round(e_act, 2),
        "total_reactive_energy_kvarh": round(e_rea, 2),
        "total_apparent_energy_kvah": round(e_app, 2),
    }
