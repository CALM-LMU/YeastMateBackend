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

bento = Analysis(['bentoserver.py'],
             pathex=['C:\\Users\\david\\Projects\\MitoScannerBackend'],
             binaries=[],
             datas=[
                ('./yeastmate', 'yeastmate'),
                (get_package_paths('detectron2')[1],"detectron2"),
                (get_package_paths('yacs')[1],"yacs"),
                (get_package_paths('portalocker')[1],"portalocker"),
                (get_package_paths('iopath')[1],"iopath"),
                (get_package_paths('dask')[1],"dask"),
                (get_package_paths('pythonjsonlogger')[1],"pythonjsonlogger"),
                (get_package_paths('bentoml')[1],"bentoml"),
                (get_package_paths('fvcore')[1],"fvcore"),
                (get_package_paths('biodetectron')[1],"biodetectron"),
                (get_package_paths('tifffile')[1],"tifffile")
                ],            
             hiddenimports=[
                 'biodetectron', 
                 'torch',
                 'torchvision',
                 'detectron2', 
                 'pythonjsonlogger', 
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

MISSING_DYLIBS = []

dll = glob('C:\\Users\\david\\miniconda3\\envs\\fullpackage\\Library\\bin\\*.dll')

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
          name='YeastMateDetector',
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
               name='YeastMateDetector')
