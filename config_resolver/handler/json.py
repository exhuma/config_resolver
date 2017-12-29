from distutils.version import StrictVersion

from json import load, loads

DEFAULT_FILENAME = 'app.json'


def empty():
    return {}


def from_string(data):
    return loads(data)


def from_filename(filename):
    with open(filename) as fp:
        output = load(fp)
    return output


def get_version(data):
    if 'meta' not in data or 'version' not in data['meta']:
        return None
    raw_value = data['meta']['version']
    parsed = StrictVersion(raw_value)
    return parsed


def update_from_file(data, filename):
    with open(filename) as fp:
        new_data = load(fp)
        data.update(new_data)
