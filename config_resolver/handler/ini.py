'''
Handler for INI files
'''

from configparser import ConfigParser

from config_resolver.dirty import StrictVersion

DEFAULT_FILENAME = 'app.ini'


def empty():
    '''
    Create an empty configuration instance.
    '''
    return ConfigParser()


def from_string(data):
    '''
    Create a configuration instance from a text-string
    '''
    parser = ConfigParser()
    parser.read_string(data)
    return parser


def from_filename(filename):
    '''
    Create a configuration instance from a file-name.
    '''
    parser = ConfigParser()
    with open(filename) as fptr:
        parser.read_file(fptr)
    return parser


def get_version(parser):
    '''
    Retrieve the parsed version number from a given config instance.
    '''
    if (not parser.has_section('meta') or
            not parser.has_option('meta', 'version')):
        return None
    raw_value = parser.get('meta', 'version')
    parsed = StrictVersion(raw_value)
    return parsed


def update_from_file(parser, filename):
    '''
    Updates an existing config instance from a given filename.

    The config instance in *data* will be modified in-place!
    '''
    with open(filename) as fptr:
        parser.read_file(fptr)
