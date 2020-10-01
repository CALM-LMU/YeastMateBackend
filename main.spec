# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from glob import glob

from PyInstaller.utils.hooks import get_package_paths

block_cipher = None

a = Analysis(['main.py'],
             pathex=['C:\\Users\\david\\Projects\\MitoScannerBackend'],
             binaries=[],
             datas=[(get_package_paths('dask')[1],"dask"), ('./tasks.py', '.'), ('./alignment.py', '.'), ('./utils.py', '.'), ('./views.py', '.'), ('./app.py', '.')],
             hiddenimports=['pims_nd2', 'huey', 'scipy', 'scipy.special.cython_special', 'pkg_resources.py2_warn', 'dask', 'tasks', 'opencv-python', 'scikit-image'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

MISSING_DYLIBS = [
    Path('C:\\Users\\david\\miniconda3\\Lib\\site-packages\\pims_nd2\\ND2SDK\\win\\nd2ReadSDK.h')
]

nd2lib = glob('C:\\Users\\david\\miniconda3\\Lib\\site-packages\\pims_nd2\\ND2SDK\\win\\x64\\*')

for lib in nd2lib:
    MISSING_DYLIBS.append(Path(lib))

a.binaries += TOC([
    (lib.name, str(lib.resolve()), 'BINARY') for lib in MISSING_DYLIBS
])

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='YeastMateBackend',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
