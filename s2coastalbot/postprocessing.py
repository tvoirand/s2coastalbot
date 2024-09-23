"""Image postprocessing module for s2coastalbot."""

# standard library
import logging
import random

# third party
import geopandas as gpd
import numpy as np
import pyproj
import rasterio
from rasterio.windows import Window
from shapely.geometry import LineString
from shapely.geometry import MultiLineString
from shapely.geometry import Point
from shapely.geometry import Polygon

# create some constants
INPUT_MAX_SIZE = 10980
SUBSET_SIZE = 1000


def get_window(window_center, window_width, window_height, image_width, image_height):
    """Find pixels window around a given center taking into account image bounds.

    The window width and height are fixed, and its center might be shifted if the desired window
    surpasses image bounds.

    Args:
        window_center (int, int): Pixel coordinates (row, col) for the desired center
        window_width (int)
        window_height (int)
        image_width (int)
        image_height (int)
    """
    row_start = window_center[0] - int(window_height / 2)
    row_stop = window_center[0] + int(window_height / 2)
    col_start = window_center[1] - int(window_width / 2)
    col_stop = window_center[1] + int(window_width / 2)
    if row_start < 0:
        row_stop += -row_start
        row_start += -row_start
    if row_stop > image_height:
        row_start -= row_stop - image_height
        row_stop -= row_stop - image_height
    if col_start < 0:
        col_stop += -col_start
        col_start += -col_start
    if col_stop > image_width:
        col_start -= col_stop - image_width
        col_stop -= col_stop - image_width
    return row_start, row_stop, col_start, col_stop


def postprocess_tci_image(input_file, aoi_file):
    """Postprocess TCI image for s2coastalbot.

    Args:
        input_file (Path)
        aoi_file (Path): Geojson file containing polyline shapes

    Returns:
        output_file (Path)
        center_coords (float, float): lon, lat
    """

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
        intersection = footprint.intersection(gdf["geometry"])
        coastline_subsets = []
        for geom in intersection:
            if isinstance(geom, LineString):
                coastline_subsets.append(geom)
            elif isinstance(geom, MultiLineString):
                coastline_subsets.extend(geom.geoms)
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

            # look for nodata pixels, if there are none, select this subset and continue
            logger.debug("Checking nodata pixels ratio")
            nonzero_array = np.count_nonzero(array, axis=0)  # array of non-zero count along bands
            nodata_array = nonzero_array == 0  # array of bool with True for nodata pixels
            nodata_count = np.count_nonzero(nodata_array)  # amount of nodata pixels in array
            if nodata_count == 0:
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

        logger.info("Couldn't find subset without nodata in this image")
        return None, None
