"""
Image postprocessing module for s2coastalbot.
"""

# standard library
import logging
import random

# third party
import geopandas as gpd
import numpy as np
import pyproj
import rasterio
from rasterio.windows import Window
from shapely.geometry import Point
from shapely.geometry import Polygon

# create some constants
INPUT_MAX_SIZE = 10980
SUBSET_SIZE = 1000


def postprocess_tci_image(input_file, aoi_file):
    """
    Postprocess TCI image for s2coastalbot.
    Input:
        -input_file     Path
        -aoi_file       Path
            Geojson file containing polyline shapes
    Output:
        -output_file    Path
        -center_coords  (float, float)
            lon, lat
    """

    def get_window(center, subset_width, subset_height, max_width, max_height):
        """Find pixels window around target center taking into account image bounds."""
        row_start = center[0] - int(subset_height / 2)
        row_stop = center[0] + int(subset_height / 2)
        col_start = center[1] - int(subset_width / 2)
        col_stop = center[1] + int(subset_width / 2)
        if row_start < 0:
            row_stop += -row_start
            row_start += -row_start
        if row_stop > max_height:
            row_start -= row_stop - max_height
            row_stop -= row_stop - max_height
        if col_start < 0:
            col_stop += -col_start
            col_start += -col_start
        if col_stop > max_width:
            col_start -= col_stop - max_width
            col_stop -= col_stop - max_width
        return row_start, row_stop, col_start, col_stop

    def translate(value, in_min, in_max, out_min, out_max):
        """Map value from one range to another"""
        # compute ranges spans
        in_span = in_max - in_min
        out_span = out_max - out_min

        # translate input range to a 0-1 range
        value_scaled = (value - in_min) / in_span

        # translate 0-1 range into output range
        return out_min + (value_scaled * out_span)

    logger = logging.getLogger()

    # create some constants
    output_file = input_file.parent / f"{input_file.stem}_postprocessed.png"

    # open input dataset
    with rasterio.open(input_file) as in_dataset:

        # read TCI image footprint
        footprint = [
            (in_dataset.bounds.left, in_dataset.bounds.top),
            (in_dataset.bounds.right, in_dataset.bounds.top),
            (in_dataset.bounds.right, in_dataset.bounds.bottom),
            (in_dataset.bounds.left, in_dataset.bounds.bottom),
        ]
        utm_to_latlon = pyproj.Transformer.from_crs(in_dataset.crs.to_epsg(), 4326)
        footprint = [(lon, lat) for (lat, lon) in utm_to_latlon.itransform(footprint)]
        footprint = Polygon(footprint)

        # locate image subset center among intersections with coastline
        logger.info("Locating subset center among intersections with coastline")
        gdf = gpd.read_file(aoi_file)
        coastline_subsets = footprint.intersection(gdf["geometry"])
        coastline_subsets = [line for line in coastline_subsets if not line.is_empty]

        # raise error if there are no intersection with coastline
        if coastline_subsets == []:
            raise Exception("No intersection with coastline found")

        # list up to a hundred of potential subset centers randomly picked along coastline
        coastline_points = [
            Point(coords) for line in coastline_subsets for coords in line.coords[:]
        ]
        random.shuffle(coastline_points)
        coastline_points = coastline_points[:100]

        # loop through potential subset centers, and check if subset contains nodata pixels
        logger.info("Checking for nodata around a set of points along coastline")
        for subset_center in coastline_points:

            # find subset center pixel
            logger.debug("Finding subset center pixel")
            latlon_to_utm = pyproj.Transformer.from_crs(4326, in_dataset.crs.to_epsg())
            center_coords_utm = latlon_to_utm.transform(subset_center.y, subset_center.x)
            center_pixel = rasterio.transform.rowcol(
                in_dataset.transform, center_coords_utm[0], center_coords_utm[1]
            )

            # find subset window
            logger.debug("Finding corresponding subset window")
            row_start, row_stop, col_start, col_stop = get_window(
                center_pixel, SUBSET_SIZE, SUBSET_SIZE, INPUT_MAX_SIZE, INPUT_MAX_SIZE
            )
            window = Window.from_slices((row_start, row_stop), (col_start, col_stop))

            # read subset of TCI image
            logger.debug("Reading subset of TCI image")
            array = in_dataset.read(window=window)

            # check ratio of nodata pixels, if it's inferior to 5%, select this subset and continue
            logger.debug("Checking nodata pixels ratio")
            non_zero_array = np.count_nonzero(array, axis=0)  # array of non-zero count along bands
            non_zero_count = np.count_nonzero(non_zero_array)  # amount of non-zero pixles in array
            nodata_ratio = 1 - non_zero_count / array.shape[1] / array.shape[2]
            if nodata_ratio < 0.05:
                logger.info(
                    "Selected subset center (lon, lat): {:.4f} - {:.4f}".format(
                        subset_center.x, subset_center.y
                    )
                )

                # write subset to output file
                logger.info("Writing subset output file")
                with rasterio.open(
                    output_file,
                    "w",
                    driver="PNG",
                    count=in_dataset.count,
                    height=SUBSET_SIZE,
                    width=SUBSET_SIZE,
                    dtype=np.uint8,
                    transform=in_dataset.window_transform(window),
                    crs=in_dataset.crs,
                ) as out_dataset:
                    out_dataset.write(array)

                return output_file, (subset_center.x, subset_center.y)

        logger.info("Couldn't find subset with <5% nodata in this image")
        return None, None
