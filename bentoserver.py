def script_method(fn, _rcb=None):
    return fn
def script(obj, optimize=True, _frames_up=0, _rcb=None):
    return obj    
import torch.jit
torch.jit.script_method = script_method 
torch.jit.script = script

import os
os.environ['PATH'] += (os.path.dirname(os.path.realpath(__file__)))

import argparse
from bentoml.server import start_dev_server
from multiprocessing import freeze_support

path = os.getcwd()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int, help='Port of bentoml server.')
    parser.add_argument('device', type=str, help='Set device to cpu or gpu.')
    args = parser.parse_args()

    freeze_support()

    if args.device == 'cpu':
        module = 'yeastmate_cpu'
    elif args.device == 'gpu' and torch.cuda.is_available() == True:
        module = 'yeastmate_gpu'
    else:
        module = 'yeastmate_cpu'

    start_dev_server(os.path.join(path, module), args.port, False, False)