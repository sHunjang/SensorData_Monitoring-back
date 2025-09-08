import minimalmodbus, serial

def create_humidity_instrument(port="COM5", slave_id=3):
    inst = minimalmodbus.Instrument(port, slave_id)
    inst.serial.baudrate = 9600
    inst.serial.bytesize = 8
    inst.serial.parity = serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout = 1
    return inst

def read_humidity(inst):
    raw = inst.read_register(0x0002, 1, functioncode=3, signed=True)
    return round(float(raw),2)
