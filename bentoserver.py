def script_method(fn, _rcb=None):
    return fn
def script(obj, optimize=True, _frames_up=0, _rcb=None):
    return obj    
import torch.jit
torch.jit.script_method = script_method 
torch.jit.script = script

import os
os.environ['PATH'] += (os.path.dirname(os.path.realpath(__file__)))

from bentoml.server import start_dev_server
from multiprocessing import freeze_support

path = os.getcwd()

if __name__ == '__main__':
    freeze_support()
    start_dev_server(os.path.join(path, 'yeastmate'), 5000, False, False)