'''
Tests the default "INI" file parser.

This also includes the main functionality tests.
'''
from contextlib import contextmanager
import logging
import os
import re
import stat
import sys
import unittest
from configparser import NoOptionError, NoSectionError
from os.path import expanduser, join, abspath
from textwrap import dedent
from unittest.mock import patch

from config_resolver import (
    NoVersionError,
    from_string,
    get_config,
)


@contextmanager
def environment(**kwargs):
    """
    Context manager to tempolrarily change environment variables. On exit all
    variables are set to their original value.
    """
    old_values = {}
    nonexistent = set()
    for key in kwargs:
        if key not in os.environ:
            nonexistent.add(key)
        else:
            old_values[key] = os.environ[key]
        os.environ[key] = kwargs[key]
    try:
        yield
    finally:
        for key in old_values:
            os.environ[key] = old_values[key]
        for key in nonexistent:
            os.environ.pop(key)


class TestableHandler(logging.Handler):
    """
    A logging handler which is usable in unit tests. Log records are simply
    appended to an internal list and can be checked with ``contains``.
    """

    def __init__(self, *args, **kwargs):
        super(TestableHandler, self).__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        """
        Overrides :py:meth:`logging.Handler.emit`.
        """
        self.records.append(record)

    def assert_contains(self, logger, level, needle):
        if not self.contains(logger, level, needle):
            msg = '%s did not contain a message with %r and level %r'
            raise AssertionError(msg % (logger, needle, level))

    def assert_contains_regex(self, logger, level, needle):
        if not self.contains(logger, level, needle, is_regex=True):
            msg = '%s did not contain a message matching %r and level %r'
            raise AssertionError(msg % (logger, needle, level))

    def contains(self, logger, level, message, is_regex=False):
        """
        Checks whether a message has been logged to a specific logger with a
        specific level.

        :param logger: The logger.
        :param level: The log level.
        :param messgae: The message contents.
        :param is_regex: Whether the expected message is a regex or not.
            Non-regex messages are simply tested for inclusion.
        """
        for record in self.records:
            if record.name != logger or record.levelno != level:
                continue
            if is_regex:
                if re.search(message, (record.msg % record.args)):
                    return True
            else:
                if message in (record.msg % record.args):
                    return True
        return False

    def reset(self):
        del self.records[:]


class SimpleInitFromContent(unittest.TestCase):
    '''
    Tests loading a config string from memory
    '''
    # TODO: This should also check if the [meta] section is properly parsed!

    def setUp(self):
        self.cfg = from_string(dedent(
            '''\
            [section_mem]
            val = 1
            '''
        ))

    def test_sections_available(self):
        self.assertTrue(self.cfg.has_section('section_mem'))

    def test_getting_values(self):
        self.assertEqual(self.cfg.get('section_mem', 'val'), '1')


class SimpleInitTest(unittest.TestCase):

    def setUp(self):
        self.cfg = get_config('hello', 'world', search_path='testdata')

    def test_simple_init(self):
        self.assertTrue(self.cfg.has_section('section1'))

    def test_get(self):
        self.assertEqual(self.cfg.get('section1', 'var1'), 'foo')
        self.assertEqual(self.cfg.get('section1', 'var2'), 'bar')
        self.assertEqual(self.cfg.get('section2', 'var1'), 'baz')

    def test_no_option_error(self):
        self.assertIs(self.cfg.get('section1', 'b', fallback=None), None)

    def test_no_section_error(self):
        self.assertIs(self.cfg.get('a', 'b', fallback=None), None)


class AdvancedInitTest(unittest.TestCase):

    def setUp(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        self.catcher = TestableHandler()
        logger.addHandler(self.catcher)

    def tearDown(self):
        self.catcher.reset()

    def test_env_name(self):
        with environment(HELLO_WORLD_FILENAME='test.ini',
                         XDG_CONFIG_HOME='',
                         XDG_CONFIG_DIRS=''):
            cfg = get_config('hello', 'world')
        expected = ['/etc/hello/world/test.ini',
                    '/etc/xdg/hello/world/test.ini',
                    expanduser('~/.config/hello/world/test.ini'),
                    '{}/.hello/world/test.ini'.format(os.getcwd())]
        self.assertEqual(
            cfg.active_path,
            expected)

    def test_env_name_override(self):
        with environment(HELLO_WORLD_FILENAME='test.ini'):
            get_config('hello', 'world')
        msg = ("filename was overridden with 'test.ini' by the environment "
               "variable HELLO_WORLD_FILENAME")
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)

    def test_env_path(self):
        with environment(HELLO_WORLD_PATH='testdata:testdata/a:testdata/b'):
            cfg = get_config('hello', 'world')
        expected = ['testdata/app.ini',
                    'testdata/a/app.ini',
                    'testdata/b/app.ini']
        self.assertEqual(
            cfg.active_path,
            expected)

    def test_env_path_override_log(self):
        with environment(HELLO_WORLD_PATH='testdata:testdata/a:testdata/b'):
            get_config('hello', 'world')
        msg = ("overridden with 'testdata:testdata/a:testdata/b' by the "
               "environment variable 'HELLO_WORLD_PATH'")
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)

    def test_env_path_add(self):
        with environment(HELLO_WORLD_PATH='+testdata:testdata/a:testdata/b',
                         XDG_CONFIG_HOME='',
                         XDG_CONFIG_DIRS=''):
            cfg = get_config('hello', 'world')
        expected = ['/etc/hello/world/app.ini',
                    '/etc/xdg/hello/world/app.ini',
                    expanduser('~/.config/hello/world/app.ini'),
                    '{}/.hello/world/app.ini'.format(os.getcwd()),
                    'testdata/app.ini',
                    'testdata/a/app.ini', 'testdata/b/app.ini']
        self.assertEqual(
            cfg.active_path,
            expected)

    def test_env_path_add_log(self):
        with environment(HELLO_WORLD_PATH='+testdata:testdata/a:testdata/b'):
            get_config('hello', 'world')
        msg = ("extended with ['testdata', 'testdata/a', 'testdata/b'] by the "
               "environment variable HELLO_WORLD_PATH")
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)

    def test_search_path(self):
        cfg = get_config('hello', 'world',
                         search_path='testdata:testdata/a:testdata/b')
        self.assertTrue(cfg.has_section('section3'))
        self.assertEqual(cfg.get('section1', 'var1'), 'frob')
        self.assertEqual(
            cfg.loaded_files,
            ['testdata/app.ini', 'testdata/a/app.ini', 'testdata/b/app.ini'])

    def test_filename(self):
        cfg = get_config('hello', 'world', filename='test.ini',
                         search_path='testdata')
        self.assertEqual(cfg.get('section2', 'var1'), 'baz')

    def test_app_group_name(self):
        cfg = get_config('hello', 'world')
        self.assertEqual(cfg.group_name, 'hello')
        self.assertEqual(cfg.app_name, 'world')


class FunctionalityTests(unittest.TestCase):

    def setUp(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        self.catcher = TestableHandler()
        logger.addHandler(self.catcher)

    def tearDown(self):
        self.catcher.reset()

    def test_mandatory_section(self):
        config = get_config('hello', 'world', search_path='testdata')
        with self.assertRaises(NoSectionError):
            config.get('nosuchsection', 'nosuchoption')

    def test_mandatory_option(self):
        config = get_config('hello', 'world', search_path='testdata')
        with self.assertRaises(NoOptionError):
            config.get('section1', 'nosuchoption')

    def test_unsecured_logmessage(self):
        logger = logging.getLogger('config_resolver')
        logger.setLevel(logging.DEBUG)
        catcher = TestableHandler()
        logger.addHandler(catcher)
        get_config('hello', 'world', filename='test.ini',
                   search_path='testdata', secure=True)
        expected_message = (
            "File 'testdata/test.ini' is not secure enough. "
            "Change it's mode to 600")
        catcher.assert_contains(
            'config_resolver.hello.world',
            logging.WARNING,
            expected_message)

    def test_unsecured_file(self):
        conf = get_config('hello', 'world', filename='test.ini',
                          search_path='testdata', secure=True)
        self.assertNotIn(join('testdata', 'test.ini'), conf.loaded_files)

    def test_secured_file(self):
        # make sure the file is secured. This information is lost through git so
        # we need to set it here manually. Also, this is only available on *nix,
        # so we need to skip if necessary
        if sys.platform not in ('linux', 'linux2'):
            self.skipTest('Only runnable on *nix')

        path = join('testdata', 'secure.ini')
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

        conf = get_config('hello', 'world', filename='secure.ini',
                          search_path='testdata', secure=True)
        self.assertIn(path, conf.loaded_files)

    def test_secured_nonexisting_file(self):
        conf = get_config('hello', 'world', filename='nonexisting.ini',
                          search_path='testdata', secure=True)
        self.assertNotIn(join('testdata', 'nonexisting.ini'),
                         conf.loaded_files)

    def test_file_not_found_exception(self):
        with self.assertRaises(IOError):
            get_config('hello', 'world', filename='nonexisting.ini',
                       search_path='testdata', require_load=True)

    def test_no_version_found_warning(self):
        with self.assertRaises(NoVersionError):
            get_config('hello', 'world', search_path='testdata', version='1.1')

    def test_mismatching_major(self):
        config = get_config('hello', 'world', search_path='testdata/versioned',
                            version='1.1')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            'Invalid major version number')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            '2.1')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            '1.1')

        # Values should not be loaded. Let's check if they really are missing.
        # They should be!
        self.assertFalse('section1' in config.sections())

        # Also, no files should be added to the "loaded_files" list.
        self.assertEqual(config.loaded_files, [])

    def test_mismatching_minor(self):
        get_config('hello', 'world', search_path='testdata/versioned',
                   version='2.0')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.WARNING,
            'Mismatching minor version number')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.WARNING,
            '2.1')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.WARNING,
            '2.0')

    def test_mixed_version_load(self):
        """
        If the instance has no version assigned, the first file which contains a
        version should "lock in" that version. This is to avoid mixed config
        files even if the application did not explicitly request a version
        number!
        """
        self.skipTest('TODO')  # XXX
        get_config('hello', 'world',
                   filename='mismatch.ini',
                   search_path='testdata/versioned:testdata/versioned2')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            'Invalid major version number')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            '1.0')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            '2.0')

    def test_xdg_config_dirs(self):
        with environment(XDG_CONFIG_DIRS='/xdgpath1:/xdgpath2',
                         XDG_CONFIG_HOME=''):
            cfg = get_config('foo', 'bar')
            self.assertEqual([
                '/etc/foo/bar/app.ini',
                '/xdgpath2/foo/bar/app.ini',
                '/xdgpath1/foo/bar/app.ini',
                expanduser('~/.config/foo/bar/app.ini'),
                abspath('.foo/bar/app.ini')
            ], cfg.active_path)

    def test_xdg_empty_config_dirs(self):
        with environment(XDG_CONFIG_DIRS='',
                         XDG_CONFIG_HOME=''):
            cfg = get_config('foo', 'bar')
            self.assertEqual([
                '/etc/foo/bar/app.ini',
                '/etc/xdg/foo/bar/app.ini',
                expanduser('~/.config/foo/bar/app.ini'),
                abspath('.foo/bar/app.ini')
            ], cfg.active_path)

    def test_xdg_config_home(self):
        with environment(XDG_CONFIG_HOME='/path/to/config/home',
                         XDG_CONFIG_DIRS=''):
            cfg = get_config('foo', 'bar')
            self.assertEqual([
                '/etc/foo/bar/app.ini',
                '/etc/xdg/foo/bar/app.ini',
                '/path/to/config/home/foo/bar/app.ini',
                abspath('.foo/bar/app.ini')
            ], cfg.active_path)

    def test_xdg_empty_config_home(self):
        with environment(XDG_CONFIG_HOME='',
                         XDG_CONFIG_DIRS=''):
            cfg = get_config('foo', 'bar')
            self.assertEqual([
                '/etc/foo/bar/app.ini',
                '/etc/xdg/foo/bar/app.ini',
                expanduser('~/.config/foo/bar/app.ini'),
                abspath('.foo/bar/app.ini')
            ], cfg.active_path)

    def test_both_xdg_variables(self):
        with environment(XDG_CONFIG_DIRS='/xdgpath1:/xdgpath2',
                         XDG_CONFIG_HOME='/xdg/config/home'):
            cfg = get_config('foo', 'bar')
            self.assertEqual([
                '/etc/foo/bar/app.ini',
                '/xdgpath2/foo/bar/app.ini',
                '/xdgpath1/foo/bar/app.ini',
                '/xdg/config/home/foo/bar/app.ini',
                abspath('.foo/bar/app.ini')
            ], cfg.active_path)

    def test_filename_in_log_minor(self):
        """
        When getting a version number mismatch, the filename should be logged!
        """
        get_config('hello', 'world', search_path='testdata/versioned',
                   version='2.0')
        self.catcher.assert_contains_regex(
            'config_resolver.hello.world',
            logging.WARNING,
            'testdata/versioned/app.ini')

    def test_filename_in_log_major(self):
        """
        When getting a version number mismatch, the filename should be logged!
        """
        get_config('hello', 'world', search_path='testdata/versioned',
                   version='5.0')
        self.catcher.assert_contains_regex(
            'config_resolver.hello.world',
            logging.ERROR,
            'testdata/versioned/app.ini')


if __name__ == '__main__':
    unittest.main()
