import logging
from distutils.version import StrictVersion

from configparser import ConfigParser

LOG = logging.getLogger(__name__)
DEFAULT_FILENAME = 'app.ini'


def empty():
    return ConfigParser()


def from_string(data):
    LOG.debug('Loading config from string')
    parser = ConfigParser()
    parser.read_string(data)
    return parser


def from_filename(filename):
    LOG.debug('Loading config from %r', filename)
    parser = ConfigParser()
    with open(filename) as fp:
        parser.readfp(fp)
    return parser


def get_version(parser):
    if not parser.has_section('meta') or not parser.has_option('meta', 'version'):
        return None
    raw_value = parser.get('meta', 'version')
    parsed = StrictVersion(raw_value)
    return parsed


def update_from_file(parser, filename):
    LOG.debug('Updating %r from %r', parser, filename)
    with open(filename) as fp:
        parser.readfp(fp)
