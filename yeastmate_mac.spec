# -*- mode: python ; coding: utf-8 -*-

import os
from ctypes.util import find_library
from pathlib import Path
from glob import glob

from PyInstaller.utils.hooks import get_package_paths

block_cipher = None

# Try and set lib-dynload and lib folder within conda environment automatically
# In case this fails and produces an error or non-functional builds, set these paths manually

package_path = get_package_paths('skimage')[1].split('/')

dynload_path = os.path.join(*package_path[:-2])
dynload_path = os.path.join(dynload_path, 'lib-dynload')
dynload_path = '/' + dynload_path

libpath = os.path.join(*package_path[:-2])

napari = Analysis(['annotation.py'],
             pathex=[],
             binaries=[],
             datas=[(get_package_paths('dask')[1],"dask"), 
                (get_package_paths('skimage')[1],"skimage"), 
                (get_package_paths('vispy')[1],"vispy"),
                (get_package_paths('scipy')[1],"scipy"), 
                (get_package_paths('napari')[1],"napari"), 
                (dynload_path, "lib-dynload") 
                ],
             hiddenimports=['skimage', 
                "vispy.ext._bundled.siz", "vispy.app.backends._pyqt5", 
                "napari", "PyQt5", "binascii"
                ],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

io = Analysis(['hueyserver.py'],
             pathex=[],
             binaries=[],
             datas=[
                (get_package_paths('jpype')[1],"jpype"),
                (get_package_paths('pims')[1],"pims"), 
                ('./tasks.py', '.'), ('./alignment.py', '.'), 
                ('./detection.py', '.'), ('./utils.py', '.'), 
                ('./views.py', '.'), ('./app.py', '.'), \
                ('./osx_libs/_sysconfigdata_i686_conda_cos6_linux_gnu.py', '.'), 
                ('./osx_libs/_sysconfigdata_m_darwin_darwin.py', '.'), 
                ('./osx_libs/_sysconfigdata_powerpc64le_conda_cos7_linux_gnu.py', '.'), 
                ('./osx_libs/_sysconfigdata_x86_64_apple_darwin13_4_0.py', '.'), 
                ('./osx_libs/_sysconfigdata_x86_64_conda_cos6_linux_gnu.py', '.') 
                ],
             hiddenimports=[ 'tasks', 'pims', 'jpype'],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

bento = Analysis(['bentoserver.py'],
             pathex=[],
             binaries=[],
             datas=[
                ('./yeastmate_cpu', 'yeastmate_cpu'),
                (get_package_paths('detectron2')[1],"detectron2"),
                (get_package_paths('yacs')[1],"yacs"),
                (get_package_paths('portalocker')[1],"portalocker"),
                (get_package_paths('iopath')[1],"iopath"),
                (get_package_paths('dask')[1],"dask"),
                (get_package_paths('pythonjsonlogger')[1],"pythonjsonlogger"),
                (get_package_paths('bentoml')[1],"bentoml"),
                (get_package_paths('fvcore')[1],"fvcore"),
                (get_package_paths('yeastmatedetector')[1],"yeastmatedetector"),
                (get_package_paths('tifffile')[1],"tifffile")
                ],            
             hiddenimports=[
                 'yeastmatedetector', 
                 'torch',
                 'torchvision',
                 'detectron2', 
                 'yacs', 
                 'portalocker', 
                 'scipy.special.cython_special', 
                 'opencv-python', 
                 'scikit-image', 
                 'pycocotools', 
                 'imgaug',
                 'tifffile', 
                 'fvcore',
                 'termcolor'
              ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

MERGE( (napari, 'napari', 'napari'), (io, 'hueyserver', 'hueyserver'), (bento, 'bentoserver', 'bentoserver') )

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
          name='YeastMateBackend',
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
               name='YeastMateBackend')

MISSING_DYLIBS = []

dll = glob(os.path.join(libpath, '*.dylib'))

for lib in dll:
    MISSING_DYLIBS.append(Path(lib))

bento.binaries += TOC([
    (lib.name, str(lib.resolve()), 'BINARY') for lib in MISSING_DYLIBS
])

bento_pyz = PYZ(bento.pure, bento.zipped_data,
             cipher=block_cipher)

bento_exe = EXE(bento_pyz,
          bento.scripts,
          [],
          exclude_binaries=True,
          name='YeastMateDetectionServer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

bento_coll = COLLECT(bento_exe,
               bento.binaries,
               bento.zipfiles,
               bento.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='YeastMateDetectionServer')

