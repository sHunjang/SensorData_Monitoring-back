"""
TAC4300CT 전력계(Modbus RTU, FC=03) 데이터 읽기
- 평균 전압, 전류합, 전체 유효/무효/피상 전력, 역률, 에너지
"""
import minimalmodbus, serial
from typing import Dict

def create_instrument(port: str = "COM3", slave_id: int = 11):
    """
    Modbus RTU 통신용 Instrument 객체 생성
    - port: COM 포트
    - slave_id: 장치 주소 (TAC4300CT 메뉴얼 기본은 11)
    """
    inst = minimalmodbus.Instrument(port, slave_id)
    inst.serial.baudrate = 9600
    inst.serial.bytesize = 8
    inst.serial.parity = serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout = 1
    inst.clear_buffers_before_each_transaction = True
    return inst

def _read_u32(inst, addr: int) -> int:
    """32비트 Unsigned 값 읽기 (High Word 먼저)"""
    hi, lo = inst.read_registers(addr, 2, functioncode=3)
    return (hi << 16) | lo

def _read_s32(inst, addr: int) -> int:
    """32비트 Signed 값 읽기"""
    raw = _read_u32(inst, addr)
    return raw - 0x100000000 if (raw & 0x80000000) else raw

def _read_s16(inst, addr: int) -> int:
    """16비트 Signed 값 읽기"""
    return inst.read_register(addr, 0, functioncode=3, signed=True)

def read_summary(inst) -> Dict[str, float]:
    """
    요약 데이터 읽기
    레지스터 매핑:
    - 0x0036 평균전압×0.01V
    - 0x0034 전류합×0.001A
    - 0x002C 전체유효전력×0.001kW
    - 0x002E 전체무효전력×0.001kvar
    - 0x0030 전체피상전력×0.001kVA
    - 0x0032 전체역률×0.001
    - 0x0404 전체Active에너지×0.01kWh
    - 0x040C 전체Reactive에너지×0.01kvarh
    - 0x0410 전체Apparent에너지×0.01kVAh
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
        "avg_voltage_V": round(v_avg,2),
        "sum_current_A": round(i_sum,2),
        "total_active_kW": round(p_tot,2),
        "total_reactive_kvar": round(q_tot,2),
        "total_apparent_kVA": round(s_tot,2),
        "total_power_factor": round(pf,3),
        "total_active_energy_kwh": round(e_act,2),
        "total_reactive_energy_kvarh": round(e_rea,2),
        "total_apparent_energy_kVAh": round(e_app,2),
    }
