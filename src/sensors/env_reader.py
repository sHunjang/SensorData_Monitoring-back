"""
env_reader.py
- CWT-XYTH 온습도 센서 (RS485 Modbus RTU)
- Slave IDs: 21, 22, 23
- 반환 dict: {"temperature": float, "humidity": float}
"""

import minimalmodbus

def create_instrument(port="COM8", slave_id=21, baudrate=9600) -> minimalmodbus.Instrument:
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
    Holding Register 0x0000 ~ 0x0001 (2개) 읽어서 습도/온도 반환
    - Function Code: 0x03
    - 응답 데이터: [습도, 온도] (각각 16bit)
    - 단위: 0.1 (%RH, ℃)
    """
    try:
        # 레지스터 0~1 → 2개 값 읽기
        regs = inst.read_registers(0, 2, functioncode=3)

        if len(regs) != 2:
            raise ValueError("Invalid response length")

        raw_humi, raw_temp = regs

        # 습도 (%RH)
        humidity = raw_humi / 10.0

        # 온도 (℃) → 매뉴얼 상 보정 필요할 수 있음
        temperature = (raw_temp / 10.0) - 41.0  # 예: 38.5 → -2.5 ℃

        return {
            "temperature": round(temperature, 1),
            "humidity": round(humidity, 1),
        }
    except Exception as e:
        raise RuntimeError(f"Env sensor read failed: {e}")
