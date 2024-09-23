"""Test components of the postprocessing module."""

# standard library
from pathlib import Path
from unittest import mock

# third party
import affine
import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString

# current project
from s2coastalbot.postprocessing import get_window
from s2coastalbot.postprocessing import postprocess_tci_image

# Mock location data corresponding to an area near Nuuk, in format: East, North, West, South
MOCK_BOUNDS_32622 = (451000, 7140000, 479000, 7100000)  # In CRS EPSG:32622
MOCK_BOUNDS_4326 = (-52.02, 64.38, -51.43, 64.03)  # In CRS EPSG:4326


def test_get_window():
    # Define mock image and window size
    max_width = 500
    max_height = 100
    subset_width = 50
    subset_height = 10

    # Check that the correct window is returned based on various input center pixel
    window = get_window((50, 200), subset_width, subset_height, max_width, max_height)
    assert window == (45, 55, 175, 225)
    window = get_window((5, 200), subset_width, subset_height, max_width, max_height)
    assert window == (0, 10, 175, 225)
    window = get_window((50, 485), subset_width, subset_height, max_width, max_height)
    assert window == (45, 55, 450, 500)


@pytest.fixture
def mock_rasterio_open(request):
    """Mocks the behavior of rasterio.open context manager.

    Simulates an image in which all pixels have the same value, which is parametrized.

    Args:
        image_contents (int): Pixels value for the mock image array, obtained through the pytest
            'request' special object.

    Returns:
        mock_open (mock.MagicMock)
    """
    image_contents = request.param

    # Define raster dimensions based on mock bounds
    east_bound, north_bound, west_bound, south_bound = MOCK_BOUNDS_32622
    x_size = 1000.0
    y_size = -1000.0
    width = int((west_bound - east_bound) / x_size)
    height = int((south_bound - north_bound) / y_size)

    # Mocking TCI image raster dataset
    mock_dataset = mock.MagicMock()
    mock_dataset.bounds = mock.MagicMock(
        left=east_bound,
        top=north_bound,
        right=west_bound,
        bottom=south_bound,
    )
    mock_dataset.crs.to_epsg.return_value = 32622
    mock_dataset.transform = affine.Affine(
        x_size, 0.0, float(east_bound), 0.0, y_size, float(north_bound)
    )
    mock_dataset.read.return_value = np.ones((3, width, height)) * image_contents

    mock_open = mock.MagicMock()
    mock_open.return_value.__enter__.return_value = mock_dataset

    return mock_open


@pytest.fixture
def mock_gpd_read_file(request):
    """Mock behavior of gpd.read_file to simulate reading coastline vector file.

    The mock coastline is a horizontal line parametrized to either cross the mock image bounds, or
    lie outside of the mock image bounds.

    Args:
        coastline_within_bounds (bool): If set to True, mock coastline crosses mock image
            bounds, if set to False, mock coastline lies outside of mock image bounds. Obtained
            through the pytest 'request' special object.

    Returns:
        mock_read_file (mock.MagicMock)
    """

    # Define coastline coords based on fixture parameterization
    east_bound, north_bound, west_bound, south_bound = MOCK_BOUNDS_4326
    coastline_within_bounds = request.param
    if coastline_within_bounds:
        coastline_coords = [
            (east_bound, (north_bound + south_bound) / 2),
            (west_bound, (north_bound + south_bound) / 2),
        ]
    else:
        coastline_coords = [
            (east_bound, north_bound + north_bound / 10),
            (west_bound, north_bound + north_bound / 10),
        ]

    # Mock coastline geodataframe
    mock_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries())
    mock_gdf.set_geometry(col="geometry", inplace=True)
    mock_gdf.loc[0] = [LineString(coastline_coords)]
    mock_read_file = mock.MagicMock()
    mock_read_file.return_value = mock_gdf

    return mock_read_file


@pytest.mark.parametrize(
    "mock_rasterio_open, mock_gpd_read_file",
    [(1, True)],
    indirect=["mock_rasterio_open", "mock_gpd_read_file"],
)
def test_postprocess_tci_image(mock_rasterio_open, mock_gpd_read_file):
    """Postprocessing "happy" test where image contains data and coastline within bounds."""

    east_bound, north_bound, west_bound, south_bound = MOCK_BOUNDS_4326

    with mock.patch("s2coastalbot.postprocessing.rasterio.open", mock_rasterio_open), mock.patch(
        "s2coastalbot.postprocessing.gpd.read_file", mock_gpd_read_file
    ):
        output_file, center_coords = postprocess_tci_image(
            Path("tmp/fake/path/input.tif"), Path("tmp/fake/path/aoi.geojson")
        )

        assert output_file == Path("tmp/fake/path/input_postprocessed.png")
        assert east_bound <= center_coords[0] <= west_bound
        assert south_bound <= center_coords[1] <= north_bound


@pytest.mark.parametrize(
    "mock_rasterio_open, mock_gpd_read_file",
    [(0, True)],
    indirect=["mock_rasterio_open", "mock_gpd_read_file"],
)
def test_postprocess_tci_image_only_nodata(mock_rasterio_open, mock_gpd_read_file):
    """Postprocessing "sad" test where image doesn't contains data and coastline outside bounds."""

    with mock.patch("s2coastalbot.postprocessing.rasterio.open", mock_rasterio_open), mock.patch(
        "s2coastalbot.postprocessing.gpd.read_file", mock_gpd_read_file
    ):
        output_file, center_coords = postprocess_tci_image(
            Path("tmp/fake/path/input.tif"), Path("tmp/fake/path/aoi.geojson")
        )
        assert output_file is None
        assert center_coords is None


@pytest.mark.parametrize(
    "mock_rasterio_open, mock_gpd_read_file",
    [(1, False)],
    indirect=["mock_rasterio_open", "mock_gpd_read_file"],
)
def test_postprocess_tci_image_no_intersection(mock_rasterio_open, mock_gpd_read_file):
    """Postprocessing "sad" test where image contains data and coastline outside bounds."""

    with mock.patch("s2coastalbot.postprocessing.rasterio.open", mock_rasterio_open), mock.patch(
        "s2coastalbot.postprocessing.gpd.read_file", mock_gpd_read_file
    ), pytest.raises(Exception, match="No intersection with coastline found"):
        postprocess_tci_image(Path("tmp/fake/path/input.tif"), Path("tmp/fake/path/aoi.geojson"))
