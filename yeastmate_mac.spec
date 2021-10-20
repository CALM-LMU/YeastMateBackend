# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import get_package_paths
from PyInstaller.utils.hooks import collect_dynamic_libs
from pathlib import Path
from ctypes.util import find_library

import sys
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
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

server = Analysis(['yeastmate_server.py'],
             pathex=[],
             binaries=[(find_library('uv'), '.')] if find_library('uv') is not None else [],
             datas=[
                 ('./models', 'models'),
                 # TODO: do this more cleanly via hook?
                 (get_package_paths('torchvision')[1],"torchvision"),
             ],
             hiddenimports=[],
             hookspath=['hooks'],
             hooksconfig={},
             runtime_hooks=[],
             excludes=['matplotlib'],
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

# NB: we exclude torch dynamic libraries, as another copy will be put in the torch folder
# otherwise, the detection server fails to start with some C++ error
# https://stackoverflow.com/a/56853037
# excluded_binaries = ['libtorch_cpu.dylib']
# excluded_binaries = [Path(lib[0]).name for lib in collect_dynamic_libs('torch')]
# server.binaries = TOC([x for x in server.binaries if x[0] not in excluded_binaries])

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
