# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for building verify.exe on Windows
# Usage:  pyinstaller verify.spec

import sys
from PyInstaller.utils.hooks import collect_all

# Collect all files from verify_core (probes self-register at import time)
core_datas, core_binaries, core_hiddenimports = collect_all('verify_core')
cli_datas,  cli_binaries,  cli_hiddenimports  = collect_all('verify_cli')

a = Analysis(
    ['verify_cli/main.py'],
    pathex=[],
    binaries=core_binaries + cli_binaries,
    datas=core_datas + cli_datas + [
        ('../../data/15code_catalog/models.yaml', 'data/15code_catalog'),
    ],
    hiddenimports=core_hiddenimports + cli_hiddenimports + [
        'tiktoken_ext.openai_public',
        'tiktoken_ext',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['numpy', 'scipy', 'matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    [],
    name='verify',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
