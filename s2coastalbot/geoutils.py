"""Utils functions to handle geolocations."""

# standard library
import json
import time

# third party
import backoff
import requests
from shapely.geometry import Point


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException)
def get_url(url, headers=None):
    return requests.get(url, headers=headers)


def format_lon_lat(coords):
    """Format latitude and longitude into readable text

    Args:
        coords (float, float): lon, lat

    Returns:
        s (str)
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


def get_location_name(input_coords):
    """Convert latitude and longitude into an address using OSM.

    Args:
        input_coords (float, float): lon, lat

    Returns:
        (str)
    """

    # initiate request points, requests count, OSM response, and search circle radius
    points = [input_coords]
    count = 0
    response = "error"
    radius = 0

    # keep requesting while error in response, but limit requests to 1000
    while "error" in response and count < 1000:

        # while location unknown, keep looking in growing circles
        if count % 10 == 1:  # increase circle radius every 10 points

            # create larger circle and pick 10 points on the circle
            radius += 0.1
            circle = Point(input_coords).buffer(radius).exterior.coords
            points += circle[:: len(circle) // 9]

        # get coords where location name is requested from OSM
        coords = points[count]

        # perform request
        headers = {
            "Accept-Language": "en-US,en;q=0.8",
            "Referer": "https://thibautvoirand.com/s2coastalbot",
        }
        url = "http://nominatim.openstreetmap.org/reverse?lat={}&lon={}&".format(
            coords[1], coords[0]
        )
        url += "addressdetails=0&format=json&zoom=6&extratags=0"
        response = get_url(url, headers=headers)
        response = json.loads(response.text)

        count += 1
        time.sleep(1)  # to avoid heavy use of OSM's Nominatim service

    if count >= 1000:
        return "Unknown location"

    return response["display_name"]
