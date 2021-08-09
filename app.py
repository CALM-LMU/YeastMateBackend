import os
import json
import threading
import tempfile

from flask import Flask
from flask_cors import CORS
from huey import  SqliteHuey

class ThreadSafeDict(dict) :
    def __init__(self, * p_arg, ** n_arg) :
        dict.__init__(self, * p_arg, ** n_arg)
        self._lock = threading.Lock()

    def __enter__(self) :
        self._lock.acquire()
        return self

    def __exit__(self, type, value, traceback) :
        self._lock.release()

executing_tasks = {}

app = Flask(__name__)
app.config.from_object(__name__)

CORS(app)

tmpdir = tempfile.gettempdir()
hueypath = os.path.join(tmpdir, 'huey.db')

print(hueypath)

huey =  SqliteHuey(filename=hueypath)
huey.storage.put_data('tasks', json.dumps({}).encode('utf-8'))
