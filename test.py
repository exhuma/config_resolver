import logging
import os
import re
import stat
import sys
import unittest
from contextlib import contextmanager
from os.path import abspath, expanduser, join
from textwrap import dedent
from warnings import catch_warnings

from config_resolver import (Config, NoOptionError, NoSectionError,
                             NoVersionError, SecuredConfig, get_config)

from config_resolver.core import ConfigID

try:
    from mock import patch
    have_mock = True
except ImportError:
    try:
        from unittest.mock import patch
        have_mock = True
    except ImportError:
        have_mock = False



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
            level = logging.getLevelName(level)
            raise AssertionError(msg % (logger, needle, level))

    def assert_contains_regex(self, logger, level, needle):
        if not self.contains(logger, level, needle, is_regex=True):
            msg = '%s did not contain a message matching %r and level %r'
            level = logging.getLevelName(level)
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


class TestBase(unittest.TestCase):
    '''
    A superclass for tests to make use of the TestableHandler class in each
    test.

    This would be easier using the pytest caplog fixture, but this would entail
    too many code changes and conflicts down the line.
    '''

    def setUp(self):
        logger = logging.getLogger('config_resolver')
        logger.setLevel(logging.DEBUG)
        self.catcher = TestableHandler()
        logger.addHandler(self.catcher)
        def remove_handler():
            logger.removeHandler(self.catcher)
        self.addCleanup(remove_handler)



@unittest.skipUnless(sys.version_info > (3, 0), 'Test only valid in Python 2')
class SimpleInitFromContent(TestBase):
    '''
    Tests loading a config string from memory
    '''

    def setUp(self):
        super(SimpleInitFromContent, self).setUp()
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


class SimpleInitTest(TestBase):

    def setUp(self):
        super(SimpleInitTest, self).setUp()
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


class AdvancedInitTest(TestBase):

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
        Config('hello', 'world')
        msg = ("filename was overridden with 'test.ini' by the environment "
               "variable HELLO_WORLD_FILENAME")
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)

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
        os.environ['HELLO_WORLD_PATH'] = 'testdata:testdata/a:testdata/b'
        Config('hello', 'world')
        msg = ("overridden with 'testdata:testdata/a:testdata/b' by the "
               "environment variable 'HELLO_WORLD_PATH'")
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)

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
        os.environ['HELLO_WORLD_PATH'] = '+testdata:testdata/a:testdata/b'
        Config('hello', 'world')
        msg = ("extended with ['testdata', 'testdata/a', 'testdata/b'] by the "
               "environment variable HELLO_WORLD_PATH")
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)

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


class FunctionalityTests(TestBase):

    def test_mandatory_section(self):
        config = Config('hello', 'world', search_path='testdata')
        with self.assertRaises(NoSectionError):
            config.get('nosuchsection', 'nosuchoption')

    def test_mandatory_option(self):
        config = Config('hello', 'world', search_path='testdata')
        with self.assertRaises(NoOptionError):
            config.get('section1', 'nosuchoption')

    def test_unsecured_logmessage(self):
        SecuredConfig('hello', 'world', filename='test.ini',
                      search_path='testdata')
        expected_message = (
            "File 'testdata/test.ini' is not secure enough. "
            "Change it's mode to 600")
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.WARNING,
            expected_message)

    def test_unsecured_file(self):
        conf = SecuredConfig('hello', 'world', filename='test.ini',
                             search_path='testdata')
        self.assertNotIn(join('testdata', 'test.ini'), conf.loaded_files)

    def test_secured_file(self):
        # make sure the file is secured. This information is lost through git so
        # we need to set it here manually. Also, this is only available on *nix,
        # so we need to skip if necessary
        if sys.platform != 'linux':
            self.skipTest('Only runnable on *nix')

        path = join('testdata', 'secure.ini')
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

        conf = SecuredConfig('hello', 'world', filename='secure.ini',
                             search_path='testdata')
        self.assertIn(path, conf.loaded_files)

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
        config = Config('hello', 'world', search_path='testdata/versioned',
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
        Config('hello', 'world', search_path='testdata/versioned',
               version='2.3')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            'Mismatching minor version number')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            '2.3')
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.ERROR,
            '2.1')

    def test_mixed_version_load(self):
        """
        If the instance has no version assigned, the first file which contains a
        version should "lock in" that version. This is to avoid mixed config
        files even if the application did not explicitly request a version
        number!
        """
        Config('hello', 'world',
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
        with patch('config_resolver.core.Config.check_file') as checker_mock:
            checker_mock.return_value = (True, "")
            Config('hello', 'world')
            expected_message = (
                "DEPRECATION WARNING: The file '{home}/.hello/world/app.ini' "
                "was loaded. The XDG Basedir standard requires this file to "
                "be in '{home}/.config/hello/world/app.ini'! This location "
                "will no longer be parsed in a future version of "
                "config_resolver! You can already (and should) move the "
                "file!".format(
                    home=expanduser("~")))
            self.catcher.assert_contains(
                'config_resolver.hello.world',
                logging.WARNING,
                expected_message)

    def test_filename_in_log_minor(self):
        """
        When getting a version number mismatch, the filename should be logged!
        """
        Config('hello', 'world', search_path='testdata/versioned',
               version='2.3')
        self.catcher.assert_contains_regex(
            'config_resolver.hello.world',
            logging.ERROR,
            'testdata/versioned/app.ini')

    def test_filename_in_log_major(self):
        """
        When getting a version number mismatch, the filename should be logged!
        """
        Config('hello', 'world', search_path='testdata/versioned',
               version='5.0')
        self.catcher.assert_contains_regex(
            'config_resolver.hello.world',
            logging.ERROR,
            'testdata/versioned/app.ini')

    def test_check_file_errored(self):
        """
        IF a file is unreadable as config, we want to skip it without crashing
        """
        with patch("config_resolver.core.exists") as exists:
            exists.return_value = True
            cfg = Config('hello', 'world', search_path='testdata/versioned',
                         version='5.0')
            result = cfg.check_file("testdata/broken.ini")
            self.assertFalse(result)


class Regressions(TestBase):

    def setUp(self):
        super(Regressions, self).setUp()
        self.cfg = Config('hello', 'world', search_path='testdata')

    def test_multiple_log_prefixes(self):
        """
        The new log message prefixes are multiplied if more than one config
        instance is created!
        """
        Config('foo', 'bar')
        cfg = Config('foo', 'bar')
        self.assertEqual(len(cfg._log.filters), 1)


class ConfigResolver5Transition(TestBase):
    '''
    To make upgrading to 5.0 easier, we will add a transition layer. This
    test-case tests that the transition layer calls the old constructor
    properly and emit appropriate deprecation warnings.

    We can implement this easily as the main entry-point changes from
    ``config_resolver.Config`` to ``config_resolver.get_config``.
    '''

    def test_ignore_handler(self):
        '''
        Version 5 will accept a new "handler" argument. This should be
        accepted, but ignored in version 4.
        '''
        with patch('config_resolver.core.Config') as mck:
            get_config('foo', 'bar', lookup_options={}, handler='dummy_handler')
            get_config('foo', 'bar', lookup_options={}, handler='dummy_handler')
        mck.assert_called_with(
            'bar', 'foo',
            filename='config.ini',
            require_load=False,
            search_path=None,
            version=None)

    def test_search_path(self):
        '''
        ``search_path`` should be taken from ``lookup_options``
        '''
        with patch('config_resolver.core.Config') as mck:
            get_config('world', 'hello', lookup_options={
                'search_path': 'testdata:testdata/a:testdata/b'
            })
        mck.assert_called_with(
            'hello', 'world',
            filename='config.ini',
            require_load=False,
            search_path='testdata:testdata/a:testdata/b',
            version=None)

    def test_filename(self):
        '''
        ``filename`` should be taken from ``lookup_options``
        '''
        with patch('config_resolver.core.Config') as mck:
            cfg_b = get_config('world', 'hello', filename='test.ini')
        mck.assert_called_with('hello', 'world',
            filename='test.ini',
            require_load=False,
            search_path=None,
            version=None)

        with patch('config_resolver.core.Config') as mck:
            cfg_b = get_config('world', 'hello', lookup_options={
                'filename': 'test.ini'
            })

        mck.assert_called_with('hello', 'world',
            filename='test.ini',
            require_load=False,
            search_path=None,
            version=None)

    def test_new_default_filename(self):
        '''
        In config_resolver 5 we will switch to "config.ini" from "app.ini".

        We want the transition-layer to continue working as usual
        '''
        with patch('config_resolver.core.Config') as mck:
            cfg_b = get_config('world', 'hello')
        mck.assert_called_with('hello', 'world',
            filename='config.ini',
            require_load=False,
            search_path=None,
            version=None)

    def test_secured_config(self):
        with patch('config_resolver.core.SecuredConfig') as mck:
            cfg_b = get_config('world', 'hello', lookup_options={
                'secure': True
            })
        mck.assert_called_with('hello', 'world',
            filename='config.ini',
            require_load=False,
            search_path=None,
            version=None)

    def test_return_value(self):
        with patch('config_resolver.core.Config') as mck:
            cfg, meta = get_config('world', 'hello')
            self.assertEqual(cfg, mck())

        self.assertEqual(meta.loaded_files, mck()._loaded_files)
        self.assertEqual(meta.active_path, mck()._active_path)

    def test_no_warning(self):
        """
        If we receive a call via "get_config" we should *not* raise a warning
        """
        with catch_warnings(record=True) as warnings:
            cfg, meta = get_config('world', 'hello')

        my_warnings = [wrn for wrn in warnings if 'get_config' in str(wrn)]
        self.assertEqual(
            len(my_warnings),
            0,
            "We should not have seen a warning from this call")


if __name__ == '__main__':
    unittest.main()
