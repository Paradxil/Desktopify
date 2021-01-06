# -*- mode: python -*-
# -*- coding: utf-8 -*-

"""
This is a PyInstaller spec file.
"""

import os
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import is_module_satisfies
from PyInstaller.archive.pyz_crypto import PyiBlockCipher

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

a = Analysis(
    ["./desktopifyBrowser.py"],
    hookspath=["./"],  # To find "hook-cefpython3.py"
    cipher=None,
    win_private_assemblies=True,
    win_no_prefer_redirects=True,
)

pyz = PYZ(a.pure,
          a.zipped_data,
          cipher=None)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name="DesktopifyBrowser",
          debug=False,
          strip=False,
          upx=False,
          console=False)

COLLECT(exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name="DesktopifyBrowser")
