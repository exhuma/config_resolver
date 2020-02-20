"""
This module is responsible to load the version information from a plain text
file to allow us to pull the version information easily using non-python tools.
"""
from os.path import dirname, join
with open(join(dirname(__file__), "version.txt")) as fptr:
    VERSION = fptr.read().strip()
