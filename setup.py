from setuptools import find_packages, setup

PACKAGE = "config_resolver"
NAME = "config_resolver"
DESCRIPTION = "A small package to automatically find a configuration file."
AUTHOR = "Michel Albert"
AUTHOR_EMAIL = "michel@albert.lu"

with open("config_resolver/version.txt") as fptr:
    VERSION = fptr.read().strip()

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    url="https://github.com/exhuma/config_resolver",
    project_urls={
        "Bug Tracker": "https://github.com/exhuma/config_resolver/issues",
        "Documentation": "https://config-resolver.readthedocs.org/en/latest/",
    },
    long_description=open("README.rst").read(),
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license="MIT",
    include_package_data=True,
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=["packaging"],
    package_data={
        "config_resolver": ["py.typed"],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 "
        "(LGPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
