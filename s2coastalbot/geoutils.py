"""
Geoutils module for s2coastalbot project.
"""

# standard imports
import json
import requests


def format_lon_lat(coords):
    """
    Convert latitude and longitude into an address using OSM
    Input:
        -coords     (float, float)
            lon, lat
    Output:
        -s          str
    """
    lon, lat = coords
    s = ""
    if lat < 0:
        s += "%.1f°S" % abs(lat)
    else:
        s += "%.1f°N" % abs(lat)

    s += " "

    if lon < 0:
        s += "%.1f°W" % abs(lon)
    else:
        s += "%.1f°E" % abs(lon)

    return s


def get_location_name(coords):
    """
    Convert latitude and longitude into an address using OSM
    Input:
        -coords     (float, float)
            lon, lat
    Output:
        -           str
    """

    headers = {"Accept-Language": "en-US,en;q=0.8"}
    url = "http://nominatim.openstreetmap.org/reverse?lat={}&lon={}&".format(
        coords[1], coords[0]
    )
    url += "addressdetails=0&format=json&zoom=6&extratags=0"

    response = json.loads(requests.get(url, headers=headers).text)

    if "error" in response:
        return "Unknown location"

    return response["display_name"]
