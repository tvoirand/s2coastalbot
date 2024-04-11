"""
Custom logging module with predefined config.
"""

# standard library
import logging
import socket
from logging.handlers import RotatingFileHandler

APP_NAME = "s2coastalbot"
APP_VERSION = "0.9"


def get_custom_logger(log_file, level=20):
    """Create logger with predefined config.

    Parameters
    ----------
    log_file : Path
    level : int
        use logging.DEBUG, logging.INFO, ... or 10, 20, ... respectively

    Returns
    -------
    logger : logging.Logger
    """

    # create some paths
    log_file.parent.mkdir(exist_ok=True, parents=True)

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
        backupCount=100,  # create new files when maxbytes reached (up to 100 * 1 MB files)
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # create stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    logger.addHandler(stream_handler)

    return logger
