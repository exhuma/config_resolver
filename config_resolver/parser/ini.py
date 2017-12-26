import logging
from distutils.version import StrictVersion

from configparser import ConfigParser

LOG = logging.getLogger(__name__)


class Parser:

    @staticmethod
    def from_string(data):
        LOG.debug('Loading config from string')
        parser = ConfigParser()
        parser.read_string(data)
        return Parser(parser)

    @staticmethod
    def from_filename(filename):
        LOG.debug('Loading config from %r', filename)
        parser = ConfigParser()
        with open(filename) as fp:
            parser.readfp(fp)
        return Parser(parser)

    def __init__(self, config_parser_instance=None):
        self.__parser = config_parser_instance or ConfigParser()

    @property
    def version(self):
        if not self.__parser.has_section('meta') or not self.__parser.has_option('meta', 'version'):
            return None
        raw_value = self.__parser.get('meta', 'version')
        parsed = StrictVersion(raw_value)
        return parsed

    def update_from_file(self, filename):
        LOG.debug('Updating config from %r', filename)
        with open(filename) as fp:
            self.__parser.readfp(fp)

    def has_section(self, section_name):
        return self.__parser.has_section(section_name)

    def get(self, section, option, fallback=None):
        return self.__parser.get(section, option, fallback=fallback)

    def sections(self):
        return self.__parser.sections()
