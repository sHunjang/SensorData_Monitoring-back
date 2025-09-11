"""
env_reader.py
- RS485 온습도 센서 (예: Slave ID 21, 22, 23)
- 반환 dict: {"temperature": float, "humidity": float}
"""

import minimalmodbus

def create_instrument(port="COM7", slave_id=21, baudrate=9600) -> minimalmodbus.Instrument:
    """RS485 장치 핸들 생성"""
    inst = minimalmodbus.Instrument(port, slave_id)
    inst.serial.baudrate = baudrate
    inst.serial.bytesize = 8
    inst.serial.parity = minimalmodbus.serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout = 1
    inst.mode = minimalmodbus.MODE_RTU
    return inst

def read_env(inst: minimalmodbus.Instrument) -> dict:
    """
    Modbus Holding Register에서 온도/습도 읽기
    - 예시: 0x0000 = 온도, 0x0001 = 습도
    - 데이터 타입: 16-bit unsigned integer
    - 스케일: 0.1 단위 (예: 253 → 25.3 °C)
    """
    try:
        # 온도 레지스터
        raw_temp = inst.read_register(0, 0, functioncode=3, signed=False)
        temperature = raw_temp / 10.0

        # 습도 레지스터
        raw_humi = inst.read_register(1, 0, functioncode=3, signed=False)
        humidity = raw_humi / 10.0

        return {
            "temperature": round(temperature, 1),
            "humidity": round(humidity, 1),
        }
    except Exception as e:
        raise RuntimeError(f"Env sensor read failed: {e}")
