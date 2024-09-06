"""Test functions in geoutils module."""

# standard library
import json
import random
from unittest import mock

# current project
from s2coastalbot.geoutils import format_lon_lat
from s2coastalbot.geoutils import get_location_name


def test_format_lon_lat():
    lon, lat = 0.1, 45.6
    text = format_lon_lat((lon, lat))
    assert text == "45.6°N 0.1°E"
    lon, lat = -0.1, 45.6
    text = format_lon_lat((lon, lat))
    assert text == "45.6°N 0.1°W"


def test_get_location_name():
    """Location name "happy" test where a mocked nominatim returns location name on first try."""

    # Generate test data
    lon = random.uniform(-180, 180)
    lat = random.uniform(-90, 90)

    # Mock nominatim request and try to get location name
    mock_response = mock.MagicMock()
    mock_response.text = json.dumps({"display_name": "test location name"})
    mock_nominatim = mock.MagicMock(return_value=mock_response)
    with mock.patch("s2coastalbot.geoutils.requests.get", mock_nominatim):
        location_name = get_location_name((lon, lat))

    # Assert that URL was called with correct parameters and returns mocked location name
    mock_nominatim.assert_called_once_with(
        f"http://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&addressdetails=0&format=json&zoom=6&extratags=0",
        headers={
            "Accept-Language": "en-US,en;q=0.8",
            "Referer": "https://thibautvoirand.com/s2coastalbot",
        },
    )
    assert location_name == "test location name"


def test_get_location_name_with_error():
    """Location name test where a mocked nominatim first returns an error, then returns a name."""

    # Use `side_effect` to return error for a specific location and success for any other location
    error_response = mock.MagicMock()
    error_response.text = json.dumps({"error": "location not found"})
    valid_response = mock.MagicMock()
    valid_response.text = json.dumps({"display_name": "test location name"})
    known_error_location = (0.0, 0.0)

    def mock_get(url, headers=None):
        if f"lat={known_error_location[0]:.1f}&lon={known_error_location[1]:.1f}" in url:
            return error_response
        return valid_response

    # Mock nominatim request and try to get location name
    with mock.patch("s2coastalbot.geoutils.requests.get", side_effect=mock_get) as mock_nominatim:
        location_name = get_location_name(known_error_location)

    # Assert that nomination was called as expected
    calls = mock_nominatim.call_args_list
    assert len(calls) >= 2
    first_call_args, _ = calls[0]
    assert "lat=0.0&lon=0.0" in first_call_args[0]
    second_call_args, _ = calls[1]
    assert "lat=0.0&lon=0.0" not in second_call_args[0]

    # Assert that the final returned location name is the valid one
    assert location_name == "test location name"
