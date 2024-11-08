"""Tests for the main script of s2coastalbot."""

# standard library
import configparser
import datetime
import tempfile
from pathlib import Path
from unittest import mock

# third party
import pytest
from icecream import ic  # noqa F401

# current project
from s2coastalbot.custom_logger import get_custom_logger
from s2coastalbot.main import s2coastalbot_main


@pytest.fixture
def tmp_dir():
    """Create and provide temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield (Path(temp_dir))


@pytest.fixture
def mock_functions(tmp_dir):
    """Fixture to mock functions called in s2coastalbot_main and used in tests."""
    mock_tci_file = tmp_dir / "mock_product_name" / "mock_image.tif"
    mock_postprocessed_file = tmp_dir / "mock_product_name" / "postprocessed_image.png"
    mock_center_coords = (45.0, -73.0)
    mock_aoi_file = tmp_dir / "mock_aoi_file.geojson"
    mock_download_tci_image = mock.MagicMock(return_value=(mock_tci_file, datetime.datetime.now()))
    mock_postprocess_tci_image = mock.MagicMock(
        return_value=(mock_postprocessed_file, mock_center_coords)
    )
    mock_get_location_name = mock.MagicMock(return_value="mock location name")
    mock_clean_data = mock.MagicMock()

    # Mock Path(__file__) to use tmp_dir instead of project path, were "data" folder lives
    data_dir = tmp_dir / "data"
    data_dir.mkdir(exist_ok=True, parents=True)
    mock_path = mock.MagicMock(return_value=tmp_dir / "mock_subdir" / "mock_file")

    return {
        "mock_path": mock_path,
        "mock_download_tci_image": mock_download_tci_image,
        "mock_postprocess_tci_image": mock_postprocess_tci_image,
        "mock_get_location_name": mock_get_location_name,
        "mock_clean_data": mock_clean_data,
        "mock_tci_file": mock_tci_file,
        "mock_postprocessed_file": mock_postprocessed_file,
        "mock_center_coords": mock_center_coords,
        "mock_aoi_file": mock_aoi_file,
    }


@pytest.fixture
def mock_config(mock_functions):
    """Fixture to create and provide a mock configuration."""
    config = configparser.ConfigParser()
    config["misc"] = {
        "cleaning": True,
        "aoi_file_postprocessing": mock_functions["mock_aoi_file"],
    }
    config["access"] = {
        "mastodon_secret_file": "mock_mastodon_secret_file",
        "twitter_consumer_key": "mock_twitter_consumer_key",
        "twitter_consumer_secret": "mock_twitter_consumer_secret",
        "twitter_access_token": "mock_twitter_access_token",
        "twitter_access_token_secret": "mock_twitter_access_token_secret",
    }
    return config


def test_process_tci_image(tmp_dir, mock_functions, mock_config, caplog):
    """Test successful image processing flow: download, postprocess, get location name."""

    # Call s2coastalbot_main while mocking necessary functions
    with mock.patch(
        "s2coastalbot.main.download_tci_image", mock_functions["mock_download_tci_image"]
    ), mock.patch(
        "s2coastalbot.main.postprocess_tci_image",
        mock_functions["mock_postprocess_tci_image"],
    ), mock.patch(
        "s2coastalbot.main.get_location_name", mock_functions["mock_get_location_name"]
    ), mock.patch(
        "s2coastalbot.main.clean_data_based_on_tci_file", mock_functions["mock_clean_data"]
    ):
        s2coastalbot_main(mock_config)

    # Assert that downloading, postprocessing and cleaning where called as expected
    # Cleaning is expected to be called when Mastodon fails due to missing config
    mock_functions["mock_download_tci_image"].assert_called_once_with(mock_config)
    mock_functions["mock_postprocess_tci_image"].assert_called_once_with(
        mock_functions["mock_tci_file"], mock_functions["mock_aoi_file"]
    )
    mock_functions["mock_get_location_name"].assert_called_once_with(
        mock_functions["mock_center_coords"]
    )
    mock_functions["mock_clean_data"].assert_called_once_with(mock_functions["mock_tci_file"])


def test_mastodon_post(tmp_dir, mock_functions, mock_config):
    """Test posting image to Mastodon."""

    # Mock Mastodon login and media post behavior
    mock_mastodon_instance = mock.MagicMock()
    mock_mastodon_instance.media_post.return_value = {"id": "mock_media_id"}
    mock_mastodon = mock.MagicMock(return_value=mock_mastodon_instance)

    with mock.patch(
        "s2coastalbot.main.download_tci_image", mock_functions["mock_download_tci_image"]
    ), mock.patch(
        "s2coastalbot.main.postprocess_tci_image", mock_functions["mock_postprocess_tci_image"]
    ), mock.patch(
        "s2coastalbot.main.get_location_name", mock_functions["mock_get_location_name"]
    ), mock.patch(
        "s2coastalbot.main.Mastodon", mock_mastodon
    ), mock.patch(
        "s2coastalbot.main.Path", mock_functions["mock_path"]
    ), mock.patch(
        "s2coastalbot.main.clean_data_based_on_tci_file", mock_functions["mock_clean_data"]
    ):
        s2coastalbot_main(mock_config)

    # Assert Mastodon API interaction
    # Cleaning is expected to be called when Twitter fails due to missing config
    mock_mastodon.assert_called_once_with(access_token="mock_mastodon_secret_file")
    mock_mastodon_instance.media_post.assert_called_once_with(
        media_file=mock_functions["mock_postprocessed_file"],
        description="Snapshot of a satellite image of a coastal area.",
    )
    mock_mastodon_instance.status_post.assert_called_once_with(
        status=mock.ANY, media_ids=["mock_media_id"], visibility="public"
    )
    assert "mock location name" in mock_mastodon_instance.status_post.call_args[1]["status"]


def test_twitter_post(tmp_dir, mock_functions, mock_config):
    """Test posting image to Twitter."""

    # Mock Twitter media upload and post behavior
    mock_twitter_api_instance = mock.MagicMock()
    mock_twitter_api_instance.media_upload.return_value.media_id = "mock_media_id"
    mock_twitter_api = mock.MagicMock(return_value=mock_twitter_api_instance)
    mock_twitter_client_instance = mock.MagicMock()
    mock_twitter_client = mock.MagicMock(return_value=mock_twitter_client_instance)

    with mock.patch(
        "s2coastalbot.main.download_tci_image", mock_functions["mock_download_tci_image"]
    ), mock.patch(
        "s2coastalbot.main.postprocess_tci_image", mock_functions["mock_postprocess_tci_image"]
    ), mock.patch(
        "s2coastalbot.main.get_location_name", mock_functions["mock_get_location_name"]
    ), mock.patch(
        "s2coastalbot.main.Mastodon", mock.MagicMock()
    ), mock.patch(
        "s2coastalbot.main.tweepy.API", mock_twitter_api
    ), mock.patch(
        "s2coastalbot.main.tweepy.Client", mock_twitter_client
    ), mock.patch(
        "s2coastalbot.main.Path", mock_functions["mock_path"]
    ), mock.patch(
        "s2coastalbot.main.clean_data_based_on_tci_file", mock_functions["mock_clean_data"]
    ):
        s2coastalbot_main(mock_config)

    # Assert Twitter API interaction
    mock_twitter_api.assert_called_once()
    mock_twitter_api_instance.media_upload.assert_called_once_with(
        filename=mock_functions["mock_postprocessed_file"]
    )
    mock_twitter_client_instance.create_tweet.assert_called_once_with(
        text=mock.ANY, media_ids=["mock_media_id"], user_auth=True
    )


def test_error_in_posting(tmp_dir, mock_functions, mock_config, caplog):
    """Mock error cases for Mastodon posting."""

    # Mock Mastodon login and media post behavior
    mock_mastodon_instance = mock.MagicMock()
    mock_error_msg = "Mock Mastodon error"
    mock_mastodon_instance.media_post.side_effect = Exception(mock_error_msg)
    mock_mastodon = mock.MagicMock(return_value=mock_mastodon_instance)

    # Create logger to capture error log
    logger = get_custom_logger(tmp_dir / "test.log")  # noqa F841

    with mock.patch(
        "s2coastalbot.main.download_tci_image", mock_functions["mock_download_tci_image"]
    ), mock.patch(
        "s2coastalbot.main.postprocess_tci_image", mock_functions["mock_postprocess_tci_image"]
    ), mock.patch(
        "s2coastalbot.main.get_location_name", mock_functions["mock_get_location_name"]
    ), mock.patch(
        "s2coastalbot.main.Mastodon", mock_mastodon
    ), mock.patch(
        "s2coastalbot.main.clean_data_based_on_tci_file", mock_functions["mock_clean_data"]
    ):
        s2coastalbot_main(mock_config)

    assert caplog.text.endswith(f"Error posting toot: {mock_error_msg}\n")
    mock_functions["mock_clean_data"].assert_called_once()


def test_update_posted_images_csv(tmp_dir, mock_functions, mock_config):
    """Ensure that the CSV file is updated correctly when an image is posted."""

    # Mock posted images file
    mock_posted_images_file = tmp_dir / "data" / "posted_images.csv"
    mock_posted_images_file.parent.mkdir(exist_ok=True, parents=True)

    with mock.patch(
        "s2coastalbot.main.download_tci_image", mock_functions["mock_download_tci_image"]
    ), mock.patch(
        "s2coastalbot.main.postprocess_tci_image", mock_functions["mock_postprocess_tci_image"]
    ), mock.patch(
        "s2coastalbot.main.get_location_name", mock_functions["mock_get_location_name"]
    ), mock.patch(
        "s2coastalbot.main.Mastodon", mock.MagicMock()
    ), mock.patch(
        "s2coastalbot.main.tweepy.API", mock.MagicMock()
    ), mock.patch(
        "s2coastalbot.main.tweepy.Client", mock.MagicMock()
    ), mock.patch(
        "s2coastalbot.main.Path", mock_functions["mock_path"]
    ), mock.patch(
        "s2coastalbot.main.clean_data_based_on_tci_file", mock_functions["mock_clean_data"]
    ):
        s2coastalbot_main(mock_config)

    assert mock_posted_images_file.exists()
    with mock_posted_images_file.open() as f:
        assert "mock_product_name" in f.read()
