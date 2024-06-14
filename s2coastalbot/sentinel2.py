"""
Sentinel-2 data handling module for s2coastalbot.
"""

# standard library
import datetime
import random
from pathlib import Path
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


def sentinelsat_retry_download(api, uuid, output_folder, nodefilter, logger):
    """Download product with sentinelsat api with retry and backoff.
    Input:
        -api            SentinelAPI or SentinelProductsAPI
        -uuid           str
        -output_folder  Path
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
            product_info = api.download(
                uuid, directory_path=str(output_folder), nodefilter=nodefilter
            )
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
        -output_folder          Path or None
        -logger                 logging.Logger or None
    Output:
        -tci_file_path          Path
        -                       datetime.datetime
    """
    project_path = Path(__file__).parents[1]

    # read config
    copernicus_user = config.get("access", "copernicus_user")
    copernicus_password = config.get("access", "copernicus_password")
    aoi_file = Path(config.get("misc", "aoi_file_downloading"))
    cloud_cover_max = config.get("search", "cloud_cover_max")
    timerange = config.get("search", "timerange")

    # create logger if necessary
    if logger is None:
        log_file = project_path / "logs" / "s2coastalbot.log"
        logger = get_custom_logger(log_file)

    # create output folder if necessary
    if output_folder is None:
        output_folder = project_path / "data"
    output_folder.mkdir(exist_ok=True, parents=True)

    # connect to APIs
    api = SentinelAPI(copernicus_user, copernicus_password, api_url="https://colhub.met.no")
    products_api = SentinelProductsAPI(
        copernicus_user, copernicus_password, api_url="https://colhub.met.no"
    )

    # read list of already downloaded images
    downloaded_images_file = project_path / "data" / "downloaded_images.csv"
    if not downloaded_images_file.exists():  # initiate file if necessary
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
                MultiPoint(footprint[:50]).wkt,  # arbitrarily query first 50 tiles
                date=("NOW-{}DAY".format(timerange), "NOW"),
                platformname="Sentinel-2",
                producttype="S2MSI2A",
                area_relation="IsWithin",
                cloudcoverpercentage=(0, cloud_cover_max),
            )
        )

        # filter out images that were already processed
        products_df = products_df.loc[
            ~products_df["title"].isin(downloaded_images["product"].to_list())
        ]

        if len(products_df) > 0:
            # arbitrarily select first product that satisfies criteria
            product_row = products_df.iloc[0]
            found_suitable_product = True

    if not found_suitable_product:  # case where while loop above didn't generate suitable product
        raise Exception("No suitable product found in any tile within the footprint")

    # download only TCI band
    nodefilter = make_path_filter("*_TCI_10m.jp2")
    product_info = sentinelsat_retry_download(
        products_api, product_row["uuid"], output_folder, nodefilter, logger
    )

    if product_info is None:
        raise Exception("Failed sentinelsat download")

    else:

        # update list of downloaded images
        downloaded_images.loc[len(downloaded_images)] = [
            datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            product_row["title"],
        ]
        downloaded_images.to_csv(downloaded_images_file, index=False)

        # find tci file path
        safe_path = output_folder / product_row["filename"]
        tci_file_path = next(safe_path.rglob("*_TCI_10m.jp2"))

        return tci_file_path, product_info["date"]
