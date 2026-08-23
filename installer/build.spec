# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['..\\source\\main.py'],
    pathex=['..\\source'],
    binaries=[
        ('..\\dlls\\64_lib\\*.dll', 'dlls\\64_lib'),
        ('..\\dlls\\control\\FTD2XX.dll', 'dlls\\control'),
        ('..\\dlls\\control\\KURIOS_COMMAND_LIB_Win64.dll', 'dlls\\control'),
    ],
    datas=[
        ('..\\source\\data', 'source\\data'),
        ('..\\dlls\\64_lib\\thorlabs_tsi_logger.cfg', 'dlls\\64_lib'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MultispectralSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    contents_directory='_internal',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MultispectralSystem',
)
