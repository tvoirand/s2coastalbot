"""
Custom logging module with predefined config.
"""

# standard imports
import os
import logging
from logging.handlers import RotatingFileHandler


def get_custom_logger(project_name, level=20):
    """Create logger with predefined config.

    Parameters
    ----------
    project_name : str
    level : int
        use logging.DEBUG, logging.INFO, ... or 10, 20, ... respectively

    Returns
    -------
    logger : logging.Logger
    """

    # create some paths
    logs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "logs")
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)

    # create logger
    logger = logging.getLogger()
    logger.setLevel(level)
    formatter = logging.Formatter("%(asctime)s :: %(levelname)s :: %(message)s")

    # create file handler
    file_handler = RotatingFileHandler( # redirect logs to rotating file
        os.path.join(logs_path, "{}.log".format(project_name)),
        maxBytes=1000000,
        backupCount=1, # create new files when maxbytes reached
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # create stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    logger.addHandler(stream_handler)

    return logger
