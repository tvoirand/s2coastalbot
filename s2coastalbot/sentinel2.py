"""
Sentinel-2 data handling module for s2coastalbot.
"""

# standard imports
import os
import argparse
import configparser
import json
import requests

# third party imports
from sentinelsat import SentinelAPI
from sentinelsat import SentinelProductsAPI
from sentinelsat import make_path_filter
from sentinelsat import read_geojson
from sentinelsat import geojson_to_wkt
import shapely.wkt


def download_tci_image(
    copernicus_user, copernicus_password, aoi_file, output_folder=None
):
    """
    Download a random recently acquired Sentinel-2 image.
    Input:
        -copernicus_user        str
        -copernicus_password    str
        -aoi_file               str
    Output:
        -tci_file_path          str
        -center_coords          (float, float)
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
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "data"
        )
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # download only TCI band
    nodefilter = make_path_filter("*_tci.jp2")
    product_info = products_api.download(
        product_row["uuid"], directory_path=output_folder, nodefilter=nodefilter
    )

    # get center lat lon
    center_coords = shapely.wkt.loads(product_info["footprint"]).centroid.coords[0]

    # find tci file path
    safe_path = os.path.join(output_folder, product_info["node_path"][2:])
    tci_file_path = find_tci_file(safe_path)

    return tci_file_path, center_coords
