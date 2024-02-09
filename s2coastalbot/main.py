"""
s2coastalbot main script.
Twitter bot that posts newly acquired Sentinel-2 images of coastal areas.
"""

# standard library
import configparser
import os
import shutil

# third party
import tweepy
from mastodon import Mastodon

# current project
from s2coastalbot.custom_logger import get_custom_logger
from s2coastalbot.geoutils import format_lon_lat
from s2coastalbot.geoutils import get_location_name
from s2coastalbot.postprocessing import postprocess_tci_image
from s2coastalbot.sentinel2 import download_tci_image


class S2CoastalBot:
    """
    Class for S2CoastalBot.
    """

    def __init__(self):
        """
        Constructor for the S2CoastalBot class.
        """

        # create logger
        log_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            "logs",
            "s2coastalbot.log",
        )
        logger = get_custom_logger(log_file)

        # read config
        logger.info("Reading config")
        config_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            "config",
            "config.ini",
        )
        config = configparser.ConfigParser()
        config.read(config_file)

        # download Sentinel-2 True Color Image
        logger.info("Downloading Sentinel-2 TCI image")
        tci_file_path, date = download_tci_image(
            config,
            logger=logger,
        )

        # postprocess image to fit twitter contraints
        logger.info("Postprocessing image")
        aoi_file_postprocessing = config.get("misc", "aoi_file_postprocessing")
        postprocessed_file_path, subset_center_coords = postprocess_tci_image(
            tci_file_path, aoi_file_postprocessing, logger
        )
        location_name = get_location_name(subset_center_coords)
        text = "{} ({}) {}".format(
            location_name,
            format_lon_lat(subset_center_coords),
            date.strftime("%Y %b %d"),
        )

        # authenticate against Mastodon API
        logger.info("Authenticating against Mastodon API")
        mastodon_email = config.get("access", "mastodon_login_email")
        mastodon_password = config.get("access", "mastodon_password")
        mastodon_client_id = config.get("access", "mastodon_client_id")
        mastodon_client_secret = config.get("access", "mastodon_client_secret")
        mastodon_base_url = config.get("access", "mastodon_base_url")
        mastodon_secret_file = config.get("access", "mastodon_secret_file")
        mastodon = Mastodon(client_id=mastodon_client_id, client_secret=mastodon_client_secret, api_base_url=mastodon_base_url)
        mastodon.log_in(
            mastodon_email,
            mastodon_password,
            to_file=mastodon_secret_file,
        )

        # post toot
        logger.info("Posting toot")
        media_dict = mastodon.media_post(media_file=postprocessed_file_path)
        mastodon.status_post(
            status=text,
            media_ids=[media_dict["id"]],
            visibility="public",
        )

        # authenticate twitter account
        logger.info("Authenticating against twitter API")
        twitter_key = config.get("access", "twitter_consumer_key")
        twitter_secret = config.get("access", "twitter_consumer_secret")
        twitter_token = config.get("access", "twitter_access_token")
        twitter_token_secret = config.get("access", "twitter_access_token_secret")
        auth = tweepy.OAuthHandler(twitter_key, twitter_secret)
        auth.set_access_token(twitter_token, twitter_token_secret)
        apiv1 = tweepy.API(auth)  # API v1.1 required to upload media
        apiv2 = tweepy.Client(  # API v2 required to post tweets
            consumer_key=twitter_key,
            consumer_secret=twitter_secret,
            access_token=twitter_token,
            access_token_secret=twitter_token_secret,
        )

        # post tweet
        logger.info("Posting tweet")
        media = apiv1.media_upload(filename=postprocessed_file_path)
        apiv2.create_tweet(text=text, media_ids=[media.media_id], user_auth=True)

        # clean data if necessary
        cleaning = config.get("misc", "cleaning").lower() in ["true", "yes", "t", "y"]
        if cleaning:
            logger.info("Cleaning data")
            product_path = os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(postprocessed_file_path)))
                )
            )
            shutil.rmtree(product_path)


if __name__ == "__main__":
    s2coastalbot = S2CoastalBot()
