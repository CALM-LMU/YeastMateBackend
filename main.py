import logging

from huey.consumer import Consumer
from huey.consumer_options import ConsumerConfig
from huey.consumer_options import OptionParserHandler
from huey.utils import load_class

import multiprocessing
from multiprocessing import freeze_support, Process

from app import app
from app import huey
from tasks import *  # Import tasks so they are registered with Huey instance.
from views import *  # Import views so they are registered with Flask app.

def consumer_main():
    # Set up logging for the "huey" namespace.
    logger = logging.getLogger('huey')
    config = ConsumerConfig()
    config.setup_logger(logger)

    consumer = huey.create_consumer(workers=1, periodic=False, backoff=1)
    consumer.run()

def start_server(port=11001):
    try:
        app.run(host='0.0.0.0', port=port)
    except:
        start_server(port=port+1)


if __name__ == '__main__':
    freeze_support()
    proc = Process(target=consumer_main)
    proc.start()

    start_server(port=11001)