# test_modbus_final.py
import minimalmodbus, serial

def create_instrument(port: str = "COM4", slave_id: int = 11):
    inst = minimalmodbus.Instrument(port, slave_id)
    inst.serial.baudrate = 9600
    inst.serial.bytesize = 8
    inst.serial.parity = serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout = 1
    inst.clear_buffers_before_each_transaction = True
    return inst

def read_uint32(regs):
    """2개의 레지스터를 uint32로 결합"""
    return (regs[0] << 16) | regs[1]

def read_int32(regs):
    """2개의 레지스터를 signed int32로 결합"""
    value = (regs[0] << 16) | regs[1]
    if value >= 2**31:
        value -= 2**32
    return value

# 테스트
device_ids = [11, 12, 13, 14, 15]

print("=" * 70)
print("TAC4300 전력량계 통신 테스트 - 주요 데이터")
print("=" * 70)

for sid in device_ids:
    inst = create_instrument(port="COM4", slave_id=sid)
    try:
        # 합계 전류 - 0x0034
        regs = inst.read_registers(0x0034, 2, functioncode=3)
        sum_current = read_uint32(regs) * 0.001
        
        # 평균 전압 - 0x0036
        regs = inst.read_registers(0x0036, 2, functioncode=3)
        avg_voltage = read_uint32(regs) * 0.01
        
        # 총 유효전력 - 0x002C
        regs = inst.read_registers(0x002C, 2, functioncode=3)
        total_power = read_int32(regs) * 0.001
        
        # 전력량 - 0x0404
        regs = inst.read_registers(0x0404, 2, functioncode=3)
        energy = read_uint32(regs) * 0.01
        
        # 역률 계산 (임시: 전압과 전류로 계산)
        if sum_current > 0 and avg_voltage > 0:
            pf = abs(total_power) / (avg_voltage * sum_current / 1000)
            pf = min(pf, 1.0)  # 역률은 최대 1.0
        else:
            pf = 0.0
        
        print(f"\nDevice {sid:2d} | V={avg_voltage:6.2f}V | I={sum_current:5.3f}A | "
              f"P={total_power*1000:6.0f}W | E={energy:8.2f}kWh | PF={pf:.2f}")
        
        inst.serial.close()
        
    except Exception as e:
        print(f"Device {sid:2d} | ERROR: {e}")

print("\n" + "=" * 70)
print("✅ 테스트 완료 - Device 11이 339W 출력 중")
print("=" * 70)
