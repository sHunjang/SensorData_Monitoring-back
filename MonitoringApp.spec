# MonitoringApp.spec - 실제 센서 라이브러리 포함

# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('.env', '.'), ('../front/dist', 'dist'), ('src', 'src')],
    
    # 🔧 실제 센서 라이브러리 추가
    hiddenimports=[
        'src.api', 
        'src.collectors',
        'src.sensors',                 # 센서 모듈 추가
        'pymodbus',                   # Modbus 통신
        'pymodbus.client',            # Modbus 클라이언트
        'pymodbus.client.sync',       # 동기식 클라이언트
        'pymodbus.exceptions',        # 예외 처리
        'minimalmodbus',              # 환경/태양광 센서용
        'serial',                     # pyserial
        'serial.tools',               # 시리얼 도구
        'serial.tools.list_ports',    # 포트 검색
    ],
    
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MonitoringApp',
    debug=False,                      # 🔧 디버그용으로 True 변경 가능
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,                     # 콘솔 창 표시 (로그 확인용)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
