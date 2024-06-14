"""
s2coastalbot main script.
Bot that posts newly acquired Sentinel-2 images of coastal areas, on Twitter and on Mastodon.
"""

# standard library
import configparser
import shutil
from pathlib import Path

# third party
import tweepy
from mastodon import Mastodon

# current project
from s2coastalbot.custom_logger import get_custom_logger
from s2coastalbot.geoutils import format_lon_lat
from s2coastalbot.geoutils import get_location_name
from s2coastalbot.postprocessing import postprocess_tci_image
from s2coastalbot.sentinel2 import download_tci_image


def main():

    project_path = Path(__file__).parents[1]

    # create logger
    log_file = project_path / "logs" / "s2coastalbot.log"
    logger = get_custom_logger(log_file)

    # read config
    logger.info("Reading config")
    config_file = project_path / "config" / "config.ini"
    config = configparser.ConfigParser()
    config.read(config_file)
    cleaning = config.getboolean("misc", "cleaning")

    postprocessed_file_path = None
    while postprocessed_file_path is None:

        # download Sentinel-2 True Color Image
        logger.info("Downloading Sentinel-2 TCI image")
        tci_file_path, date = download_tci_image(
            config,
            logger=logger,
        )

        try:
            # postprocess image to fit twitter or mastodon contraints
            logger.info("Postprocessing image")
            aoi_file_postprocessing = Path(config.get("misc", "aoi_file_postprocessing"))
            postprocessed_file_path, subset_center_coords = postprocess_tci_image(
                tci_file_path, aoi_file_postprocessing, logger
            )
            location_name = get_location_name(subset_center_coords)
            text = "{} ({}) {}".format(
                location_name,
                format_lon_lat(subset_center_coords),
                date.strftime("%Y %b %d"),
            )
        except StopIteration:
            if cleaning:
                logger.info("Cleaning data")
                product_path = tci_file_path.parents[4]
                shutil.rmtree(product_path)

        except Exception as error_msg:
            logger.error(f"Error postprocessing image: {error_msg}")
            if cleaning:
                logger.info("Cleaning data")
                product_path = tci_file_path.parents[4]
                shutil.rmtree(product_path)

    try:
        # authenticate to Mastodon API
        logger.info("Authenticating to Mastodon API")
        mastodon_email = config.get("access", "mastodon_login_email")
        mastodon_password = config.get("access", "mastodon_password")
        mastodon_client_id = config.get("access", "mastodon_client_id")
        mastodon_client_secret = config.get("access", "mastodon_client_secret")
        mastodon_base_url = config.get("access", "mastodon_base_url")
        mastodon_secret_file = config.get("access", "mastodon_secret_file")
        mastodon = Mastodon(
            client_id=mastodon_client_id,
            client_secret=mastodon_client_secret,
            api_base_url=mastodon_base_url,
        )
        mastodon.log_in(
            mastodon_email,
            mastodon_password,
            to_file=mastodon_secret_file,
        )
    except Exception as error_msg:
        logger.error(f"Error authenticating to Mastodon API: {error_msg}")
        if cleaning:
            logger.info("Cleaning data")
            product_path = tci_file_path.parents[4]
            shutil.rmtree(product_path)
        return

    try:
        # post toot
        logger.info("Posting toot")
        media_dict = mastodon.media_post(
            media_file=postprocessed_file_path,
            description="Snapshot of a satellite image of a coastal area.",
        )
        mastodon.status_post(
            status=text,
            media_ids=[media_dict["id"]],
            visibility="public",
        )
    except Exception as error_msg:
        logger.error(f"Error posting toot: {error_msg}")
        if cleaning:
            logger.info("Cleaning data")
            product_path = tci_file_path.parents[4]
            shutil.rmtree(product_path)
        return

    try:
        # authenticate twitter account
        logger.info("Authenticating to twitter API")
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
    except Exception as error_msg:
        logger.error(f"Error authenticating to twitter API: {error_msg}")
        if cleaning:
            logger.info("Cleaning data")
            product_path = tci_file_path.parents[4]
            shutil.rmtree(product_path)
        return

    try:
        # post tweet
        logger.info("Posting tweet")
        media = apiv1.media_upload(filename=postprocessed_file_path)
        apiv2.create_tweet(text=text, media_ids=[media.media_id], user_auth=True)
    except Exception as error_msg:
        logger.error(f"Error posting tweet: {error_msg}")
        if cleaning:
            logger.info("Cleaning data")
            product_path = tci_file_path.parents[4]
            shutil.rmtree(product_path)
        return

    # clean data if necessary
    if cleaning:
        logger.info("Cleaning data")
        product_path = tci_file_path.parents[4]
        shutil.rmtree(product_path)
    return


if __name__ == "__main__":
    main()
