from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('debugpy', include_py_files=True)