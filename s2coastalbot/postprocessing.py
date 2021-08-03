"""
Image postprocessing module for s2coastalbot.
"""

# standard imports
import os

# third party imports
import rasterio
from rasterio.enums import Resampling
import numpy as np


def postprocess_tci_image(input_file):
    """
    Postprocess TCI image for s2coastalbot.
    Input:
        -input_file     str
    Output:
        -               str
            path to output file
    """

    # create some constants
    output_file = "{}_postprocessed.png".format(os.path.splitext(input_file)[0])
    upscale_factor = 1/10

    # open input dataset
    with rasterio.open(input_file) as in_dataset:

        # dataset dimensions
        nb_bands = in_dataset.count
        height = int(in_dataset.height * upscale_factor)
        width = int(in_dataset.width * upscale_factor)

        # read and resample data to target shape
        data = in_dataset.read(
            out_shape=(
                nb_bands,
                height,
                width,
            ),
            resampling=Resampling.bilinear
        )

        # scale image transform
        transform = in_dataset.transform * in_dataset.transform.scale(
            (in_dataset.width / data.shape[-1]),
            (in_dataset.height / data.shape[-2])
        )

    # edit histogram
    data = np.asarray(data, dtype=np.float32)
    data = data * 3
    data[data>255] = 255
    data = np.asarray(data, dtype=np.uint8)

    # write output dataset
    with rasterio.open(
        output_file,
        "w",
        driver="PNG",
        count=nb_bands,
        height=height,
        width=width,
        dtype=np.uint8,
        transform=transform,
    ) as out_dataset:
        out_dataset.write(data)

    return output_file
