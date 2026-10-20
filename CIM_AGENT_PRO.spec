# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['CIM_AGENT_LOADER.py'],
    pathex=[],
    binaries=[],
    datas=[('FINAL_AGENT_PRO.py', '.')],
    hiddenimports=[
        'mss',
        'PIL',
        'PIL.Image',
        'websockets',
        'requests',
        'urllib.request',
        'asyncio',
        'threading',
        'ctypes',
        'ctypes.wintypes',
        'winreg',
        'shutil',
        'webbrowser'
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
    name='02_학생용_모니터링_에이전트_전송용v3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
