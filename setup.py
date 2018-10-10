import sys

from setuptools import find_packages, setup

PACKAGE = "config_resolver"
NAME = "config_resolver"
DESCRIPTION = "A small package to automatically find a configuration file."
AUTHOR = "Michel Albert"
AUTHOR_EMAIL = "michel@albert.lu"
VERSION = __import__(PACKAGE).__version__

DEPENDENCIES = []  # type: ignore
if sys.version_info < (3, 0):
    DEPENDENCIES.append('typing')

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    url='https://github.com/exhuma/config_resolver',
    long_description=open("README.rst").read(),
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license="MIT",
    include_package_data=True,
    packages=['config_resolver'],
    install_requires=DEPENDENCIES,
    requires=DEPENDENCIES,
    package_data={
        'config_resolver': ['py.typed'],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 '
        '(LGPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
