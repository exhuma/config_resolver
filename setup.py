from setuptools import setup, find_packages

PACKAGE = "config_resolver"
NAME = "config_resolver"
DESCRIPTION = "A small package to automatically find a configuration file."
AUTHOR = "Michel Albert"
AUTHOR_EMAIL = "michel@albert.lu"
VERSION = __import__(PACKAGE).__version__

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=open("README.rst").read(),
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license="LGPL",
    url='https://github.com/exhuma/config_resolver',
    packages=find_packages(exclude=["tests.*", "tests"]),
)
