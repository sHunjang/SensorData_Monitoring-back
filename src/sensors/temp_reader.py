import minimalmodbus, serial

def create_temp_instrument(port="COM4", slave_id=2):
    inst = minimalmodbus.Instrument(port, slave_id)
    inst.serial.baudrate = 9600
    inst.serial.bytesize = 8
    inst.serial.parity = serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout = 1
    return inst

def read_temperature(inst):
    # 예시: 0x0001 레지스터, 스케일 0.1
    raw = inst.read_register(0x0001, 1, functioncode=3, signed=True)
    return round(float(raw),2)
