"""
Tests the "JSON" file handler.
"""
import unittest
from textwrap import dedent

from common import CommonTests

from config_resolver.handler.json import JsonHandler


class JsonTest(CommonTests, unittest.TestCase):
    HANDLER_CLASS = JsonHandler
    TEST_FILENAME = "test.json"
    APP_FILENAME = "app.json"
    DATA_PATH = "testdata/json"
    SECURE_FILENAME = "secure.json"
    MISMATCH_FILENAME = "mismatch.json"
    TEST_STRING = dedent(
        """\
        {
            "section_mem": {
                "val": 1
            }
        }
        """
    )
    EXPECTED_OBJECT_TYPE = dict

    def _get(self, config, section, option, default=None):
        if section not in config or option not in config[section]:
            return default
        return config[section][option]

    def _sections(self, config):
        return set(config.keys())

    def test_from_string(self):
        self.skipTest("The test-code is currenty no compatible with JSON files")
