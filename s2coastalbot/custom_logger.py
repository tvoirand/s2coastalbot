"""
Custom logging module with predefined config.
"""

# standard imports
import os
import logging
from logging.handlers import RotatingFileHandler
import socket

APP_NAME = "s2coastalbot"
APP_VERSION = "0.5"


def get_custom_logger(log_file, level=20):
    """Create logger with predefined config.

    Parameters
    ----------
    log_file : str
    level : int
        use logging.DEBUG, logging.INFO, ... or 10, 20, ... respectively

    Returns
    -------
    logger : logging.Logger
    """

    # create some paths
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))

    # create logger
    logger = logging.getLogger()
    logger.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d {} {} {} [%(process)d]: [%(levelname).1s] %(message)s".format(
            socket.gethostname(),
            APP_NAME,
            APP_VERSION,
        ),
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # create file handler
    file_handler = RotatingFileHandler(  # redirect logs to rotating file
        log_file,
        maxBytes=1000000,
        backupCount=1,  # create new files when maxbytes reached
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # create stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    logger.addHandler(stream_handler)

    return logger
