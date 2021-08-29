"""
Script defining python package for s2coastalbot.
"""

# standard imports
import os
from setuptools import find_packages
from setuptools import setup


dependencies = [
    "tweepy",
    "sentinelsat",
    "pandas",
    "shapely",
    "rasterio",
    "fiona",
    "pyproj",
]


setup(
    name="s2coastalbot",
    packages=find_packages(exclude=["tests"]),
    install_requires=dependencies,
)
