"""
Script defining python package for s2coastalbot.
"""

# third party
from setuptools import find_packages
from setuptools import setup

setup(
    name="s2coastalbot",
    version="0.16",
    packages=find_packages(exclude=["tests"]),
)
