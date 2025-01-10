"""Tests for the sentinel2 module of s2coastalbot."""

# standard library
import configparser
import datetime
import random
import tempfile
from pathlib import Path
from unittest import mock

# third party
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

# current project
from s2coastalbot.sentinel2 import download_tci_image


@pytest.fixture
def tmp_dir():
    """Create and provide temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_tci_file(tmp_dir):
    """Mock a downloaded TCI image file."""
    tci_file = tmp_dir / "data" / "mock_product_001.SAFE" / "mock_image_TCI_10m.jp2"
    tci_file.parent.mkdir(exist_ok=True, parents=True)
    tci_file.touch()
    return tci_file


@pytest.fixture
def mock_config(tmp_dir):
    """Fixture to create a mock config."""
    config = configparser.ConfigParser()
    config["access"] = {"cdse_user": "mock_user", "cdse_password": "mock_password"}
    config["misc"] = {
        "aoi_file_downloading": str(tmp_dir / "mock_aoi_file.geojson"),
        "cleaning": True,
    }
    config["search"] = {"cloud_cover_max": "30", "timerange": "10"}
    return config


@pytest.fixture
def mock_footprint_df(tmp_dir):
    """Fixture to mock GeoDataFrame representing Sentinel-2 tiles."""
    gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries())
    gdf.set_geometry(col="geometry", inplace=True)
    for i in range(101):
        gdf.loc[len(gdf)] = [Point(random.randint(0, 10), random.randint(0, 10))]
    gdf.to_file(tmp_dir / "mock_aoi_file.geojson", driver="GeoJSON")
    return gdf


@pytest.fixture
def mock_downloaded_images(tmp_dir):
    """Fixture to mock downloaded_images.csv file."""
    downloaded_images_file = tmp_dir / "data" / "downloaded_images.csv"
    downloaded_images_file.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=["date", "product"]).to_csv(downloaded_images_file, index=False)
    return downloaded_images_file


def test_successful_tci_download(
    tmp_dir, mock_tci_file, mock_config, mock_footprint_df, mock_downloaded_images
):
    """Test successful TCI image download.."""

    # Mock CDSE query and download
    mock_query_features = mock.MagicMock(
        return_value=[
            {
                "properties": {
                    "title": "mock_product_001.SAFE",
                    "completionDate": "2023-09-01T12:00:00",
                },
                "id": "mock_feature_id",
            }
        ]
    )
    mock_odata_download = mock.MagicMock(return_value="mock_feature_id")

    with mock.patch(
        "s2coastalbot.sentinel2.Path", return_value=tmp_dir / "data" / "mock_subdir"
    ), mock.patch(
        "s2coastalbot.sentinel2.gpd.read_file", return_value=mock_footprint_df
    ), mock.patch(
        "s2coastalbot.sentinel2.query_features", mock_query_features
    ), mock.patch(
        "s2coastalbot.sentinel2.odata_download_with_nodefilter", mock_odata_download
    ):
        tci_file_path, completion_date = download_tci_image(mock_config)

    mock_query_features.assert_called_once()
    assert tci_file_path == mock_tci_file
    assert completion_date == datetime.datetime(2023, 9, 1, 12, 0)
    downloaded_images = pd.read_csv(mock_downloaded_images)
    assert "mock_product_001" in downloaded_images["product"].values


def test_no_suitable_product_found(tmp_dir, mock_config, mock_footprint_df):
    """Test case where no suitable Sentinel-2 product is found."""

    mock_query_features = mock.MagicMock(return_value=[])

    with mock.patch(
        "s2coastalbot.sentinel2.Path", return_value=tmp_dir / "data" / "mock_subdir"
    ), mock.patch(
        "s2coastalbot.sentinel2.gpd.read_file", return_value=mock_footprint_df
    ), mock.patch(
        "s2coastalbot.sentinel2.query_features", mock_query_features
    ):
        with pytest.raises(Exception, match="No suitable product found"):
            download_tci_image(mock_config)


def test_failed_tci_image_download(mock_config, tmp_dir, mock_footprint_df, mock_downloaded_images):
    """Test case where download fails."""

    # Mock CDSE query and download
    mock_query_features = mock.MagicMock(
        return_value=[
            {
                "properties": {
                    "title": "mock_product_001.SAFE",
                    "completionDate": "2023-09-01T12:00:00",
                },
                "id": "mock_feature_id",
            }
        ]
    )
    mock_odata_download = mock.MagicMock(return_value=None)

    with mock.patch(
        "s2coastalbot.sentinel2.Path", return_value=tmp_dir / "data" / "mock_subdir"
    ), mock.patch(
        "s2coastalbot.sentinel2.gpd.read_file", return_value=mock_footprint_df
    ), mock.patch(
        "s2coastalbot.sentinel2.query_features", mock_query_features
    ), mock.patch(
        "s2coastalbot.sentinel2.odata_download_with_nodefilter", mock_odata_download
    ):
        with pytest.raises(Exception, match="Failed Sentinel-2 image download"):
            download_tci_image(mock_config)


def test_skip_already_downloaded_images(
    mock_config, tmp_dir, mock_footprint_df, mock_downloaded_images
):
    """Test that already downloaded images are skipped."""

    # Add a mock product to the downloaded_images.csv file
    downloaded_images = pd.read_csv(mock_downloaded_images)
    downloaded_images.loc[len(downloaded_images)] = ["2023-09-01T12:00:00", "mock_product_001"]
    downloaded_images.to_csv(mock_downloaded_images, index=False)

    # Mock CDSE query with only one result, which listed in downloaded_images.csv
    mock_query_features = mock.MagicMock(
        return_value=[
            {
                "properties": {
                    "title": "mock_product_001.SAFE",
                    "completionDate": "2023-09-01T12:00:00",
                },
                "id": "mock_feature_id",
            }
        ]
    )

    with mock.patch(
        "s2coastalbot.sentinel2.Path", return_value=tmp_dir / "data" / "mock_subdir"
    ), mock.patch(
        "s2coastalbot.sentinel2.gpd.read_file", return_value=mock_footprint_df
    ), mock.patch(
        "s2coastalbot.sentinel2.query_features", mock_query_features
    ):
        # Expect not to find any suitable product
        with pytest.raises(Exception, match="No suitable product found"):
            download_tci_image(mock_config, output_folder=tmp_dir)
