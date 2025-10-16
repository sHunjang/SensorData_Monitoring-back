import minimalmodbus, serial
from typing import List

def create_instrument(port: str = "COM4", slave_id: int = 11):
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

device_ids: List[int] = [11, 12, 13, 14, 15]

for sid in device_ids:
    inst = create_instrument(port="COM4", slave_id=sid)
    try:
        print(f"Device {sid}")
        print("ΣI:", inst.read_registers(0x0034, 2, functioncode=3))   # 합계 전류
        print("Vavg:", inst.read_registers(0x0036, 2, functioncode=3)) # 평균 전압
        print("Ptot:", inst.read_registers(0x002C, 2, functioncode=3)) # 총 유효전력
        print("Energy:", inst.read_registers(0x0404, 2, functioncode=3)) # 전력량
        print("Reg1:", inst.read_registers(0x002E, 2, functioncode=3))
        print("Reg2:", inst.read_registers(0x0032, 2, functioncode=3))
        print("Reg3:", inst.read_registers(0x040C, 2, functioncode=3))
        print("Reg4:", inst.read_registers(0x0410, 2, functioncode=3))
        print("Reg5:", inst.read_registers(0x0030, 2, functioncode=3))
        print()
    except Exception as e:
        print(f"Device {sid} error:", e)
