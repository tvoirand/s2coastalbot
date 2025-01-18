"""
s2coastalbot main script.
Bot that posts newly acquired Sentinel-2 images of coastal areas, on Twitter and on Mastodon.
"""

# standard library
import argparse
import configparser
import datetime
import logging
import shutil
from pathlib import Path

# third party
import pandas as pd
from mastodon import Mastodon

# current project
from s2coastalbot.custom_logger import get_custom_logger
from s2coastalbot.geoutils import format_lon_lat
from s2coastalbot.geoutils import get_location_name
from s2coastalbot.postprocessing import postprocess_tci_image
from s2coastalbot.sentinel2 import download_tci_image


def clean_data_based_on_tci_file(tci_file_path):
    """Remove product's folder based on TCI file path.
    Input:
        - tci_file_path     Path
    """
    logger = logging.getLogger()
    logger.info("Cleaning data")
    product_path = tci_file_path.parent
    shutil.rmtree(product_path)


def s2coastalbot_main(config):
    """
    Input:
        - config    configparser.ConfigParser
            See contents in 'config/example_config.ini'
    """
    logger = logging.getLogger()
    cleaning = config.getboolean("misc", "cleaning")

    postprocessed_file_path = None
    while postprocessed_file_path is None:

        # download Sentinel-2 True Color Image
        logger.info("Downloading Sentinel-2 TCI image")
        tci_file_path, date = download_tci_image(config)

        try:

            # postprocess image to get a smaller subset
            logger.info("Postprocessing image")
            aoi_file_postprocessing = Path(config.get("misc", "aoi_file_postprocessing"))
            postprocessed_file_path, subset_center_coords = postprocess_tci_image(
                tci_file_path, aoi_file_postprocessing
            )

            if postprocessed_file_path is None:
                # no subset found within this image, try downloading another image
                if cleaning:
                    clean_data_based_on_tci_file(tci_file_path)
                continue

            location_name = get_location_name(subset_center_coords)
            text = "{} ({}) {}".format(
                location_name,
                format_lon_lat(subset_center_coords),
                date.strftime("%Y %b %d"),
            )

        except Exception as error_msg:
            logger.error(f"Error postprocessing image: {error_msg}")
            if cleaning:
                clean_data_based_on_tci_file(tci_file_path)

    try:
        # authenticate to Mastodon API
        logger.info("Authenticating to Mastodon API")
        mastodon_secret_file = config.get("access", "mastodon_secret_file")
        mastodon = Mastodon(access_token=mastodon_secret_file)
    except Exception as error_msg:
        logger.error(f"Error authenticating to Mastodon API: {error_msg}")
        if cleaning:
            clean_data_based_on_tci_file(tci_file_path)
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
            clean_data_based_on_tci_file(tci_file_path)
        return

    # update list of posted images
    project_path = Path(__file__).parents[1]
    posted_images_file = project_path / "data" / "posted_images.csv"
    if not posted_images_file.exists():  # initiate file if necessary
        posted_images = pd.DataFrame(columns=["date", "product"])
    else:
        posted_images = pd.read_csv(posted_images_file)
    posted_images.loc[len(posted_images)] = [
        datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        tci_file_path.parent.stem,
    ]
    posted_images.to_csv(posted_images_file, index=False)

    # clean data if necessary
    if cleaning:
        clean_data_based_on_tci_file(tci_file_path)
    return


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-cf",
        "--config_file",
        help="Default: 'config/config.ini' file in project's development folder",
    )
    parser.add_argument(
        "-lf",
        "--log_file",
        help="Default: 'logs/s2coastalbot.log' file in project's development folder",
    )
    args = parser.parse_args()

    project_path = Path(__file__).parents[1]

    # create logger
    log_file = (
        project_path / "logs" / "s2coastalbot.log" if args.log_file is None else Path(args.log_file)
    )
    logger = get_custom_logger(log_file)

    # read config
    logger.info("Reading config")
    config_file = (
        project_path / "config" / "config.ini"
        if args.config_file is None
        else Path(args.config_file)
    )
    config = configparser.ConfigParser()
    config.read(config_file)

    s2coastalbot_main(config)
