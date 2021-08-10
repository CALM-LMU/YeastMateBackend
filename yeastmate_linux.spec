# -*- mode: python ; coding: utf-8 -*-

import os
from ctypes.util import find_library
from pathlib import Path
from glob import glob

from PyInstaller.utils.hooks import get_package_paths

block_cipher = None

package_path = get_package_paths('skimage')[1].split('/')
dynload_path = os.path.join(*package_path[:-2])
dynload_path = os.path.join(dynload_path, 'lib-dynload')
dynload_path = '/' + dynload_path

napari = Analysis(['annotation.py'],
             pathex=['/home/bunk/YeastMateBackend/'],
             binaries=[],
             datas=[(get_package_paths('dask')[1],"dask"), \
                (get_package_paths('skimage')[1],"skimage"), \
                (get_package_paths('vispy')[1],"vispy"),\
                (get_package_paths('scipy')[1],"scipy"), \
                (get_package_paths('napari')[1],"napari"), \
		(get_package_paths('PySide2')[1],"PySide2"), \
                (get_package_paths('PyQt5')[1],"PyQt5"), \
                (dynload_path, "lib-dynload") 
                ],
             hiddenimports=['skimage', \
                "vispy.ext._bundled.siz", \
                "napari", "binascii",
                "PySide2.QtWidgets", "PySide2.QtGui", "PySide2.QtCore", "PySide2.QtOpenGL","PyQt5.QtOpenGL"
                ],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

io = Analysis(['main.py'],
             pathex=['/home/bunk/YeastMateBackend/'],
             binaries=[],
             datas=[(get_package_paths('pims')[1],"pims"), \
                (get_package_paths('pims_nd2')[1],"pims_nd2"), \
                ('./tasks.py', '.'), ('./alignment.py', '.'), \
                ('./detection.py', '.'), ('./utils.py', '.'), \
                ('./views.py', '.'), ('./app.py', '.'), \
                ],
             hiddenimports=[ 'tasks', 'pims', 'pims_nd2'],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

MERGE( (napari, 'napari', 'napari'), (io, 'main', 'backend') )

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

