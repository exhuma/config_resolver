'''
The documentation contains some code examples.

The code examples are included from existing files on dist. We can load those,
execute them an verify that they actually behave as documented to make sure the
documentation is not lying, This test-case takes care of that.
'''

import unittest
from tests.helpers import execute, environment


class TestDocExamples(unittest.TestCase):

    def test_example_01(self):
        filename = 'doc/examples/example01.py'
        with environment(ACMECORP_BIRD_FEEDER_PATH='tests/examples/configs'):
            data = execute(filename)
        loaded_config = data['cfg']
        result = loaded_config.get('section', 'var')
        expected = 'value'
        self.assertEqual(result, expected)

    def test_example_02(self):
        filename = 'doc/examples/example02.py'
        with environment(
                ACMECORP_BIRD_FEEDER_PATH='tests/examples/configs',
                ACMECORP_BIRD_FEEDER_FILENAME='secure.ini'):
            data = execute(filename)
        loaded_config = data['cfg']
        result = loaded_config.get('section', 'var')
        expected = 'value'
        self.assertEqual(result, expected)

    def test_example_03(self):
        filename = 'doc/examples/example03.py'
        with environment(
                ACMECORP_BIRD_FEEDER_PATH='tests/examples/configs',
                ACMECORP_BIRD_FEEDER_FILENAME='versioned.ini'):
            data = execute(filename)
        loaded_config = data['cfg']
        result = loaded_config.get('section', 'var')
        expected = 'value'
        self.assertEqual(result, expected)

    def test_example_04(self):
        filename = 'doc/examples/example04.py'
        with environment(
                ACMECORP_BIRD_FEEDER_PATH='tests/examples/configs',
                ACMECORP_BIRD_FEEDER_FILENAME='versioned.ini'):
            data = execute(filename)
        result = data['cfg']

        dictified = dict(result.meta._asdict())  # makes testing easier
        prefix_filter = dictified.pop('prefix_filter')  # Cannot do a simple equality for this!
        expected = {
            'active_path': ['tests/examples/configs/versioned.ini'],
            'loaded_files': ['tests/examples/configs/versioned.ini'],
            'config_id': ('acmecorp', 'bird_feeder'),
        }
        self.assertEqual(dictified, expected)
        self.assertTrue(hasattr(prefix_filter, 'filter'),
                        'Attribute "filter" missing on %r' % prefix_filter)
