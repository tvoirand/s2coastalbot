"""
Sentinel-2 data handling module for s2coastalbot.
"""

# standard imports
import os
import sys
import argparse
import configparser
import json
import requests
import datetime
import xml.etree.ElementTree as ET
import random
from time import sleep

# third party imports
from sentinelsat import SentinelAPI
from sentinelsat import SentinelProductsAPI
from sentinelsat import make_path_filter
from sentinelsat import read_geojson
from sentinelsat import geojson_to_wkt
import fiona
from shapely.geometry import MultiPoint
import shapely.wkt

# local project imports
from s2coastalbot.geoutils import get_location_name
from s2coastalbot.custom_logger import get_custom_logger


def find_tci_file(product_path):
    """Look for TCI file within S2 L2A product."""
    for path, dirs, files in os.walk(product_path):
        for f in files:
            if f.lower().endswith("_tci_10m.jp2"):
                return os.path.join(path, f)
    return None


def find_mtd_file(product_path):
    """Look for MTD file within S2 L2A product."""
    for path, dirs, files in os.walk(product_path):
        for f in files:
            if f.lower().endswith("mtd_msil2a.xml"):
                return os.path.join(path, f)
    return None


def read_nodata_pixel_percentage(mtd_file):
    """Read nodata pixel percentage from L2A product metadata file."""
    tree = ET.parse(mtd_file)
    root = tree.getroot()
    quality_indicators_info = root.find(
        "{https://psd-14.sentinel2.eo.esa.int/PSD/User_Product_Level-2A.xsd}Quality_Indicators_Info"
    )
    image_content_qi = quality_indicators_info.find("Image_Content_QI")
    nodata_pixel_percentage = float(image_content_qi.find("NODATA_PIXEL_PERCENTAGE").text)
    return nodata_pixel_percentage


def read_nodata_from_l2a_prod(product_series, output_folder, products_api, logger):
    """Read nodata pixels percentage in L2A product."""

    # download L2A product metadata file
    nodefilter = make_path_filter("*mtd_msil2a.xml")
    sentinelsat_retry_download(
        products_api,
        product_series["uuid"],
        output_folder,
        nodefilter,
        logger,
    )

    # read metadata file to check nodata pixels percentage
    l2a_safe_path = os.path.join(output_folder, product_series["filename"])
    l2a_mtd_file = find_mtd_file(l2a_safe_path)
    return read_nodata_pixel_percentage(l2a_mtd_file)


def sentinelsat_retry_download(api, uuid, output_folder, nodefilter, logger):
    """Download product with sentinelsat api with retry and backoff."""

    # initiate sleep time
    sleep_time = 2

    # limit to 5 tries
    for retry_nb in range(10):

        try:
            product_info = api.download(uuid, directory_path=output_folder, nodefilter=nodefilter)
            error_str = None

        except Exception as error:
            error_str = error
            logger.error(
                "Failed sentinelsat download after {} retries, waiting {} seconds".format(
                    retry_nb, sleep_time
                )
            )
            logger.error(error_str)
            pass

        # wait for some given time and increase time at each retry
        if error_str:
            sleep(sleep_time)
            sleep_time *= 2

        # leave retry loop in case of success
        else:
            return product_info

    # report failure after too many retries
    logger.error("Failed sentinelsat download stopped processing")
    sys.exit(128)


def download_tci_image(
    copernicus_user, copernicus_password, aoi_file, output_folder=None, logger=None
):
    """
    Download a random recently acquired Sentinel-2 image.
    Input:
        -copernicus_user        str
        -copernicus_password    str
        -aoi_file               str
        -output_folder          str or None
        -logger                 logging.Logger or None
    Output:
        -tci_file_path          str
        -                       datetime.datetime
    """

    # create logger if necessary
    if logger is None:
        log_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            "logs",
            "s2coastalbot.log",
        )
        logger = get_custom_logger(log_file)

    # create output folder if necessary
    if output_folder is None:
        output_folder = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "data"
        )
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # connect to APIs
    api = SentinelAPI(copernicus_user, copernicus_password)
    products_api = SentinelProductsAPI(copernicus_user, copernicus_password)

    # read footprint
    footprint = []
    with fiona.open(aoi_file, "r") as infile:
        for feat in infile:
            footprint.append(feat["geometry"]["coordinates"])
    random.shuffle(footprint)
    footprint = MultiPoint(footprint[:50]).wkt  # select only 50 tiles to limit search string length

    # search images
    logger.info("Initial Sentinel-2 products query")
    products_df = api.to_dataframe(
        api.query(
            footprint,
            date=("NOW-10DAY", "NOW"),
            platformname="Sentinel-2",
            producttype="S2MSI2A",
            area_relation="IsWithin",
        )
    )

    # filter out products with clouds
    logger.info("Filtering out products with clouds")
    products_df = products_df[products_df["cloudcoverpercentage"] < 0.05]

    # filter out products containing nodata pixels
    tile_is_fully_covered = False
    while not tile_is_fully_covered:

        # select a random product
        product_row = products_df.sample(n=1).iloc[0]
        logger.info("Randomly selected product: {}".format(product_row["title"]))

        # check if product contains nodata pixels (which probably means it's on edge of swath)
        tile_is_fully_covered = False
        nodata_pixel_percentage = read_nodata_from_l2a_prod(
            product_row,
            output_folder,
            products_api,
            logger,
        )
        if nodata_pixel_percentage != 0.0:
            logger.info("Tile contains nodata")
        else:
            logger.info("Tile is fully covered (0% nodata pixels)")
            tile_is_fully_covered = True

    # download only TCI band
    nodefilter = make_path_filter("*_tci_10m.jp2")
    product_info = sentinelsat_retry_download(
        products_api, product_row["uuid"], output_folder, nodefilter, logger
    )

    # find tci file path
    safe_path = os.path.join(output_folder, product_row["filename"])
    tci_file_path = find_tci_file(safe_path)

    return tci_file_path, product_info["date"]
