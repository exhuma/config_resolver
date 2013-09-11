import unittest
import os
from os.path import expanduser, join
from ConfigParser import NoOptionError, NoSectionError

from config_resolver import Config, SecuredConfig


class SimpleInitTest(unittest.TestCase):

    def setUp(self):
        self.cfg = Config('hello', 'world', search_path='testdata')

    def test_simple_init(self):
        self.assertTrue(self.cfg.has_section('section1'))

    def test_get(self):
        self.assertEqual(self.cfg.get('section1', 'var1'), 'foo')
        self.assertEqual(self.cfg.get('section1', 'var2'), 'bar')
        self.assertEqual(self.cfg.get('section2', 'var1'), 'baz')

    def test_no_option_error(self):
        self.assertIs(self.cfg.get('section1', 'b'), None)

    def test_no_section_error(self):
        self.assertIs(self.cfg.get('a', 'b'), None)


class AdvancedInitTest(unittest.TestCase):

    def tearDown(self):
        os.environ.pop('HELLO_WORLD_PATH', None)
        os.environ.pop('HELLO_WORLD_CONFIG', None)

    def test_env_name(self):
        os.environ['HELLO_WORLD_CONFIG'] = 'test.ini'
        cfg = Config('hello', 'world')
        expected = ['/etc/hello/world/test.ini',
                    expanduser('~/.hello/world/test.ini'),
                    '{}/test.ini'.format(os.getcwd())]
        self.assertEqual(
            cfg.active_path,
            expected)

    def test_env_path(self):
        os.environ['HELLO_WORLD_PATH'] = 'testdata:testdata/a:testdata/b'
        cfg = Config('hello', 'world')
        expected = ['testdata/app.ini',
                    'testdata/a/app.ini', 'testdata/b/app.ini']
        self.assertEqual(
            cfg.active_path,
            expected)

    def test_env_path_add(self):
        os.environ['HELLO_WORLD_PATH'] = '+testdata:testdata/a:testdata/b'
        cfg = Config('hello', 'world')
        expected = ['/etc/hello/world/app.ini',
                    expanduser('~/.hello/world/app.ini'),
                    '{}/app.ini'.format(os.getcwd()),
                    'testdata/app.ini',
                    'testdata/a/app.ini', 'testdata/b/app.ini']
        self.assertEqual(
            cfg.active_path,
            expected)

    def test_search_path(self):
        cfg = Config('hello', 'world',
                     search_path='testdata:testdata/a:testdata/b')
        self.assertTrue(cfg.has_section('section3'))
        self.assertEqual(cfg.get('section1', 'var1'), 'frob')
        self.assertEqual(
            cfg.loaded_files,
            ['testdata/app.ini', 'testdata/a/app.ini', 'testdata/b/app.ini'])

    def test_filename(self):
        cfg = Config('hello', 'world', filename='test.ini',
                     search_path='testdata')
        self.assertEqual(cfg.get('section2', 'var1'), 'baz')

    def test_app_group_name(self):
        cfg = Config('hello', 'world')
        self.assertEqual(cfg.group_name, 'hello')
        self.assertEqual(cfg.app_name, 'world')


class FunctionalityTests(unittest.TestCase):

    def setUp(self):
        self.cfg = Config('hello', 'world', search_path='testdata')

    def test_mandatory_section(self):
        with self.assertRaises(NoSectionError):
            self.cfg.get('nosuchsection', 'nosuchoption', mandatory=True)

    def test_mandatory_option(self):
        with self.assertRaises(NoOptionError):
            self.cfg.get('section1', 'nosuchoption', mandatory=True)

    def test_unsecured_file(self):
        conf = SecuredConfig('hello', 'world', filename='test.ini',
                             search_path='testdata')
        self.assertNotIn(join('testdata', 'test.ini'), conf.loaded_files)

    def test_secured_file(self):
        conf = SecuredConfig('hello', 'world', filename='secure.ini',
                             search_path='testdata')
        self.assertIn(join('testdata', 'secure.ini'), conf.loaded_files)


if __name__ == '__main__':
    unittest.main()
