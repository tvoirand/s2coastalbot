"""Test functionalities to download data using CDSE's OData API."""

# standard library
import json
import tempfile
from pathlib import Path
from unittest import mock

# current project
from s2coastalbot.cdse import odata_download_with_nodefilter
from s2coastalbot.cdse import search_nodes
from s2coastalbot.custom_logger import get_custom_logger

MOCK_TCI_NODE = {
    "Id": "T57MWM_20240827T234739_TCI_10m.jp2",
    "Name": "T57MWM_20240827T234739_TCI_10m.jp2",
    "ContentLength": 135468439,
    "ChildrenNumber": 0,
    "Nodes": {"uri": "https://mocked-uri/TCI_10m.jp2/Nodes"},
}
MOCK_B8_NODE = {
    "Id": "T57MWM_20240827T234739_B08_10m.jp2",
    "Name": "T57MWM_20240827T234739_B08_10m.jp2",
    "ContentLength": 113959795,
    "ChildrenNumber": 0,
    "Nodes": {"uri": "https://mocked-uri/B08_10m.jp2/Nodes"},
}
MOCK_FOLDER_NODE = {
    "Name": "folder",
    "ContentLength": 0,
    "ChildrenNumber": 1,
    "Nodes": {"uri": "https://mocked-uri/folder/Nodes"},
}
MOCK_NESTED_IMG_NODE = {
    "Name": "nested_raster_file.jp2",
    "ContentLength": 12345678,
    "ChildrenNumber": 0,
    "Nodes": {"uri": "https://mocked-uri/folder/nested_raster_file.jp2/Nodes"},
}
MOCK_NESTED_MTD_NODE = {
    "Name": "nested_mtd_file.xml",
    "ContentLength": 12345678,
    "ChildrenNumber": 0,
    "Nodes": {"uri": "https://mocked-uri/folder/nested_mtd_file.xml/Nodes"},
}


def test_search_nodes():

    # Mock OData API request
    mock_response = mock.MagicMock()
    mock_response.text = json.dumps({"result": [MOCK_TCI_NODE, MOCK_B8_NODE]})
    mock_odata = mock.MagicMock(return_value=mock_response)

    # Call search_nodes while patching odata request and assert that only expected node is returned
    with mock.patch("s2coastalbot.cdse.requests.get", mock_odata):
        filtered_nodes = search_nodes(node_url="", pattern="*TCI_10m.jp2")
    assert filtered_nodes == [MOCK_TCI_NODE]

    # Perform same test with 'exclude' option
    with mock.patch("s2coastalbot.cdse.requests.get", mock_odata):
        filtered_nodes = search_nodes(node_url="", pattern="*TCI_10m.jp2", exclude=True)
    assert filtered_nodes == [MOCK_B8_NODE]


def test_search_nodes_with_folder():
    """Test recursive behavior of search_nodes."""

    # Mock OData API requests: first at root folder level, then at nested file level
    mock_response_nested = mock.MagicMock()
    mock_response_nested.text = json.dumps({"result": [MOCK_NESTED_IMG_NODE, MOCK_NESTED_MTD_NODE]})
    mock_response_root = mock.MagicMock()
    mock_response_root.text = json.dumps({"result": [MOCK_FOLDER_NODE, MOCK_TCI_NODE]})
    mock_odata = mock.MagicMock(side_effect=[mock_response_root, mock_response_nested])

    # Call search_nodes while patching the odata request
    with mock.patch("s2coastalbot.cdse.requests.get", mock_odata):
        filtered_nodes = search_nodes(node_url="", pattern="*.jp2")

    # Ensure that both the root node and the nested node are returned
    assert mock_odata.call_count == 2
    assert len(filtered_nodes) == 2
    assert MOCK_TCI_NODE in filtered_nodes
    assert MOCK_NESTED_IMG_NODE in filtered_nodes


def test_odata_download_with_nodefilter():

    # Create temporary dir for output path
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        # Mock download request, nodes search, and open()
        mock_download_response = mock.MagicMock()
        mock_download_response.status_code = 200
        mock_download_response.iter_content.return_value = [b"data_chunk"]
        mock_session = mock.MagicMock()
        mock_session.get.return_value = mock_download_response
        mock_credentials = mock.MagicMock()
        mock_credentials.return_value.get_session.return_value = mock_session
        mock_nodes_search = mock.MagicMock(return_value=[MOCK_TCI_NODE])
        mock_open_file = mock.mock_open()

        # Call download function with mock args
        feature_id = "mock_feature_id"
        output_path = tmp_dir
        username = "mock_user"
        password = "mock_pwd"
        nodefilter_pattern = "*TCI_10m.jp2"
        with mock.patch("s2coastalbot.cdse.Credentials", mock_credentials), mock.patch(
            "s2coastalbot.cdse.search_nodes", mock_nodes_search
        ), mock.patch("s2coastalbot.cdse.open", mock_open_file):
            result = odata_download_with_nodefilter(
                feature_id, output_path, username, password, nodefilter_pattern=nodefilter_pattern
            )

        assert result == feature_id
        mock_nodes_search.assert_called_once_with(
            f"https://download.dataspace.copernicus.eu/odata/v1/Products({feature_id})/Nodes",
            nodefilter_pattern,
            False,
        )
        mock_session.get.assert_called_with("https://mocked-uri/TCI_10m.jp2/$value", stream=True)
        mock_opened_file = mock_open_file()
        mock_opened_file.write.assert_called_with(b"data_chunk")


def test_odata_download_with_nodefilter_failure(caplog):
    """Test file download failure with 404 response."""

    # Create temporary dir for output path
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        # Create logger to capture error log
        logger = get_custom_logger(tmp_dir / "test.log")  # noqa F841

        # Mock download request, nodes search, and open()
        mock_download_response = mock.MagicMock()
        mock_download_response.status_code = 404
        mock_session = mock.MagicMock()
        mock_session.get.return_value = mock_download_response
        mock_credentials = mock.MagicMock()
        mock_credentials.return_value.get_session.return_value = mock_session
        mock_nodes_search = mock.MagicMock(return_value=[MOCK_TCI_NODE])
        mock_open_file = mock.mock_open()

        # Call download function with mock args
        feature_id = "mock_feature_id"
        output_path = tmp_dir
        username = "mock_user"
        password = "mock_pwd"
        with mock.patch("s2coastalbot.cdse.Credentials", mock_credentials), mock.patch(
            "s2coastalbot.cdse.search_nodes", mock_nodes_search
        ), mock.patch("s2coastalbot.cdse.open", mock_open_file):
            result = odata_download_with_nodefilter(
                feature_id, output_path, username, password, nodefilter_pattern="*TCI_10m.jp2"
            )

        assert result == feature_id
        assert "Failed to download file. Status code: 404" in caplog.text
        mock_open_file.assert_not_called()
