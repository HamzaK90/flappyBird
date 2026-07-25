# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build spec for a single-file, windowed desktop build.
#
#   pip install pyinstaller
#   pyinstaller FlappyBird.spec
#
# The result is dist/FlappyBird (an .exe on Windows) with assets/ bundled in.
# For a Windows taskbar icon, convert a sprite to .ico and add icon='app.ico'
# to the EXE(...) call below.

a = Analysis(
    ['flappy_bird.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FlappyBird',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed app, no terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
