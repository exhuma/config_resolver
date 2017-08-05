from contextlib import contextmanager
import unittest
import logging
import os
import sys
from os.path import expanduser, join, abspath
from textwrap import dedent

try:
    from ConfigParser import NoOptionError, NoSectionError
except ImportError:
    from configparser import NoOptionError, NoSectionError

try:
    from mock import patch
    have_mock = True
except ImportError:
    have_mock = False

from config_resolver import (
    Config,
    SecuredConfig,
    NoVersionError,
    IncompatibleVersion)


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

    def contains(self, logger, level, message):
        """
        Checks whether a message has been logged to a specific logger with a
        specific level.

        :param logger: The logger.
        :param level: The log level.
        :param messgae: The message contents.
        """
        for record in self.records:
            if record.name != logger or record.levelno != level:
                continue
            if message in (record.msg % record.args):
                return True
        return False


@unittest.skipUnless(sys.version_info > (3, 0), 'Test only valid in Python 2')
class SimpleInitFromContent(unittest.TestCase):
    '''
    Tests loading a config string from memory
    '''

    def setUp(self):
        self.cfg = Config('not', 'existing', search_path='testdata')
        self.cfg.read_string(dedent(
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
        self.cfg = Config('hello', 'world', search_path='testdata')

    def test_simple_init(self):
        self.assertTrue(self.cfg.has_section('section1'))

    def test_get(self):
        self.assertEqual(self.cfg.get('section1', 'var1'), 'foo')
        self.assertEqual(self.cfg.get('section1', 'var2'), 'bar')
        self.assertEqual(self.cfg.get('section2', 'var1'), 'baz')

    def test_no_option_error(self):
        self.assertIs(self.cfg.get('section1', 'b', default=None), None)

    def test_no_section_error(self):
        self.assertIs(self.cfg.get('a', 'b', default=None), None)


class AdvancedInitTest(unittest.TestCase):

    def tearDown(self):
        os.environ.pop('HELLO_WORLD_PATH', None)
        os.environ.pop('HELLO_WORLD_FILENAME', None)

    def test_env_name(self):
        os.environ['HELLO_WORLD_FILENAME'] = 'test.ini'
        with environment(XDG_CONFIG_HOME='',
                         XDG_CONFIG_DIRS=''):
            cfg = Config('hello', 'world')
        expected = ['/etc/hello/world/test.ini',
                    '/etc/xdg/hello/world/test.ini',
                    expanduser('~/.hello/world/test.ini'),
                    expanduser('~/.config/hello/world/test.ini'),
                    '{}/.hello/world/test.ini'.format(os.getcwd())]
        self.assertEqual(
            cfg.active_path,
            expected)

    def test_env_name_override(self):
        os.environ['HELLO_WORLD_FILENAME'] = 'test.ini'
        logger = logging.getLogger('config_resolver')
        logger.setLevel(logging.DEBUG)
        catcher = TestableHandler()
        logger.addHandler(catcher)
        Config('hello', 'world')
        msg = ("filename was overridden with 'test.ini' by the environment "
               "variable HELLO_WORLD_FILENAME")
        result = catcher.contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)
        self.assertTrue(result, 'Expected log message {!r} not found in '
                        'logger!'.format(msg))

    def test_env_path(self):
        os.environ['HELLO_WORLD_PATH'] = 'testdata:testdata/a:testdata/b'
        cfg = Config('hello', 'world')
        expected = ['testdata/app.ini',
                    'testdata/a/app.ini',
                    'testdata/b/app.ini']
        self.assertEqual(
            cfg.active_path,
            expected)

    def test_env_path_override_log(self):
        logger = logging.getLogger('config_resolver')
        logger.setLevel(logging.DEBUG)
        os.environ['HELLO_WORLD_PATH'] = 'testdata:testdata/a:testdata/b'
        catcher = TestableHandler()
        logger.addHandler(catcher)
        Config('hello', 'world')
        msg = ("overridden with 'testdata:testdata/a:testdata/b' by the "
               "environment variable 'HELLO_WORLD_PATH'")
        result = catcher.contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)
        self.assertTrue(result, 'Expected log message {!r} not found in '
                        'logger!'.format(msg))

    def test_env_path_add(self):
        os.environ['HELLO_WORLD_PATH'] = '+testdata:testdata/a:testdata/b'
        with environment(XDG_CONFIG_HOME='',
                         XDG_CONFIG_DIRS=''):
            cfg = Config('hello', 'world')
        expected = ['/etc/hello/world/app.ini',
                    '/etc/xdg/hello/world/app.ini',
                    expanduser('~/.hello/world/app.ini'),
                    expanduser('~/.config/hello/world/app.ini'),
                    '{}/.hello/world/app.ini'.format(os.getcwd()),
                    'testdata/app.ini',
                    'testdata/a/app.ini', 'testdata/b/app.ini']
        self.assertEqual(
            cfg.active_path,
            expected)

    def test_env_path_add_log(self):
        logger = logging.getLogger('config_resolver')
        logger.setLevel(logging.DEBUG)
        os.environ['HELLO_WORLD_PATH'] = '+testdata:testdata/a:testdata/b'
        catcher = TestableHandler()
        logger.addHandler(catcher)
        Config('hello', 'world')
        msg = ("extended with ['testdata', 'testdata/a', 'testdata/b'] by the "
               "environment variable HELLO_WORLD_PATH")
        result = catcher.contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)
        self.assertTrue(result, 'Expected log message {!r} not found in '
                        'logger!'.format(msg))

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

    def test_mandatory_section(self):
        config = Config('hello', 'world', search_path='testdata')
        with self.assertRaises(NoSectionError):
            config.get('nosuchsection', 'nosuchoption')

    def test_mandatory_option(self):
        config = Config('hello', 'world', search_path='testdata')
        with self.assertRaises(NoOptionError):
            config.get('section1', 'nosuchoption')

    def test_unsecured_logmessage(self):
        logger = logging.getLogger('config_resolver')
        logger.setLevel(logging.DEBUG)
        catcher = TestableHandler()
        logger.addHandler(catcher)
        SecuredConfig('hello', 'world', filename='test.ini',
                      search_path='testdata')
        expected_message = (
            "File 'testdata/test.ini' is not secure enough. "
            "Change it's mode to 600")
        result = catcher.contains(
            'config_resolver.hello.world',
            logging.WARNING,
            expected_message)
        self.assertTrue(result, "Expected log message: {!r} not found in "
                        "logger!".format(expected_message))

    def test_unsecured_file(self):
        conf = SecuredConfig('hello', 'world', filename='test.ini',
                             search_path='testdata')
        self.assertNotIn(join('testdata', 'test.ini'), conf.loaded_files)

    def test_secured_file(self):
        conf = SecuredConfig('hello', 'world', filename='secure.ini',
                             search_path='testdata')
        self.assertIn(join('testdata', 'secure.ini'), conf.loaded_files)

    def test_secured_nonexisting_file(self):
        conf = SecuredConfig('hello', 'world', filename='nonexisting.ini',
                             search_path='testdata')
        self.assertNotIn(join('testdata', 'nonexisting.ini'),
                         conf.loaded_files)

    def test_file_not_found_exception(self):
        with self.assertRaises(IOError):
            Config('hello', 'world', filename='nonexisting.ini',
                   search_path='testdata', require_load=True)

    def test_no_version_found_warning(self):
        with self.assertRaises(NoVersionError):
            Config('hello', 'world', search_path='testdata', version='1.1')

    def test_mismatching_major(self):
        logger = logging.getLogger('config_resolver')
        logger.setLevel(logging.DEBUG)
        catcher = TestableHandler()
        logger.addHandler(catcher)

        config = Config('hello', 'world', search_path='testdata/versioned',
                        version='1.1')
        catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            'Invalid major version number')
        catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            '2.1')
        catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            '1.1')

        # Values should not be loaded. Let's check if they really are missing.
        # They should be!
        self.assertFalse('section1' in config.sections())

        # Also, no files should be added to the "loaded_files" list.
        self.assertEqual(config.loaded_files, [])

    def test_mismatching_minor(self):
        logger = logging.getLogger('config_resolver')
        logger.setLevel(logging.DEBUG)
        catcher = TestableHandler()
        logger.addHandler(catcher)
        Config('hello', 'world', search_path='testdata/versioned',
               version='2.0')
        catcher.assert_contains(
            'config_resolver.hello.world',
            logging.WARNING,
            'Mismatching minor version number')
        catcher.assert_contains(
            'config_resolver.hello.world',
            logging.WARNING,
            '2.1')
        catcher.assert_contains(
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
        logger = logging.getLogger('config_resolver')
        logger.setLevel(logging.DEBUG)
        catcher = TestableHandler()
        logger.addHandler(catcher)
        Config('hello', 'world',
               filename='mismatch.ini',
               search_path='testdata/versioned:testdata/versioned2')
        catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            'Invalid major version number')
        catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            '1.0')
        catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            '2.0')

    def test_xdg_config_dirs(self):
        with environment(XDG_CONFIG_DIRS='/xdgpath1:/xdgpath2',
                         XDG_CONFIG_HOME=''):
            cfg = Config('foo', 'bar')
            self.assertEqual([
                '/etc/foo/bar/app.ini',
                '/xdgpath2/foo/bar/app.ini',
                '/xdgpath1/foo/bar/app.ini',
                expanduser('~/.foo/bar/app.ini'),
                expanduser('~/.config/foo/bar/app.ini'),
                abspath('.foo/bar/app.ini')
            ], cfg.active_path)

    def test_xdg_empty_config_dirs(self):
        with environment(XDG_CONFIG_DIRS='',
                         XDG_CONFIG_HOME=''):
            cfg = Config('foo', 'bar')
            self.assertEqual([
                '/etc/foo/bar/app.ini',
                '/etc/xdg/foo/bar/app.ini',
                expanduser('~/.foo/bar/app.ini'),
                expanduser('~/.config/foo/bar/app.ini'),
                abspath('.foo/bar/app.ini')
            ], cfg.active_path)

    def test_xdg_config_home(self):
        with environment(XDG_CONFIG_HOME='/path/to/config/home',
                         XDG_CONFIG_DIRS=''):
            cfg = Config('foo', 'bar')
            self.assertEqual([
                '/etc/foo/bar/app.ini',
                '/etc/xdg/foo/bar/app.ini',
                expanduser('~/.foo/bar/app.ini'),
                '/path/to/config/home/foo/bar/app.ini',
                abspath('.foo/bar/app.ini')
            ], cfg.active_path)

    def test_xdg_empty_config_home(self):
        with environment(XDG_CONFIG_HOME='',
                         XDG_CONFIG_DIRS=''):
            cfg = Config('foo', 'bar')
            self.assertEqual([
                '/etc/foo/bar/app.ini',
                '/etc/xdg/foo/bar/app.ini',
                expanduser('~/.foo/bar/app.ini'),
                expanduser('~/.config/foo/bar/app.ini'),
                abspath('.foo/bar/app.ini')
            ], cfg.active_path)

    def test_both_xdg_variables(self):
        with environment(XDG_CONFIG_DIRS='/xdgpath1:/xdgpath2',
                         XDG_CONFIG_HOME='/xdg/config/home'):
            cfg = Config('foo', 'bar')
            self.assertEqual([
                '/etc/foo/bar/app.ini',
                '/xdgpath2/foo/bar/app.ini',
                '/xdgpath1/foo/bar/app.ini',
                expanduser('~/.foo/bar/app.ini'),
                '/xdg/config/home/foo/bar/app.ini',
                abspath('.foo/bar/app.ini')
            ], cfg.active_path)

    @unittest.skipUnless(have_mock, "mock module is not available")
    def test_xdg_deprecation(self):
        """
        ~/.group/app/app.ini should issue a deprecation warning.

        NOTE: This is a *user* warning. Not a developer warning! So we'll use
        the logging module instead of the warnings module!
        """
        with patch('config_resolver.Config.check_file') as checker_mock:
            checker_mock.return_value = (True, "")
            logger = logging.getLogger('config_resolver')
            logger.setLevel(logging.DEBUG)
            catcher = TestableHandler()
            logger.addHandler(catcher)
            Config('hello', 'world')
            expected_message = (
                "DEPRECATION WARNING: The file '{home}/.hello/world/app.ini' "
                "was loaded. The XDG Basedir standard requires this file to "
                "be in '{home}/.config/hello/world/app.ini'! This location "
                "will no longer be parsed in a future version of "
                "config_resolver! You can already (and should) move the "
                "file!".format(
                    home=expanduser("~")))
            result = catcher.contains(
                'config_resolver',
                logging.WARNING,
                expected_message)
            self.assertTrue(result, "Expected log message: {!r} not found in "
                            "logger!".format(expected_message))


class Regressions(unittest.TestCase):

    def setUp(self):
        self.cfg = Config('hello', 'world', search_path='testdata')

    def test_multiple_log_prefixes(self):
        """
        The new log message prefixes are multiplied if more than one config
        instance is created!
        """
        Config('foo', 'bar')
        cfg = Config('foo', 'bar')
        self.assertEqual(len(cfg._log.filters), 1)


if __name__ == '__main__':
    unittest.main()
