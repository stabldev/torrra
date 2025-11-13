# -*- mode: python ; coding: utf-8 -*-
import os
from glob import glob


css_files = glob("src/torrra/**/*.css", recursive=True)
additional_datas = [
    (f, os.path.dirname(f).replace("src/", "")) for f in css_files
]

a = Analysis(
    ["src/torrra/__main__.py"],
    pathex=[],
    binaries=[],
    datas=additional_datas,
    hiddenimports=[
      "torrra.indexers.jackett",
      "torrra.indexers.prowlarr",
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
    name="torrra",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
