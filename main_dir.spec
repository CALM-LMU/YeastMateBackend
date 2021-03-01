# -*- mode: python ; coding: utf-8 -*-

from ctypes.util import find_library
from pathlib import Path
from glob import glob

from PyInstaller.utils.hooks import get_package_paths

block_cipher = None

a = Analysis(['main.py'],
             pathex=['C:\\Users\\david\\Projects\\MitoScannerBackend'],
             binaries=[],
             datas=[(get_package_paths('dask')[1],"dask"), (get_package_paths('pims')[1],"pims"), (get_package_paths('pims_nd2')[1],"pims_nd2"), (get_package_paths('skimage')[1],"skimage"), ('./tasks.py', '.'), ('./alignment.py', '.'), ('./utils.py', '.'), ('./views.py', '.'), ('./app.py', '.')],
             hiddenimports=['scipy.special.cython_special', 'tasks', 'skimage', 'pims', 'pims_nd2'],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

MISSING_DYLIBS = [
    Path(find_library("libiomp5md")),
    Path(find_library("vcruntime140")),
    Path(find_library("msvcp140")),
    Path('C:\\Users\\david\\miniconda3\\Lib\\site-packages\\pims_nd2\\ND2SDK\\win\\nd2ReadSDK.h')
]

nd2lib = glob('C:\\Users\\david\\miniconda3\\Lib\\site-packages\\pims_nd2\\ND2SDK\\win\\x64\\*')

for lib in nd2lib:
    print(lib)
    MISSING_DYLIBS.append(Path(lib))

a.binaries += TOC([
    (lib.name, str(lib.resolve()), 'BINARY') for lib in MISSING_DYLIBS
])

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='YeastMateIO',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='YeastMateIO')
