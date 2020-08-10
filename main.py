import logging

from huey.consumer import Consumer
from huey.consumer_options import ConsumerConfig
from huey.consumer_options import OptionParserHandler
from huey.utils import load_class

from multiprocessing import freeze_support, Process

from app import app
from app import huey
import tasks  # Import tasks so they are registered with Huey instance.
import views  # Import views so they are registered with Flask app.

def consumer_main():
    # Set up logging for the "huey" namespace.
    logger = logging.getLogger('huey')
    config = ConsumerConfig()
    config.setup_logger(logger)

    consumer = huey.create_consumer(workers=4, periodic=False, backoff=1)
    consumer.run()

if __name__ == '__main__':
    freeze_support()
    proc = Process(target=consumer_main)
    proc.start()
    app.run()