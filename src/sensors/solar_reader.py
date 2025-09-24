"""
solar_reader.py
- CWT-SI-M-S 일사량 센서(Modbus RTU, FC=03)
- 값 단위: W/m²
"""
import minimalmodbus
import serial

def create_instrument(port="COM9", slave_id=31, baudrate=4800) -> minimalmodbus.Instrument:
    inst = minimalmodbus.Instrument(port, slave_id)
    inst.serial.baudrate = baudrate
    inst.serial.bytesize = 8
    inst.serial.parity = serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout = 1
    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    return inst

def read_solar(inst: minimalmodbus.Instrument) -> float:
    """
    Holding Register 0x0000 (1개)
    - 16-bit Unsigned
    - 단위: W/m²
    """
    value = inst.read_register(0, 0, functioncode=3, signed=False)
    return float(value)
