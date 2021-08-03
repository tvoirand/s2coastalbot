"""
s2coastalbot main script.
Twitter bot that posts newly acquired Sentinel-2 images of coastal areas.
"""

# standard imports
import os
import argparse
import configparser
import json
import requests

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


def get_location_name(lat, lon):
    """
    Convert latitude and longitude into an address using OSM
    Input:
        -lat    float
        -lon    float
    Output:
        -       str
    """

    headers = {"Accept-Language": "en-US,en;q=0.8"}
    url = "http://nominatim.openstreetmap.org/reverse?lat={}&lon={}&".format(lat, lon)
    url += "addressdetails=0&format=json&zoom=6&extratags=0"

    response = json.loads(requests.get(url, headers=headers).text)

    if "error" in response:
        return "Unknown location, do you recognise it?"

    return response["display_name"]


class S2CoastalBot:
    """
    Class for S2CoastalBot.
    """

    def __init__(self):
        """
        Constructor for the S2CoastalBot class.
        """

        # read config
        config_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "config", "config.ini"
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
        tci_file_path = download_tci_image(copernicus_user, copernicus_password, aoi_file)

        # authenticate twitter account
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth)

        # post tweet
        api.update_status(status="Not implemented yet")


if __name__ == "__main__":

    s2coastalbot = S2CoastalBot()
