'''
Handler for JSON files
'''

from json import load, loads

from config_resolver.dirty import StrictVersion

from .base import Handler


class JsonHandler(Handler[dict]):
    """
    A config-resolver handler capable of reading ".json" files.
    """
    DEFAULT_FILENAME = 'app.json'

    @staticmethod
    def empty() -> dict:
        return {}

    @staticmethod
    def from_string(data: str) -> dict:
        return loads(data)

    @staticmethod
    def from_filename(filename: str) -> dict:
        with open(filename) as fptr:
            output = load(fptr)
        return output

    @staticmethod
    def get_version(config: dict) -> StrictVersion:
        if 'meta' not in config or 'version' not in config['meta']:
            return None
        raw_value = config['meta']['version']
        parsed = StrictVersion(raw_value)
        return parsed

    @staticmethod
    def update_from_file(config: dict, filename: str) -> None:
        with open(filename) as fptr:
            new_data = load(fptr)
            config.update(new_data)
