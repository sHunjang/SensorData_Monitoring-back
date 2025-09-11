"""
solar_reader.py
- CWT-SI-M-S 일사량 센서 (RS485 Modbus RTU)
- 값 단위: W/m²
"""

import minimalmodbus

def create_instrument(port="COM3", slave_id=31, baudrate=9600) -> minimalmodbus.Instrument:
    """RS485 장치 핸들 생성"""
    try:
        inst = minimalmodbus.Instrument(port, slave_id)
        inst.serial.baudrate = 9600
        inst.serial.bytesize = 8
        inst.serial.parity = minimalmodbus.serial.PARITY_NONE
        inst.serial.stopbits = 1
        inst.serial.timeout = 1
        inst.clear_buffers_before_each_transaction = True
        return inst
    except Exception as e:
        raise ConnectionError(f"포트 {port}에서 장치 조회/초기화 실패: {e}")

def read_solar(inst: minimalmodbus.Instrument) -> float:
    """
    Holding Register 0x0000 (1개) → 일사량 값
    - Function Code: 0x03
    - Data Type: 16-bit Unsigned
    - 단위: W/m²
    """
    value = inst.read_register(0, 0, functioncode=3, signed=False)
    return float(value)
