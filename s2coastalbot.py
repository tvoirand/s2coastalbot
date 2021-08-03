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


def download_tci_image(copernicus_user, copernicus_password, aoi_file, output_folder=None):
    """
    Randomly find newly acquired Sentinel-2 image of coastal area.
    Input:
        -copernicus_user        str
        -copernicus_password    str
        -aoi_file               str
    """

    def find_tci_file(product_path):
        """Look for TCI file within S2 product"""
        for path, dirs, files in os.walk(product_path):
            if path.endswith("IMG_DATA"):
                for f in files:
                    if f.lower().endswith("_tci.jp2"):
                        return os.path.join(path, f)
        return None

    # connect to APIs
    api = SentinelAPI(copernicus_user, copernicus_password)
    products_api = SentinelProductsAPI(copernicus_user, copernicus_password)

    # read footprint
    footprint = geojson_to_wkt(read_geojson(aoi_file))

    # search images
    products = api.query(
        footprint,
        date=("NOW-6DAY", "NOW"),
        platformname="Sentinel-2",
    )

    # convert to Pandas DataFrame
    products_df = api.to_dataframe(products)

    # filter out products with coulds and randomly pick one product
    products_df = products_df[products_df["cloudcoverpercentage"] < 0.05]
    product_row = products_df.sample(n=1).iloc[0]

    # create output folder if necessary
    if output_folder is None:
        output_folder = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "data"
        )
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # download only TCI band
    nodefilter = make_path_filter("*_tci.jp2")
    product_info = products_api.download(
        product_row["uuid"], directory_path=output_folder, nodefilter=nodefilter
    )

    # return tci file path
    safe_path = os.path.join(output_folder, product_info["node_path"][2:])
    return find_tci_file(safe_path)


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

        print("not implemented yet")

    def authenticate_twitter():
        """
        Twitter authentication.
        """

        # read config file
        project_path = os.path.dirname(os.path.realpath(__file__))
        config = configparser.ConfigParser()
        config.read(os.path.join(project_path, "config", "config.ini"))
        consumer_key = config.get("access", "consumer_key")
        consumer_secret = config.get("access", "consumer_secret")
        access_token = config.get("access", "access_token")
        access_token_secret = config.get("access", "access_token_secret")

        # twitter authentification
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth)

    def post_tweet():
        """
        Post tweet of newly acquired Sentinel-2 coastal image.
        """

        api.update_status(status="Not implemented yet")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--user", help="Copernicus user")
    parser.add_argument("-p", "--password", help="Copernicus password")
    parser.add_argument("-a", "--aoi", help="Area of interest geojson file")
    args = parser.parse_args()

    tci_file_path = download_tci_image(args.user, args.password, args.aoi)

    # s2coastalbot = S2CoastalBot()
    #
    # s2coastalbot.authenticate()
    #
    # s2coastalbot.post_tweet()
