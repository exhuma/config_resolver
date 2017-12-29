from distutils.version import StrictVersion

from configparser import ConfigParser

DEFAULT_FILENAME = 'app.ini'


def empty():
    return ConfigParser()


def from_string(data):
    parser = ConfigParser()
    parser.read_string(data)
    return parser


def from_filename(filename):
    parser = ConfigParser()
    with open(filename) as fp:
        parser.read_file(fp)
    return parser


def get_version(parser):
    if not parser.has_section('meta') or not parser.has_option('meta', 'version'):
        return None
    raw_value = parser.get('meta', 'version')
    parsed = StrictVersion(raw_value)
    return parsed


def update_from_file(parser, filename):
    with open(filename) as fp:
        parser.read_file(fp)
