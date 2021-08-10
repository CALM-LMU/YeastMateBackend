# -*- mode: python ; coding: utf-8 -*-

from ctypes.util import find_library
from pathlib import Path
from glob import glob

from PyInstaller.utils.hooks import get_package_paths

block_cipher = None

napari = Analysis(['annotation.py'],
             pathex=['C:\\Users\\david\\Projects\\MitoScannerBackend'],
             binaries=[],
             datas=[(get_package_paths('dask')[1],"dask"), (get_package_paths('skimage')[1],"skimage"), (get_package_paths('vispy')[1],"vispy"),(get_package_paths('napari')[1],"napari")],
             hiddenimports=['scipy.special.cython_special', 'skimage', "vispy.ext._bundled.siz", "vispy.app.backends._pyqt5", "napari", "PyQt5"],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

io = Analysis(['hueyserver.py'],
             pathex=['C:\\Users\\david\\Projects\\MitoScannerBackend'],
             binaries=[],
             datas=[(get_package_paths('jpype')[1],"jpype"),(get_package_paths('pims')[1],"pims"), ('./tasks.py', '.'), ('./alignment.py', '.'), ('./detection.py', '.'), ('./utils.py', '.'), ('./views.py', '.'), ('./app.py', '.')],
             hiddenimports=[ 'tasks', 'pims', 'jpype'],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

MERGE( (napari, 'napari', 'napari'), (io, 'hueyserver', 'hueyserver') )

napari_pyz = PYZ(napari.pure, napari.zipped_data,
             cipher=block_cipher)

napari_exe = EXE(napari_pyz,
          napari.scripts, 
          [],
          exclude_binaries=True,
          name='YeastMateAnnotation',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
napari_coll = COLLECT(napari_exe,
               napari.binaries,
               napari.zipfiles,
               napari.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='YeastMateAnnotation')

io_pyz = PYZ(io.pure, io.zipped_data,
             cipher=block_cipher)

MISSING_DYLIBS = [
    Path(find_library("libiomp5md")),
    Path(find_library("vcruntime140")),
    Path(find_library("msvcp140"))
    ]

io.binaries += TOC([
    (lib.name, str(lib.resolve()), 'BINARY') for lib in MISSING_DYLIBS
])

io_exe = EXE(io_pyz,
          io.scripts,
          [],
          exclude_binaries=True,
          name='YeastMateIO',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

io_coll = COLLECT(io_exe,
               io.binaries,
               io.zipfiles,
               io.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='YeastMateIO')
