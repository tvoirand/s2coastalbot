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

    response = json.loads(
        requests.get(url, headers=headers).text
    )

    if "error" in response:
        return "Unknown location, do you recognise it?"

    return response["display_name"]


class S2CoastalBot():
    """
    Class for S2CoastalBot.
    """

    def __init__(self):
        """
        Constructor for the S2CoastalBot class.
        """

        print("not implemented yet")

    def authenticate():
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
    parser.add_argument()
    args = parser.parse_args()

    s2coastalbot = S2CoastalBot()

    s2coastalbot.authenticate()

    s2coastalbot.post_tweet()
