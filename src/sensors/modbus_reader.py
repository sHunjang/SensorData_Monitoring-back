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
    regs: List[int] = inst.read_registers(addr, 2, functioncode=3)
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
    # 실시간
    v_avg = _u32(inst, 0x0036) * 0.01
    i_sum = _u32(inst, 0x0034) * 0.001
    p_tot = _s32(inst, 0x002C) * 0.001
    q_tot = _s32(inst, 0x002E) * 0.001
    s_tot = _u32(inst, 0x0030) * 0.001
    pf    = _s16(inst, 0x0032) * 0.001

    # 에너지
    e_act = _s32(inst, 0x0404) * 0.01
    e_rea = _s32(inst, 0x040C) * 0.01
    e_app = _u32(inst, 0x0410) * 0.01

    return {
        "avg_voltage_V": round(v_avg, 2),
        "sum_current_A": round(i_sum, 2),
        "total_active_kW": round(p_tot, 2),
        "total_reactive_kvar": round(q_tot, 2),
        "total_apparent_kVA": round(s_tot, 2),
        "total_power_factor": round(pf, 3),
        "total_active_energy_kwh": round(e_act, 2),
        "total_reactive_energy_kvarh": round(e_rea, 2),
        "total_apparent_energy_kvah": round(e_app, 2),
    }
