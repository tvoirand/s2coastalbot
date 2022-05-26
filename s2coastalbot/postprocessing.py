"""
Image postprocessing module for s2coastalbot.
"""

# standard imports
import os
import sys
import random

# third party imports
import rasterio
from rasterio.windows import Window
import numpy as np
import fiona
from shapely.geometry import LineString
from shapely.geometry import MultiLineString
from shapely.geometry import Polygon
import pyproj

# local project imports
from s2coastalbot.custom_logger import get_custom_logger


# create some constants
INPUT_MAX_SIZE = 10980
SUBSET_SIZE = 1000


def postprocess_tci_image(input_file, aoi_file, logger=None):
    """
    Postprocess TCI image for s2coastalbot.
    Input:
        -input_file     str
        -aoi_file       str
            Geojson file containing polyline shapes
        -logger         logging.Logger or None
    Output:
        -output_file    str
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

    # create logger if necessary
    if logger is None:
        log_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            "logs",
            "s2coastalbot.log",
        )
        logger = get_custom_logger(log_file)

    # create some constants
    output_file = "{}_postprocessed.png".format(os.path.splitext(input_file)[0])

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
        coastline_subsets = []
        with fiona.open(aoi_file, "r") as infile:
            for feat in infile:
                line = LineString(feat["geometry"]["coordinates"])
                if line.intersects(footprint):
                    intersection = line.intersection(footprint)
                    if type(intersection) == LineString:
                        coastline_subsets.append(line.intersection(footprint))
                    elif type(intersection) == MultiLineString:
                        for linestring in intersection:
                            coastline_subsets.append(linestring)

        # raise error if there are no intersection with coastline
        if coastline_subsets == []:
            logger.error("No intersection with coastline found")
            sys.exit(128)

        center_coords = random.choice(random.choice(coastline_subsets).coords)
        logger.info(
            "Subset center (lon, lat): {:.4f} - {:.4f}".format(center_coords[0], center_coords[1])
        )

        # find subset center pixel
        latlon_to_utm = pyproj.Transformer.from_crs(4326, in_dataset.crs.to_epsg())
        center_coords_utm = latlon_to_utm.transform(center_coords[1], center_coords[0])
        center_pixel = rasterio.transform.rowcol(
            in_dataset.transform, center_coords_utm[0], center_coords_utm[1]
        )

        # find subset window
        logger.info("Finding corresponding subset window")
        row_start, row_stop, col_start, col_stop = get_window(
            center_pixel, SUBSET_SIZE, SUBSET_SIZE, INPUT_MAX_SIZE, INPUT_MAX_SIZE
        )
        window = Window.from_slices((row_start, row_stop), (col_start, col_stop))

        # read subset of TCI image
        array = in_dataset.read(window=window)

        # increase brightness
        array = translate(array, 0, 90, 0, 255)
        array[array>255] = 255

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

    return output_file, center_coords
