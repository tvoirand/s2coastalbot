"""
Image postprocessing module for s2coastalbot.
"""

# standard imports
import os
import random

# third party imports
import rasterio
from rasterio.windows import Window
import numpy as np
import fiona
from shapely.geometry import LineString, Polygon
import pyproj


# create some constants
INPUT_MAX_SIZE = 10980
SUBSET_WIDTH = 1000
SUBSET_HEIGHT = 1000


def postprocess_tci_image(input_file, aoi_file):
    """
    Postprocess TCI image for s2coastalbot.
    Input:
        -input_file     str
        -aoi_file       str
            Geojson file containing polyline shapes
    Output:
        -               str
            path to output file
    """

    def get_window(center, subset_width, subset_height, max_width, max_height):
        """Find pixels window around target center taking into account image bounds."""
        row_start = center[0] - int(subset_height / 2)
        row_stop = center[0] + int(subset_height / 2)
        col_start = center[1] - int(subset_width / 2)
        col_stop = center[1] + int(subset_width / 2)
        if row_start < 0:
            row_start += -row_start
            row_stop += -row_start
        if row_stop > max_height:
            row_start -= row_stop - max_height
            row_stop -= row_stop - max_height
        if col_start < 0:
            col_start += -col_start
            col_stop += -col_start
        if col_stop > max_width:
            col_start -= col_stop - max_width
            col_stop -= col_stop - max_width
        return row_start, row_stop, col_start, col_stop

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
        coastline_subsets = []
        with fiona.open(aoi_file, "r") as infile:
            for feat in infile:
                line = LineString(feat["geometry"]["coordinates"])
                if line.intersects(footprint):
                    coastline_subsets.append(line.intersection(footprint))
        center_coords = random.choice(random.choice(coastline_subsets).coords)

        # find subset center pixel
        latlon_to_utm = pyproj.Transformer.from_crs(4326, in_dataset.crs.to_epsg())
        center_coords = latlon_to_utm.transform(center_coords[1], center_coords[0])
        center_pixel = rasterio.transform.rowcol(
            in_dataset.transform, center_coords[0], center_coords[1]
        )

        # find subset window
        row_start, row_stop, col_start, col_stop = get_window(
            center_pixel, SUBSET_WIDTH, SUBSET_HEIGHT, INPUT_MAX_SIZE, INPUT_MAX_SIZE
        )
        window = Window.from_slices((row_start, row_stop), (col_start, col_stop))

        # read subset of TCI image
        array = in_dataset.read(window=window)

        # write subset to output file
        with rasterio.open(
            output_file,
            "w",
            driver="PNG",
            count=in_dataset.count,
            height=SUBSET_HEIGHT,
            width=SUBSET_WIDTH,
            dtype=np.uint8,
            transform=in_dataset.window_transform(window),
            crs=in_dataset.crs,
        ) as out_dataset:
            out_dataset.write(array)

    return output_file
