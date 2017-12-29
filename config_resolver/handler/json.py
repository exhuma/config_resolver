'''
Handler for JSON files
'''

from distutils.version import StrictVersion

from json import load, loads

DEFAULT_FILENAME = 'app.json'


def empty():
    '''
    Create an empty configuration instance.
    '''
    return {}


def from_string(data):
    '''
    Create a configuration instance from a text-string
    '''
    return loads(data)


def from_filename(filename):
    '''
    Create a configuration instance from a file-name.
    '''
    with open(filename) as fp:
        output = load(fp)
    return output


def get_version(data):
    '''
    Retrieve the parsed version number from a given config instance.
    '''
    if 'meta' not in data or 'version' not in data['meta']:
        return None
    raw_value = data['meta']['version']
    parsed = StrictVersion(raw_value)
    return parsed


def update_from_file(data, filename):
    '''
    Updates an existing config instance from a given filename.

    The config instance in *data* will be modified in-place!
    '''
    with open(filename) as fp:
        new_data = load(fp)
        data.update(new_data)
