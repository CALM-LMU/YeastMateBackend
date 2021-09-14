# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import get_package_paths
from ctypes.util import find_library
from pathlib import Path

import os
import sys
from glob import glob

sys.modules["FixTk"] = None

block_cipher = None

annotation = Analysis(['annotation.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=['hooks'],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[
               "FixTk",
               "tcl",
               "tk",
               "_tkinter",
               "tkinter",
               "Tkinter",
               "matplotlib",
            ],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

huey = Analysis(['hueyserver.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=['cv2'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

server = Analysis(['yeastmate_server.py'],
             pathex=[],
             binaries=[(find_library('uv'), '.')] if find_library('uv') is not None else [],
             datas=[
                 ('./yeastmate-artifacts', 'yeastmate-artifacts'),
                 (get_package_paths('cv2')[1],"cv2")
             ],
             hiddenimports=[],
             hookspath=['hooks'],
             hooksconfig={},
             runtime_hooks=[],
             excludes=['matplotlib', 'caffe2'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

MERGE( (annotation, 'annotation', 'annotation'), (huey, 'hueyserver', 'hueyserver'), (server, 'yeastmate_server', 'yeastmate_server') )

annotation_pyz = PYZ(annotation.pure, annotation.zipped_data,
             cipher=block_cipher)

annotation_exe = EXE(annotation_pyz,
          annotation.scripts, 
          [],
          exclude_binaries=True,
          name='annotation',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )

annotation_coll = COLLECT(annotation_exe,
               annotation.binaries,
               annotation.zipfiles,
               annotation.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='annotation')

huey_pyz = PYZ(huey.pure, huey.zipped_data,
             cipher=block_cipher)

huey_exe = EXE(huey_pyz,
          huey.scripts, 
          [],
          exclude_binaries=True,
          name='hueyserver',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )

huey_coll = COLLECT(huey_exe,
               huey.binaries,
               huey.zipfiles,
               huey.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='hueyserver')

MISSING_DYLIBS = []

dll = glob(os.path.join(os.environ['CONDA_PREFIX'], 'Library/bin/*.dll'))

for lib in dll:
    MISSING_DYLIBS.append(Path(lib))

server.binaries += TOC([
    (lib.name, str(lib.resolve()), 'BINARY') for lib in MISSING_DYLIBS
])

server_pyz = PYZ(server.pure, server.zipped_data,
             cipher=block_cipher)

server_exe = EXE(server_pyz,
          server.scripts, 
          [],
          exclude_binaries=True,
          name='yeastmate_server',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )

server_coll = COLLECT(server_exe,
               server.binaries,
               server.zipfiles,
               server.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='yeastmate_server')
