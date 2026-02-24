from pyModbusTCP.client import ModbusClient

client = ModbusClient(
    host='192.168.0.69',
    port=502,
    unit_id=1,
    auto_open=True,
    auto_close=False,
    timeout=3
)

try:
    regs = client.read_holding_registers(100, 10)
    if regs is None:
        raise RuntimeError("레지스터 읽기 실패")

    print("읽은 데이터:", regs)

    ok = client.write_single_register(100, 123)
    if not ok:
        raise RuntimeError("레지스터 쓰기 실패")

finally:
    client.close()
