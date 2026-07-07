# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Fuzzy Account Matcher.

Build commands:
    macOS:   pyinstaller fuzzy_matcher.spec
    Windows: pyinstaller fuzzy_matcher.spec

Output (one-folder bundle):
    macOS:   dist/FuzzyMatcher.app
    Windows: dist/FuzzyMatcher/FuzzyMatcher.exe
"""

import os
import sys
from pathlib import Path

ROOT = Path.cwd()

# Platform-specific icon
if sys.platform == "win32":
    APP_ICON = str(ROOT / "resources" / "icons" / "app.ico")
else:
    APP_ICON = str(ROOT / "resources" / "icons" / "app.icns")

# Use a fallback empty string if icon file hasn't been created yet
if not os.path.exists(APP_ICON):
    APP_ICON = None

block_cipher = None

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Bundle the resources folder
        (str(ROOT / "resources"), "resources"),
    ],
    hiddenimports=[
        # openpyxl internal modules PyInstaller misses
        "openpyxl",
        "openpyxl.cell._writer",
        "openpyxl.styles",
        "openpyxl.styles.differential",
        "openpyxl.utils",
        # pandas / numpy
        "pandas",
        "pandas._libs.tslibs.np_datetime",
        "pandas._libs.tslibs.timedeltas",
        "pandas._libs.tslibs.nattype",
        "pandas._libs.tslibs.timestamps",
        "pandas._libs.hashtable",
        "pandas._libs.missing",
        # rapidfuzz
        "rapidfuzz",
        "rapidfuzz.fuzz",
        "rapidfuzz.process",
        # PySide6 Qt plugins
        "PySide6.QtWidgets",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtPrintSupport",
    ],
    excludes=[
        # Exclude optional heavy deps that are not needed
        "pyarrow",
        "IPython",
        "jupyter",
        "notebook",
        "matplotlib",
        "scipy",
        "sklearn",
        "tensorflow",
        "torch",
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DRender",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia",
        "PySide6.QtNetwork",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
    ],
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
    name="FuzzyMatcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,       # No terminal window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=APP_ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FuzzyMatcher",
)

# macOS: wrap the COLLECT output in a .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="FuzzyMatcher.app",
        icon=APP_ICON,
        bundle_identifier="com.fuzzy-matcher.app",
        info_plist={
            "CFBundleDisplayName": "Fuzzy Account Matcher",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
        },
    )
