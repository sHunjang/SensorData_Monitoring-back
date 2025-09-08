import minimalmodbus, serial

def create_solar_instrument(port="COM6", slave_id=4):
    inst = minimalmodbus.Instrument(port, slave_id)
    inst.serial.baudrate = 9600
    inst.serial.bytesize = 8
    inst.serial.parity = serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout = 1
    return inst

def read_solar(inst):
    raw = inst.read_register(0x0003, 1, functioncode=3, signed=False)
    return round(float(raw),2)
