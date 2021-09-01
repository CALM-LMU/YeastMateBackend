# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import get_package_paths
from ctypes.util import find_library

block_cipher = None

a = Analysis(['yeastmate_server.py'],
             pathex=['C:\\Users\\david\\Documents\\workspace\\YeastMateBackend'],
             binaries=[(find_library('uv'), '.')],
             datas=[
                 ('./yeastmate-artifacts', 'yeastmate-artifacts'),
#                (get_package_paths('detectron2')[1],"detectron2"),
#                (get_package_paths('yacs')[1],"yacs"),
#                (get_package_paths('portalocker')[1],"portalocker"),
#                (get_package_paths('iopath')[1],"iopath"),
#                (get_package_paths('dask')[1],"dask"),
#                (get_package_paths('pythonjsonlogger')[1],"pythonjsonlogger"),
#                (get_package_paths('flask')[1],"flask"),
#                (get_package_paths('waitress')[1],"waitress"),
#                (get_package_paths('omegaconf')[1],"omegaconf"),
#                (get_package_paths('fvcore')[1],"fvcore"),
#                (get_package_paths('yeastmatedetector')[1],"yeastmatedetector"),
#                (get_package_paths('tifffile')[1],"tifffile")
             ],
             hiddenimports=[
#                 'yeastmatedetector',
#                 'torch',
#                 'torchvision',
#                 'detectron2', 
#                 'pythonjsonlogger', 
#                 'yacs',
#                 'omegaconf',
#                 'antlr4',
#                 'portalocker', 
#                 'scipy.special.cython_special', 
#                 'opencv-python', 
#                 'scikit-image', 
#                 'pycocotools', 
#                 'imgaug',
#                 'tifffile', 
#                 'fvcore',
#                 'termcolor',
#                 'flask',
#                 'waitress'
              ],
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
