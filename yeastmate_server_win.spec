# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import get_package_paths
from ctypes.util import find_library

block_cipher = None

a = Analysis(['yeastmate_server.py'],
             pathex=[],
             binaries=[(find_library('uv'), '.')] if find_library('uv') is not None else [],
             datas=[
                 ('./yeastmate-artifacts', 'yeastmate-artifacts'),
             ],
             hiddenimports=[],
             hookspath=['hooks'],
             hooksconfig={},
             runtime_hooks=[],
             excludes=['matplotlib', 'caffe2', 'cv2'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
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
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='yeastmate_server')
