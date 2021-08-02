import sys
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

if __name__ == '__main__':
    # Parse arguments from Electron frontend.
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=str, help='Port to serve backend on.')
    args = parser.parse_args()

    port = int(args.port)

    # Freeze and start huey worker
    freeze_support()
    proc = Process(target=consumer_main)
    proc.start()

    # Start flask server
    app.run(host='0.0.0.0', port=port)