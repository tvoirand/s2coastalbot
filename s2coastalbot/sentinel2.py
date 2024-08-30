"""
Sentinel-2 data handling module for s2coastalbot.
"""

# standard library
import datetime
import logging
from pathlib import Path

# third party
import geopandas as gpd
import pandas as pd
from cdsetool.query import query_features
from shapely.geometry import MultiPoint

# current project
from s2coastalbot.cdse import odata_download_with_nodefilter


def download_tci_image(config, output_folder=None):
    """
    Download a random recently acquired Sentinel-2 image.
    Input:
        -config                 configparser.ConfigParser
            contains:
                access: cdse_user, cdse_password
                misc: aoi_file_downloading, cleaning
        -output_folder          Path or None
    Output:
        -tci_file_path          Path
        -                       datetime.datetime
    """
    logger = logging.getLogger()

    project_path = Path(__file__).parents[1]

    # read config
    cdse_user = config.get("access", "cdse_user")
    cdse_password = config.get("access", "cdse_password")
    aoi_file = Path(config.get("misc", "aoi_file_downloading"))
    cloud_cover_max = config.getint("search", "cloud_cover_max")
    timerange = config.getint("search", "timerange")

    # create output folder if necessary
    if output_folder is None:
        output_folder = project_path / "data"
    output_folder.mkdir(exist_ok=True, parents=True)

    # read list of already downloaded images
    downloaded_images_file = project_path / "data" / "downloaded_images.csv"
    if not downloaded_images_file.exists():  # initiate file if necessary
        downloaded_images = pd.DataFrame(columns=["date", "product"])
    else:
        downloaded_images = pd.read_csv(downloaded_images_file)

    # read and shuffle S2 tiles centroids
    footprint_df = gpd.read_file(aoi_file)
    footprint_df = footprint_df.sample(frac=1).reset_index(drop=True)

    # search for suitable product
    count = 0
    found_suitable_product = False
    while not found_suitable_product and count + 1 < len(footprint_df) / 50:

        # use 50 tiles sliding window to query products on all footprint
        footprint_subset = footprint_df[count * 50 : (count + 1) * 50]  # noqa E203
        count += 1

        # search images
        logger.info("Querying Sentinel-2 products")
        features = query_features(
            "Sentinel2",
            {
                "startDate": datetime.datetime.now() - datetime.timedelta(days=timerange),
                "completionDate": datetime.datetime.now(),
                "productType": "S2MSI2A",
                "geometry": MultiPoint(footprint_subset["geometry"]),
                "cloudCover": f"[0,{cloud_cover_max}]",
            },
        )

        # filter out images that were already processed
        features = filter(
            lambda f: f["properties"]["title"][:-5] not in downloaded_images["product"].to_list(),
            features,
        )

        features = list(features)
        if len(features) > 0:
            # arbitrarily select first product that satisfies criteria
            feature = features[0]
            found_suitable_product = True

    if not found_suitable_product:  # case where while loop above didn't generate suitable product
        raise Exception("No suitable product found in any tile within the footprint")

    # download only TCI band
    feature_id = odata_download_with_nodefilter(
        feature["id"],
        output_folder / feature["properties"]["title"],
        cdse_user,
        cdse_password,
        "*_TCI_10m.jp2",
    )

    if feature_id is None:
        raise Exception("Failed Sentinel-2 image download")

    else:

        # update list of downloaded images
        downloaded_images.loc[len(downloaded_images)] = [
            datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            feature["properties"]["title"][:-5],
        ]
        downloaded_images.to_csv(downloaded_images_file, index=False)

        # find tci file path
        safe_path = output_folder / feature["properties"]["title"]
        tci_file_path = next(safe_path.rglob("*_TCI_10m.jp2"))

        return tci_file_path, datetime.datetime.fromisoformat(
            feature["properties"]["completionDate"]
        )
