'''
Tests the default "INI" file handler.
'''
from configparser import ConfigParser
import unittest
from textwrap import dedent

from config_resolver.handler import ini
from common import CommonTests


class IniTest(CommonTests, unittest.TestCase):
    HANDLER_CLASS = ini
    TEST_FILENAME = 'test.ini'
    APP_FILENAME = 'app.ini'
    DATA_PATH = 'testdata/ini'
    SECURE_FILENAME = 'secure.ini'
    MISMATCH_FILENAME = 'mismatch.ini'
    TEST_STRING = dedent(
        '''\
        [section_mem]
        val = 1
        '''
    )
    EXPECTED_OBJECT_TYPE = ConfigParser

    def _get(self, config, section, option, default=None):
        return config.get(section, option, fallback=default)

    def _sections(self, config):
        return set(config.sections())
