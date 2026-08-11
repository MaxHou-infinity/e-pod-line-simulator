# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置（V3.2 P2）

用法（在 e_pod_line_simulator 目录）：
    pyinstaller --noconfirm packaging/e_pod_line_simulator.spec
"""

import os

from PyInstaller.utils.hooks import collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [
    (os.path.join(ROOT, "assets"), "assets"),
    (os.path.join(ROOT, "configs"), "configs"),
]

hiddenimports = (
    collect_submodules("simpy")
    + collect_submodules("pandas")
    + collect_submodules("openpyxl")
    + collect_submodules("reportlab")
)

a = Analysis(
    [os.path.join(ROOT, "run.py")],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="E-Pod-Line-Simulator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="E-Pod-Line-Simulator",
)

app = BUNDLE(
    coll,
    name="E-Pod-Line-Simulator.app",
    icon=None,
    bundle_identifier="com.maxhou.e-pod-line-simulator",
)
