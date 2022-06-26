"""
Script to find centroids of S2 tiles intersected by world coastline.
"""

# standard imports
import argparse

# third party imports
import fiona
from shapely.geometry import LineString
from shapely.geometry import MultiLineString
from shapely.geometry import Polygon
from tqdm import tqdm
import geojson

# current project imports
from s2coastalbot.custom_logger import get_custom_logger


def find_tiles_centroids(tiles_shp, coastline_shp, output_file, log_file=None):
    """Find centroids of S2 tiles intersected by world coastline.

    Parameters
    ----------
    tiles_shp : str
    coastline_shp : str
    output_shp : str
    log_file : str or None
    """

    # create logger
    if log_file is not None:
        logger = get_custom_logger(log_file)

    # initiate output shape
    output_shape = {"type": "FeatureCollection", "features": []}

    # read world coastline shp as multiline
    lines = []
    with fiona.open(coastline_shp, "r") as infile:
        for feat in infile:
            lines.append(LineString(feat["geometry"]["coordinates"]))
    coastline = MultiLineString(lines)

    # loop through s2 tiles
    with fiona.open(tiles_shp, "r") as infile:
        for i, feat in enumerate(infile):
            if log_file is not None:
                logger.info("Processing tile {} of {}".format(i + 1, len(infile)))
            tile_name = feat["properties"]["Name"]
            tile_polygon = Polygon(feat["geometry"]["coordinates"][0])

            # check if intersects coastline
            if tile_polygon.intersects(coastline):

                # add centroid to output shape
                output_shape["features"].append(
                    {
                        "type": "Feature",
                        "properties": {"name": tile_name},
                        "geometry": {
                            "type": "Point",
                            "coordinates": tile_polygon.centroid.coords[:][0],
                        },
                    }
                )

    # write output shapefile
    with open(output_file, "w") as outfile:
        geojson.dump(output_shape, outfile)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tiles_shp", required=True)
    parser.add_argument("-c", "--coastline_shp", required=True)
    parser.add_argument("-o", "--output_shp", required=True)
    parser.add_argument("-l", "--log_file")
    args = parser.parse_args()

    find_tiles_centroids(args.tiles_shp, args.coastline_shp, args.output_shp, args.log_file)
