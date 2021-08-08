"""
s2coastalbot main script.
Twitter bot that posts newly acquired Sentinel-2 images of coastal areas.
"""

# standard imports
import os
import argparse
import configparser
import logging

# third party imports
import tweepy
from sentinelsat import SentinelAPI
from sentinelsat import SentinelProductsAPI
from sentinelsat import make_path_filter
from sentinelsat import read_geojson
from sentinelsat import geojson_to_wkt
import pandas as pd

# local project imports
from s2coastalbot.sentinel2 import download_tci_image
from s2coastalbot.postprocessing import postprocess_tci_image
from s2coastalbot.custom_logger import get_custom_logger
from s2coastalbot.geoutils import get_location_name


class S2CoastalBot:
    """
    Class for S2CoastalBot.
    """

    def __init__(self):
        """
        Constructor for the S2CoastalBot class.
        """

        # create logger
        logger = get_custom_logger("s2coastalbot", logging.INFO)

        # read config
        logger.info("Reading config")
        config_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            "config",
            "config.ini",
        )
        config = configparser.ConfigParser()
        config.read(config_file)
        copernicus_user = config.get("access", "copernicus_user")
        copernicus_password = config.get("access", "copernicus_password")
        aoi_file = config.get("misc", "aoi_file")
        consumer_key = config.get("access", "consumer_key")
        consumer_secret = config.get("access", "consumer_secret")
        access_token = config.get("access", "access_token")
        access_token_secret = config.get("access", "access_token_secret")

        # download Sentinel-2 True Color Image
        logger.info("Downloading Sentinel-2 TCI image")
        tci_file_path, center_coords = download_tci_image(
            copernicus_user, copernicus_password, aoi_file
        )

        # postprocess image to fit twitter contraints
        logger.info("Postprocessing image")
        postprocessed_file_path = postprocess_tci_image(tci_file_path)

        # authenticate twitter account
        logger.info("Authenticating against twitter API")
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth)

        # post tweet
        logger.info("Posting tweet")
        api.update_with_media(
            filename=postprocessed_file_path, status=get_location_name(center_coords)
        )


if __name__ == "__main__":

    s2coastalbot = S2CoastalBot()
