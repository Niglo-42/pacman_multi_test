# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PACMAN42.

    Build:    uv run pyinstaller --noconfirm pacman.spec      (or: make package)
    Output:   dist/PACMAN42/           <- the folder to distribute
    Publish:  butler push dist/PACMAN42 <user>/pacman:<channel>

The game loads every asset through a path relative to the working directory
(e.g. "images/sprites/000.png", "font/press_start_2p.ttf", "config/..."), so
those trees must ship inside the bundle. pac-man.py chdir()s into the bundle
directory at startup when frozen, which keeps all those relative paths valid.
"""

datas = [
    ('images', 'images'),
    ('audio', 'audio'),
    ('font', 'font'),
    ('config', 'config'),
]

a = Analysis(
    ['pac-man.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['mazegenerator'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pydantic', 'mypy', 'flake8', 'pytest', 'tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PACMAN42',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='images/icon.ico',  # drop a .ico (Windows) / .icns (macOS) here to set one
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PACMAN42',
)
