"""
CWT-XYTH (RS485, Modbus RTU)
- 통신: 9600, N, 8, 1 / 기본 ID=1
- FC=03: 0x0000(온도), 0x0001(습도) -> 각 16bit 값
- 계산식: T(°C) = -40 + temp_raw/10, H(%RH) = humi_raw/10
- ID 설정: FC=06, 0x000F 에 쓰기
참조 매뉴얼의 프레임·레지스터·변환식에 따름.
"""
import minimalmodbus
import serial
from typing import Tuple, Dict

DEF_PORT = "COM3"   # 환경에 맞게 수정
DEF_BAUD = 9600

def create_instrument(port: str = DEF_PORT, slave_id: int = 1, baudrate: int = DEF_BAUD) -> minimalmodbus.Instrument:
    inst = minimalmodbus.Instrument(port, slave_id)
    inst.serial.baudrate = baudrate
    inst.serial.bytesize = 8
    inst.serial.parity   = serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout  = 1.0
    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    return inst

def _read_two(inst: minimalmodbus.Instrument) -> Tuple[int, int]:
    """
    FC=03, 시작 0x0000, 길이 2 → [temp_raw, humi_raw]
    """
    regs = inst.read_registers(0x0000, 2, functioncode=3)
    if len(regs) != 2:
        raise RuntimeError(f"Invalid response: {regs}")
    return regs[0], regs[1]

def _convert(temp_raw: int, humi_raw: int) -> Dict[str, float]:
    """
    temp_raw 0~1650 → -40~125°C  : -40 + raw/10
    humi_raw 0~1000 → 0~100 %RH  : raw/10
    """
    return {
        "temperature": round(-40.0 + (temp_raw / 10.0), 1),
        "humidity":    round(humi_raw / 10.0, 1),
    }

def read_env(inst: minimalmodbus.Instrument) -> Dict[str, float]:
    t_raw, h_raw = _read_two(inst)
    return _convert(t_raw, h_raw)

def read_id(inst: minimalmodbus.Instrument) -> int:
    """
    슬레이브 ID 레지스터: 0x000F (FC=03)
    """
    return inst.read_register(0x000F, 0, functioncode=3, signed=False)

def write_id(inst: minimalmodbus.Instrument, new_id: int) -> None:
    """
    슬레이브 ID 설정: 0x000F (FC=06)
    - 성공 후 inst.address를 새 ID로 갱신
    """
    if not (1 <= new_id <= 254):
        raise ValueError("new_id must be 1..254")
    inst.write_register(0x000F, new_id, functioncode=6)
    inst.address = new_id
