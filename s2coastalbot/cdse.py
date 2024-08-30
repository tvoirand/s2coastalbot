"""Download products from CDSE using OData API with node filtering."""

# standard library
import fnmatch
import json
import logging
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Union

# third party
import requests
from cdsetool.credentials import Credentials

logger = logging.getLogger()


def search_nodes(node_url: str, pattern: str, exclude: bool = False) -> List[Dict[str, Any]]:
    """Search for a given pattern in product node tree obtained from a CDSE OData API url.

    Args:
        node_url (str)
        pattern (str)
        exclude (bool): If set to False, return only nodes that match pattern, if set to True,
            return only nodes that do not match pattern

    Returns
        output_nodes (list[dict[str, Any]])
    """
    input_nodes = json.loads(requests.get(node_url).text)["result"]
    output_nodes = []
    for node in input_nodes:

        # If this node is a dir, call 'search_nodes' recursively
        if node["ContentLength"] == 0:
            output_nodes.extend(search_nodes(node["Nodes"]["uri"], pattern))

        # If this node is a file, check for pattern match and optionally append to results
        elif node["ContentLength"] >= 0:
            match = fnmatch.fnmatch(node["Name"], pattern)
            if exclude and not match:
                output_nodes.append(node)
            elif match:
                output_nodes.append(node)

    return output_nodes


def odata_download_with_nodefilter(
    feature_id: str,
    output_path: Path,
    username: str,
    password: str,
    nodefilter_pattern: Union[str, None] = None,
    exclude: bool = False,
) -> Union[str, None]:
    """Download files from CDSE using OData API with node filtering pattern.

    Args:
        feature_id (str): Product features ID, typically obtained from CDSE OpenSearch API for
            example through CDSETool
        output_path (Path)
        username (str)
        password (str)
        nodefilter_pattern (str)
        exclude (bool): If set to False, return only nodes that match pattern, if set to True,
            return only nodes that do not match pattern

    Returns:
        feature_id (str)
    """
    output_path.mkdir(exist_ok=True, parents=True)
    url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({feature_id})/Nodes"
    nodes = search_nodes(url, nodefilter_pattern, exclude)

    for node in nodes:

        # Authenticate to CDSE using CDSETool
        session = Credentials(username, password).get_session()

        url = f"{node['Nodes']['uri'][:-5]}$value"
        response = session.get(url, stream=True)

        # Download file if request was successful
        if response.status_code == 200:
            with open(
                output_path / node["Name"], "wb"  # TODO: Reproduce directories tree structure
            ) as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
        else:
            logger.error(f"Failed to download file. Status code: {response.status_code}")
            logger.error(response.text)

    return feature_id
