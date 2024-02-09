"""
Sentinel-2 data handling module for s2coastalbot.
"""

# standard library
import datetime
import os
import random
import shutil
import sys
import xml.etree.ElementTree as ET
from time import sleep

# third party
import fiona
import pandas as pd
from sentinelsat import SentinelAPI
from sentinelsat import SentinelProductsAPI
from sentinelsat import make_path_filter
from shapely.geometry import MultiPoint

# current project
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
    """Read nodata pixels percentage in L2A product.
    Input:
        -product_series     pd.Series
        -output_folder      str
        -products_api       SentinelProductsAPI
        -logger             logging.Logger
    Output:
        -                   float or None
    """

    # download L2A product metadata file
    nodefilter = make_path_filter("*MTD_MSIL2A.xml")
    product_info = sentinelsat_retry_download(
        products_api,
        product_series["uuid"],
        output_folder,
        nodefilter,
        logger,
    )

    if product_info is None:
        return None
    else:
        # read metadata file to check nodata pixels percentage
        l2a_safe_path = os.path.join(output_folder, product_series["filename"])
        l2a_mtd_file = find_mtd_file(l2a_safe_path)
        return read_nodata_pixel_percentage(l2a_mtd_file)


def sentinelsat_retry_download(api, uuid, output_folder, nodefilter, logger):
    """Download product with sentinelsat api with retry and backoff.
    Input:
        -api            SentinelAPI or SentinelProductsAPI
        -uuid           str
        -output_folder  str
        -nodefilter     nodefilter function
        -logger         logging.Logger
    Output:
        -               dict or None
    """

    # initiate sleep time
    sleep_time = 2

    # limit to 9 tries
    for retry_nb in range(9):

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
    logger.error("Backing off sentinelsat download after 10 failures")
    return None


def download_tci_image(config, output_folder=None, logger=None):
    """
    Download a random recently acquired Sentinel-2 image.
    Input:
        -config                 configparser.ConfigParser
            contains:
                access: copernicus_user, copernicus_password
                misc: aoi_file_downloading, cleaning
        -output_folder          str or None
        -logger                 logging.Logger or None
    Output:
        -tci_file_path          str
        -                       datetime.datetime
    """

    # read config
    copernicus_user = config.get("access", "copernicus_user")
    copernicus_password = config.get("access", "copernicus_password")
    aoi_file = config.get("misc", "aoi_file_downloading")
    cleaning = config.get("misc", "cleaning")
    cloud_cover_max = config.get("search", "cloud_cover_max")
    timerange = config.get("search", "timerange")

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
    api = SentinelAPI(copernicus_user, copernicus_password, api_url="https://colhub.met.no")
    products_api = SentinelProductsAPI(
        copernicus_user, copernicus_password, api_url="https://colhub.met.no"
    )

    # read list of already downloaded images
    downloaded_images_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
        "data",
        "downloaded_images.csv",
    )
    if not os.path.exists(downloaded_images_file):  # initiate file if necessary
        downloaded_images = pd.DataFrame(columns=["date", "product"])
    else:
        downloaded_images = pd.read_csv(downloaded_images_file)

    # read footprint
    footprint = []
    with fiona.open(aoi_file, "r") as infile:
        for feat in infile:
            footprint.append(feat["geometry"]["coordinates"])
    random.shuffle(footprint)

    # search for suitable product
    count = 0
    found_suitable_product = False
    while not found_suitable_product and count + 1 < len(footprint) / 50:

        # use 50 tiles sliding window to query products on all footprint
        footprint_subset = footprint[count * 50 : (count + 1) * 50]  # noqa E203
        count += 1

        # search images
        logger.info("Querying Sentinel-2 products")
        products_df = api.to_dataframe(
            api.query(
                MultiPoint(footprint_subset).wkt,
                date=("NOW-{}DAY".format(timerange), "NOW"),
                platformname="Sentinel-2",
                producttype="S2MSI2A",
                area_relation="IsWithin",
                cloudcoverpercentage=(0, cloud_cover_max),
            )
        )

        # select a product that is fully covered (no nodata pixels)
        for i, product_row in [
            (i, p)
            for (i, p) in products_df.iterrows()
            if not p["title"] in downloaded_images["product"].to_list()
        ]:

            logger.info("Checking nodata for product: {}".format(product_row["title"]))

            # check if product contains nodata pixels (which probably means it's on edge of swath)
            nodata_pixel_percentage = read_nodata_from_l2a_prod(
                product_row,
                output_folder,
                products_api,
                logger,
            )
            if nodata_pixel_percentage != 0.0 or nodata_pixel_percentage is None:
                logger.info("Tile contains nodata or metadata download failure")
                if cleaning:
                    shutil.rmtree(os.path.join(output_folder, product_row["filename"]))
            else:
                logger.info("Tile is fully covered (0% nodata pixels)")
                found_suitable_product = True
                break

    if not found_suitable_product:  # case where while loop above didn't generate suitable product
        logger.error("No suitable product found in any tile within the footprint")
        sys.exit(128)

    # download only TCI band
    nodefilter = make_path_filter("*_TCI_10m.jp2")
    product_info = sentinelsat_retry_download(
        products_api, product_row["uuid"], output_folder, nodefilter, logger
    )

    if product_info is None:
        logger.error("Failed sentinelsat download stopped processing")
        sys.exit(128)

    else:

        # update list of downloaded images
        downloaded_images.loc[len(downloaded_images)] = [
            datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            product_row["title"],
        ]
        downloaded_images.to_csv(downloaded_images_file, index=False)

        # find tci file path
        safe_path = os.path.join(output_folder, product_row["filename"])
        tci_file_path = find_tci_file(safe_path)

        return tci_file_path, product_info["date"]
