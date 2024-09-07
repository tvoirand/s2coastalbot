"""Tests for the main script of s2coastalbot."""

# standard library
import configparser
import datetime
import tempfile
from pathlib import Path
from unittest import mock

# third party
from icecream import ic  # noqa F401

# current project
from s2coastalbot.custom_logger import get_custom_logger
from s2coastalbot.main import s2coastalbot_main


def test_process_tci_image(caplog):
    """Test successful image processing flow: download, postprocess, get location name."""

    # Create temporary dir for output files
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        # Mock downloading, postprocessing, get location name and cleaning functions
        mock_tci_file = tmp_dir / "mock_image.tif"
        mock_download_tci_image = mock.MagicMock(
            return_value=(mock_tci_file, datetime.datetime.now())
        )
        mock_postprocessed_file = tmp_dir / "postprocessed_image.png"
        mock_center_coords = (45.0, -73.0)
        mock_postprocess_tci_image = mock.MagicMock(
            return_value=(mock_postprocessed_file, mock_center_coords)
        )
        mock_get_location_name = mock.MagicMock()
        mock_clean_data = mock.MagicMock()

        # Mock config
        mock_aoi_file = tmp_dir / "mock_aoi_file.geojson"
        config = configparser.ConfigParser()
        config["misc"] = {
            "cleaning": True,
            "aoi_file_postprocessing": mock_aoi_file,
        }

        # Call s2coastalbot_main while mocking necessary functions
        with mock.patch(
            "s2coastalbot.main.download_tci_image", mock_download_tci_image
        ), mock.patch(
            "s2coastalbot.main.postprocess_tci_image",
            mock_postprocess_tci_image,
        ), mock.patch(
            "s2coastalbot.main.get_location_name", mock_get_location_name
        ), mock.patch(
            "s2coastalbot.main.clean_data_based_on_tci_file", mock_clean_data
        ):
            s2coastalbot_main(config)

        # Assert that downloading, postprocessing and cleaning where called as expected
        # Cleaning is expected to be called when Mastodon fails due to missing config
        mock_download_tci_image.assert_called_once_with(config)
        mock_postprocess_tci_image.assert_called_once_with(mock_tci_file, mock_aoi_file)
        mock_get_location_name.assert_called_once_with(mock_center_coords)
        mock_clean_data.assert_called_once_with(mock_tci_file)


def test_mastodon_post():
    """Test posting image to Mastodon."""

    # Create temporary dir for output path
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        # Mock image downloading and processing flow
        mock_tci_file = tmp_dir / "mock_image.tif"
        mock_download_tci_image = mock.MagicMock(
            return_value=(mock_tci_file, datetime.datetime.now())
        )
        mock_postprocessed_file = tmp_dir / "postprocessed_image.png"
        mock_center_coords = (45.0, -73.0)
        mock_postprocess_tci_image = mock.MagicMock(
            return_value=(mock_postprocessed_file, mock_center_coords)
        )
        mock_location_name = "mock location name"
        mock_get_location_name = mock.MagicMock(return_value=mock_location_name)
        mock_clean_data = mock.MagicMock()

        # Mock Mastodon login and media post behavior
        mock_mastodon_instance = mock.MagicMock()
        mock_mastodon_instance.media_post.return_value = {"id": "mock_media_id"}
        mock_mastodon = mock.MagicMock(return_value=mock_mastodon_instance)

        config = configparser.ConfigParser()
        config["misc"] = {
            "aoi_file_postprocessing": tmp_dir / "mock_aoi_file.geojson",
            "cleaning": True,
        }
        config["access"] = {
            "mastodon_login_email": "mock_mastodon_login_email",
            "mastodon_password": "mock_mastodon_password",
            "mastodon_client_id": "mock_mastodon_client_id",
            "mastodon_client_secret": "mock_mastodon_client_secret",
            "mastodon_base_url": "mock_mastodon_base_url",
            "mastodon_secret_file": "mock_mastodon_secret_file",
        }

        with mock.patch(
            "s2coastalbot.main.download_tci_image", mock_download_tci_image
        ), mock.patch(
            "s2coastalbot.main.postprocess_tci_image", mock_postprocess_tci_image
        ), mock.patch(
            "s2coastalbot.main.get_location_name", mock_get_location_name
        ), mock.patch(
            "s2coastalbot.main.Mastodon", mock_mastodon
        ), mock.patch(
            "s2coastalbot.main.clean_data_based_on_tci_file", mock_clean_data
        ):
            s2coastalbot_main(config)

        # Assert Mastodon API interaction
        # Cleaning is expected to be called when Twitter fails due to missing config
        mock_mastodon.assert_called_once()
        mock_mastodon_instance.log_in.assert_called_once_with(
            "mock_mastodon_login_email",
            "mock_mastodon_password",
            to_file="mock_mastodon_secret_file",
        )
        mock_mastodon_instance.media_post.assert_called_once_with(
            media_file=mock_postprocessed_file,
            description="Snapshot of a satellite image of a coastal area.",
        )
        mock_mastodon_instance.status_post.assert_called_once_with(
            status=mock.ANY, media_ids=["mock_media_id"], visibility="public"
        )
        assert mock_location_name in mock_mastodon_instance.status_post.call_args[1]["status"]


def test_twitter_post():
    """Test posting image to Twitter."""

    # Create temporary dir for output path
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        # Mock image downloading and processing flow
        mock_tci_file = tmp_dir / "mock_image.tif"
        mock_download_tci_image = mock.MagicMock(
            return_value=(mock_tci_file, datetime.datetime.now())
        )
        mock_postprocessed_file = tmp_dir / "postprocessed_image.png"
        mock_center_coords = (45.0, -73.0)
        mock_postprocess_tci_image = mock.MagicMock(
            return_value=(mock_postprocessed_file, mock_center_coords)
        )
        mock_location_name = "mock location name"
        mock_get_location_name = mock.MagicMock(return_value=mock_location_name)
        mock_clean_data = mock.MagicMock()

        # Mock Twitter media upload and post behavior
        mock_twitter_api_instance = mock.MagicMock()
        mock_twitter_api_instance.media_upload.return_value.media_id = "mock_media_id"
        mock_twitter_api = mock.MagicMock(return_value=mock_twitter_api_instance)
        mock_twitter_client_instance = mock.MagicMock()
        mock_twitter_client = mock.MagicMock(return_value=mock_twitter_client_instance)

        config = configparser.ConfigParser()
        config["misc"] = {
            "aoi_file_postprocessing": tmp_dir / "mock_aoi_file.geojson",
            "cleaning": True,
        }
        config["access"] = {
            "mastodon_login_email": "",
            "mastodon_password": "",
            "mastodon_client_id": "",
            "mastodon_client_secret": "",
            "mastodon_base_url": "",
            "mastodon_secret_file": "",
            "twitter_consumer_key": "mock_twitter_consumer_key",
            "twitter_consumer_secret": "mock_twitter_consumer_secret",
            "twitter_access_token": "mock_twitter_access_token",
            "twitter_access_token_secret": "mock_twitter_access_token_secret",
        }

        with mock.patch(
            "s2coastalbot.main.download_tci_image", mock_download_tci_image
        ), mock.patch(
            "s2coastalbot.main.postprocess_tci_image", mock_postprocess_tci_image
        ), mock.patch(
            "s2coastalbot.main.get_location_name", mock_get_location_name
        ), mock.patch(
            "s2coastalbot.main.Mastodon", mock.MagicMock()
        ), mock.patch(
            "s2coastalbot.main.tweepy.API", mock_twitter_api
        ), mock.patch(
            "s2coastalbot.main.tweepy.Client", mock_twitter_client
        ), mock.patch(
            "s2coastalbot.main.clean_data_based_on_tci_file", mock_clean_data
        ):
            s2coastalbot_main(config)

        # Assert Twitter API interaction
        mock_twitter_api.assert_called_once()
        mock_twitter_api_instance.media_upload.assert_called_once_with(
            filename=mock_postprocessed_file
        )
        mock_twitter_client_instance.create_tweet.assert_called_once_with(
            text=mock.ANY, media_ids=["mock_media_id"], user_auth=True
        )


def test_error_in_posting(caplog):
    """Mock error cases for Mastodon posting."""

    # Create temporary dir for output path
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        # Mock image downloading and processing flow
        mock_tci_file = tmp_dir / "mock_image.tif"
        mock_download_tci_image = mock.MagicMock(
            return_value=(mock_tci_file, datetime.datetime.now())
        )
        mock_postprocessed_file = tmp_dir / "postprocessed_image.png"
        mock_center_coords = (45.0, -73.0)
        mock_postprocess_tci_image = mock.MagicMock(
            return_value=(mock_postprocessed_file, mock_center_coords)
        )
        mock_location_name = "mock location name"
        mock_get_location_name = mock.MagicMock(return_value=mock_location_name)
        mock_clean_data = mock.MagicMock()

        # Mock Mastodon login and media post behavior
        mock_mastodon_instance = mock.MagicMock()
        mock_error_msg = "Mock Mastodon error"
        mock_mastodon_instance.media_post.side_effect = Exception(mock_error_msg)
        mock_mastodon = mock.MagicMock(return_value=mock_mastodon_instance)

        config = configparser.ConfigParser()
        config["misc"] = {
            "aoi_file_postprocessing": tmp_dir / "mock_aoi_file.geojson",
            "cleaning": True,
        }
        config["access"] = {
            "mastodon_login_email": "mock_mastodon_login_email",
            "mastodon_password": "mock_mastodon_password",
            "mastodon_client_id": "mock_mastodon_client_id",
            "mastodon_client_secret": "mock_mastodon_client_secret",
            "mastodon_base_url": "mock_mastodon_base_url",
            "mastodon_secret_file": "mock_mastodon_secret_file",
        }

        # Create logger to capture error log
        logger = get_custom_logger(tmp_dir / "test.log")  # noqa F841

        with mock.patch(
            "s2coastalbot.main.download_tci_image", mock_download_tci_image
        ), mock.patch(
            "s2coastalbot.main.postprocess_tci_image", mock_postprocess_tci_image
        ), mock.patch(
            "s2coastalbot.main.get_location_name", mock_get_location_name
        ), mock.patch(
            "s2coastalbot.main.Mastodon", mock_mastodon
        ), mock.patch(
            "s2coastalbot.main.clean_data_based_on_tci_file", mock_clean_data
        ):
            s2coastalbot_main(config)

        assert caplog.text.endswith(f"Error posting toot: {mock_error_msg}\n")
        mock_clean_data.assert_called_once()


def test_update_posted_images_csv():
    """Ensure that the CSV file is updated correctly when an image is posted."""

    # Create temporary dir for output path
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        # Mock image downloading and processing flow
        mock_tci_file = tmp_dir / "mock_product_name" / "mock_image.tif"
        mock_download_tci_image = mock.MagicMock(
            return_value=(mock_tci_file, datetime.datetime.now())
        )
        mock_postprocessed_file = tmp_dir / "postprocessed_image.png"
        mock_center_coords = (45.0, -73.0)
        mock_postprocess_tci_image = mock.MagicMock(
            return_value=(mock_postprocessed_file, mock_center_coords)
        )
        mock_location_name = "mock location name"
        mock_get_location_name = mock.MagicMock(return_value=mock_location_name)
        mock_clean_data = mock.MagicMock()

        # Mock config
        config = configparser.ConfigParser()
        config["misc"] = {
            "aoi_file_postprocessing": tmp_dir / "mock_aoi_file.geojson",
            "cleaning": True,
        }
        config["access"] = {
            "mastodon_login_email": "",
            "mastodon_password": "",
            "mastodon_client_id": "",
            "mastodon_client_secret": "",
            "mastodon_base_url": "",
            "mastodon_secret_file": "",
            "twitter_consumer_key": "",
            "twitter_consumer_secret": "",
            "twitter_access_token": "",
            "twitter_access_token_secret": "",
        }

        # Mock posted images file
        mock_posted_images_file = tmp_dir / "data" / "posted_images.csv"
        mock_posted_images_file.parent.mkdir(exist_ok=True, parents=True)

        with mock.patch(
            "s2coastalbot.main.download_tci_image", mock_download_tci_image
        ), mock.patch(
            "s2coastalbot.main.postprocess_tci_image", mock_postprocess_tci_image
        ), mock.patch(
            "s2coastalbot.main.get_location_name", mock_get_location_name
        ), mock.patch(
            "s2coastalbot.main.Mastodon", mock.MagicMock()
        ), mock.patch(
            "s2coastalbot.main.tweepy.API", mock.MagicMock()
        ), mock.patch(
            "s2coastalbot.main.tweepy.Client", mock.MagicMock()
        ), mock.patch(
            "s2coastalbot.main.Path", return_value=tmp_dir / "data" / "mock_subdir"
        ), mock.patch(
            "s2coastalbot.main.clean_data_based_on_tci_file", mock_clean_data
        ):
            s2coastalbot_main(config)

        assert mock_posted_images_file.exists()
        with mock_posted_images_file.open() as f:
            assert "mock_product_name" in f.read()
