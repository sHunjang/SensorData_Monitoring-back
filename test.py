# test_pymodbus_install.py - 설치 확인

def test_pymodbus_installation():
    """pymodbus 설치 상태 확인"""
    
    print("🔍 pymodbus 설치 상태 확인...")
    
    try:
        # v3.x 방식 시도
        from pymodbus.client import ModbusSerialClient
        print("✅ pymodbus v3.x 설치 확인됨")
        
        # 버전 확인
        import pymodbus
        version = getattr(pymodbus, '__version__', '버전 불명')
        print(f"📦 pymodbus 버전: {version}")
        
        # 클라이언트 생성 테스트
        client = ModbusSerialClient(port='COM1', baudrate=9600, timeout=1)
        print("✅ ModbusSerialClient 생성 성공")
        
        return True
        
    except ImportError as e:
        print(f"❌ pymodbus 설치 실패: {e}")
        print("💡 해결책: pip install pymodbus==3.6.8")
        return False
    
    except Exception as e:
        print(f"⚠️  pymodbus 설치되었으나 문제 발생: {e}")
        return False

if __name__ == "__main__":
    if test_pymodbus_installation():
        print("\n🎉 pymodbus 설치 및 설정 완료!")
        print("이제 MODE=real로 설정하여 실제 장비와 통신할 수 있습니다.")
    else:
        print("\n❌ pymodbus 설치에 문제가 있습니다.")
        print("Miniconda 환경에서 다음 명령어를 실행하세요:")
        print("pip install pymodbus==3.6.8 pyserial==3.5")
