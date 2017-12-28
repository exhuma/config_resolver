'''
Tests the default "INI" file handler.

This also includes the main functionality tests.
'''
from contextlib import contextmanager
import logging
import os
import re
import stat
import sys
import unittest
from os.path import expanduser, join, abspath
from textwrap import dedent

from config_resolver import (
    NoVersionError,
    from_string,
    get_config,
)
from config_resolver.handler import ini, json


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


class CommonTests:
    HANDLER_CLASS = None
    TEST_FILENAME = 'test.ini'
    APP_FILENAME = 'app.ini'
    SECURE_FILENAME = 'secure.ini'
    DATA_PATH = 'testdata/ini'
    MISMATCH_FILENAME = 'mismatch.json'
    TEST_STRING = dedent(
        '''\
        [section_mem]
        val = 1
        '''
    )

    def setUp(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        self.catcher = TestableHandler()
        logger.addHandler(self.catcher)

    def tearDown(self):
        self.catcher.reset()

    def test_from_string(self):
        result = from_string(self.TEST_STRING, handler=self.HANDLER_CLASS)
        config = result.config
        self.assertTrue(config.has_section('section_mem'))
        self.assertEqual(self._get(config, 'section_mem', 'val'), '1')

    def test_simple_init(self):
        '''
        If we find a file named ``app.ini`` in ``search_path``, we load that.
        '''
        result = get_config('hello', 'world', {'search_path': self.DATA_PATH},
                            handler=self.HANDLER_CLASS)
        config = result.config
        self.assertTrue(config.has_section('section1'))

    def test_get(self):
        result = get_config('hello', 'world', {'search_path': self.DATA_PATH},
                            handler=self.HANDLER_CLASS)
        config = result.config
        self.assertEqual(self._get(config, 'section1', 'var1'), 'foo')
        self.assertEqual(self._get(config, 'section1', 'var2'), 'bar')
        self.assertEqual(self._get(config, 'section2', 'var1'), 'baz')

    def test_no_option_error(self):
        result = get_config('hello', 'world', {'search_path': self.DATA_PATH},
                            handler=self.HANDLER_CLASS)
        config = result.config
        self.assertIs(self._get(config, 'section1', 'b', default=None), None)

    def test_no_section_error(self):
        result = get_config('hello', 'world', {'search_path': self.DATA_PATH},
                            handler=self.HANDLER_CLASS)
        config = result.config
        self.assertIs(self._get(config, 'a', 'b', default=None), None)

    def test_env_name(self):
        with environment(HELLO_WORLD_FILENAME=self.TEST_FILENAME,
                         XDG_CONFIG_HOME='',
                         XDG_CONFIG_DIRS=''):
            result = get_config('hello', 'world', handler=self.HANDLER_CLASS)
        expected = ['/etc/hello/world/%s' % self.TEST_FILENAME,
                    '/etc/xdg/hello/world/%s' % self.TEST_FILENAME,
                    expanduser('~/.config/hello/world/%s' % self.TEST_FILENAME),
                    '{}/.hello/world/{}'.format(os.getcwd(), self.TEST_FILENAME)]
        self.assertEqual(
            result.meta.active_path,
            expected)

    def test_env_name_override(self):
        with environment(HELLO_WORLD_FILENAME=self.TEST_FILENAME):
            get_config('hello', 'world', handler=self.HANDLER_CLASS)
        msg = ("filename was overridden with '%s' by the environment "
               "variable HELLO_WORLD_FILENAME" % self.TEST_FILENAME)
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)

    def test_env_path(self):
        path = '{0}:{0}/a:{0}/b'.format(self.DATA_PATH)
        with environment(HELLO_WORLD_PATH=path):
            result = get_config('hello', 'world', handler=self.HANDLER_CLASS)
        expected = ['%s/%s' % (self.DATA_PATH, self.APP_FILENAME),
                    '%s/a/%s' % (self.DATA_PATH, self.APP_FILENAME),
                    '%s/b/%s' % (self.DATA_PATH, self.APP_FILENAME)]
        self.assertEqual(
            result.meta.active_path,
            expected)

    def test_env_path_override_log(self):
        path = '{0}:{0}/a:{0}/b'.format(self.DATA_PATH)
        with environment(HELLO_WORLD_PATH=path):
            get_config('hello', 'world', handler=self.HANDLER_CLASS)
        msg = ("overridden with '%s' by the "
               "environment variable 'HELLO_WORLD_PATH'") % path
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)

    def test_env_path_add(self):
        path = '+{0}:{0}/a:{0}/b'.format(self.DATA_PATH)
        with environment(HELLO_WORLD_PATH=path,
                         XDG_CONFIG_HOME='',
                         XDG_CONFIG_DIRS=''):
            result = get_config('hello', 'world', handler=self.HANDLER_CLASS)
        expected = [
            '/etc/hello/world/%s' % self.APP_FILENAME,
            '/etc/xdg/hello/world/%s' % self.APP_FILENAME,
            expanduser('~/.config/hello/world/%s' % self.APP_FILENAME),
            '%s/.hello/world/%s' % (os.getcwd(), self.APP_FILENAME),
            '%s/%s' % (self.DATA_PATH, self.APP_FILENAME),
            '%s/a/%s' % (self.DATA_PATH, self.APP_FILENAME),
            '%s/b/%s' % (self.DATA_PATH, self.APP_FILENAME)
        ]
        self.assertEqual(
            result.meta.active_path,
            expected)

    def test_env_path_add_log(self):
        path = '+{0}:{0}/a:{0}/b'.format(self.DATA_PATH)
        with environment(HELLO_WORLD_PATH=path):
            get_config('hello', 'world', handler=self.HANDLER_CLASS)
        msg = ("extended with '%s' by the "
               "environment variable HELLO_WORLD_PATH") % path
        self.catcher.assert_contains(
            'config_resolver.hello.world',
            logging.INFO,
            msg)

    def test_search_path(self):
        result = get_config('hello', 'world',
                            {'search_path': '{0}:{0}/a:{0}/b'.format(self.DATA_PATH)},
                            handler=self.HANDLER_CLASS)
        config = result.config
        self.assertEqual(self._get(config, 'section3', 'var1'), 'Hello World!')
        self.assertEqual(self._get(config, 'section1', 'var1'), 'frob')
        self.assertEqual(
            result.meta.loaded_files,
            [
                '%s/%s' % (self.DATA_PATH, self.APP_FILENAME),
                '%s/a/%s' % (self.DATA_PATH, self.APP_FILENAME),
                '%s/b/%s' % (self.DATA_PATH, self.APP_FILENAME),
            ])

    def test_filename(self):
        result = get_config('hello', 'world',
                            {
                                'filename': self.TEST_FILENAME,
                                'search_path': self.DATA_PATH,
                            },
                            handler=self.HANDLER_CLASS)
        self.assertEqual(self._get(result.config, 'section2', 'var1'), 'baz')

    def test_app_group_name(self):
        result = get_config('hello', 'world', handler=self.HANDLER_CLASS)
        self.assertEqual(result.meta.config_id.group, 'hello')
        self.assertEqual(result.meta.config_id.app, 'world')

    def test_unsecured_logmessage(self):
        logger = logging.getLogger('config_resolver')
        logger.setLevel(logging.DEBUG)
        catcher = TestableHandler()
        logger.addHandler(catcher)
        get_config(
            'hello', 'world',
            {
                'filename': self.TEST_FILENAME,
                'search_path': self.DATA_PATH,
                'secure': True,
            },
            handler=self.HANDLER_CLASS)
        expected_message = (
            "File '%s/%s' is not secure enough. "
            "Change it's mode to 600" % (self.DATA_PATH, self.TEST_FILENAME))
        catcher.assert_contains(
            'config_resolver.hello.world',
            logging.WARNING,
            expected_message)

    def test_unsecured_file(self):
        result = get_config('hello', 'world',
                            {
                                'filename': self.TEST_FILENAME,
                                'search_path': self.DATA_PATH,
                                'secure': True,
                            },
                            handler=self.HANDLER_CLASS)
        self.assertNotIn(join(self.DATA_PATH, self.TEST_FILENAME), result.meta.loaded_files)

    def test_secured_file(self):
        # make sure the file is secured. This information is lost through git so
        # we need to set it here manually. Also, this is only available on *nix,
        # so we need to skip if necessary
        if sys.platform not in ('linux', 'linux2'):
            self.skipTest('Only runnable on *nix')

        path = join(self.DATA_PATH, self.SECURE_FILENAME)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

        result = get_config('hello', 'world',
                            {
                                'filename': self.SECURE_FILENAME,
                                'search_path': self.DATA_PATH,
                                'secure': True,
                            },
                            handler=self.HANDLER_CLASS)
        self.assertIn(path, result.meta.loaded_files)

    def test_secured_nonexisting_file(self):
        result = get_config('hello', 'world',
                            {
                                'filename': 'nonexisting.ini',
                                'search_path': self.DATA_PATH,
                                'secure': True,
                            },
                            handler=self.HANDLER_CLASS)
        self.assertNotIn(join(self.DATA_PATH, 'nonexisting.ini'),
                         result.meta.loaded_files)

    def test_file_not_found_exception(self):
        with self.assertRaises(IOError):
            get_config('hello', 'world',
                       {
                           'filename': 'nonexisting.ini',
                           'search_path': self.DATA_PATH,
                           'require_load': True,
                       },
                       handler=self.HANDLER_CLASS)

    def test_no_version_found_warning(self):
        with self.assertRaises(NoVersionError):
            get_config('hello', 'world',
                       {
                           'search_path': self.DATA_PATH,
                           'version': '1.1',
                       },
                       handler=self.HANDLER_CLASS)

    def test_mismatching_major(self):
        result = get_config('hello', 'world',
                            {
                                'search_path': '%s/versioned' % self.DATA_PATH,
                                'version': '1.1',
                            },
                            handler=self.HANDLER_CLASS)
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

        config = result.config
        meta = result.meta
        # Values should not be loaded. Let's check if they really are missing.
        # They should be!
        self.assertFalse('section1' in self._sections(config))

        # Also, no files should be added to the "loaded_files" list.
        self.assertEqual(meta.loaded_files, [])

    def test_mismatching_minor(self):
        get_config('hello', 'world',
                   {
                       'search_path': '%s/versioned' % self.DATA_PATH,
                       'version': '2.0',
                   },
                   handler=self.HANDLER_CLASS)
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
        get_config('hello', 'world',
                   {
                    'filename': self.MISMATCH_FILENAME,
                    'search_path': '{0}/versioned:{0}/versioned2'.format(self.DATA_PATH),
                   },
                   handler=self.HANDLER_CLASS)
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
            result = get_config('foo', 'bar', handler=self.HANDLER_CLASS)
            self.assertEqual([
                '/etc/foo/bar/%s' % self.APP_FILENAME,
                '/xdgpath2/foo/bar/%s' % self.APP_FILENAME,
                '/xdgpath1/foo/bar/%s' % self.APP_FILENAME,
                expanduser('~/.config/foo/bar/%s' % self.APP_FILENAME),
                abspath('.foo/bar/%s' % self.APP_FILENAME)
            ], result.meta.active_path)

    def test_xdg_empty_config_dirs(self):
        with environment(XDG_CONFIG_DIRS='',
                         XDG_CONFIG_HOME=''):
            result = get_config('foo', 'bar', handler=self.HANDLER_CLASS)
            self.assertEqual([
                '/etc/foo/bar/%s' % self.APP_FILENAME,
                '/etc/xdg/foo/bar/%s' % self.APP_FILENAME,
                expanduser('~/.config/foo/bar/%s' % self.APP_FILENAME),
                abspath('.foo/bar/%s' % self.APP_FILENAME)
            ], result.meta.active_path)

    def test_xdg_config_home(self):
        with environment(XDG_CONFIG_HOME='/path/to/config/home',
                         XDG_CONFIG_DIRS=''):
            result = get_config('foo', 'bar', handler=self.HANDLER_CLASS)
            self.assertEqual([
                '/etc/foo/bar/%s' % self.APP_FILENAME,
                '/etc/xdg/foo/bar/%s' % self.APP_FILENAME,
                '/path/to/config/home/foo/bar/%s' % self.APP_FILENAME,
                abspath('.foo/bar/%s' % self.APP_FILENAME)
            ], result.meta.active_path)

    def test_xdg_empty_config_home(self):
        with environment(XDG_CONFIG_HOME='',
                         XDG_CONFIG_DIRS=''):
            result = get_config('foo', 'bar', handler=self.HANDLER_CLASS)
            self.assertEqual([
                '/etc/foo/bar/%s' % self.APP_FILENAME,
                '/etc/xdg/foo/bar/%s' % self.APP_FILENAME,
                expanduser('~/.config/foo/bar/%s' % self.APP_FILENAME),
                abspath('.foo/bar/%s' % self.APP_FILENAME)
            ], result.meta.active_path)

    def test_both_xdg_variables(self):
        with environment(XDG_CONFIG_DIRS='/xdgpath1:/xdgpath2',
                         XDG_CONFIG_HOME='/xdg/config/home'):
            result = get_config('foo', 'bar', handler=self.HANDLER_CLASS)
            self.assertEqual([
                '/etc/foo/bar/%s' % self.APP_FILENAME,
                '/xdgpath2/foo/bar/%s' % self.APP_FILENAME,
                '/xdgpath1/foo/bar/%s' % self.APP_FILENAME,
                '/xdg/config/home/foo/bar/%s' % self.APP_FILENAME,
                abspath('.foo/bar/%s' % self.APP_FILENAME)
            ], result.meta.active_path)

    def test_filename_in_log_minor(self):
        """
        When getting a version number mismatch, the filename should be logged!
        """
        get_config('hello', 'world',
                   {
                       'search_path': '%s/versioned' % self.DATA_PATH,
                       'version': '2.0'
                   },
                   handler=self.HANDLER_CLASS)
        self.catcher.assert_contains_regex(
            'config_resolver.hello.world',
            logging.WARNING,
            '%s/versioned/%s' % (self.DATA_PATH, self.APP_FILENAME))

    def test_filename_in_log_major(self):
        """
        When getting a version number mismatch, the filename should be logged!
        """
        get_config('hello', 'world',
                   {
                       'search_path': '%s/versioned' % self.DATA_PATH,
                       'version': '5.0',
                   },
                   handler=self.HANDLER_CLASS)
        self.catcher.assert_contains_regex(
            'config_resolver.hello.world',
            logging.ERROR,
            '%s/versioned/%s' % (self.DATA_PATH, self.APP_FILENAME))


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

    def _get(self, config, section, option, default=None):
        return config.get(section, option, fallback=default)

    def _sections(self, config):
        return set(config.sections())


class JsonTest(CommonTests, unittest.TestCase):
    HANDLER_CLASS = json
    TEST_FILENAME = 'test.json'
    APP_FILENAME = 'app.json'
    DATA_PATH = 'testdata/json'
    SECURE_FILENAME = 'secure.json'
    MISMATCH_FILENAME = 'mismatch.json'
    TEST_STRING = dedent(
        '''\
        {
            "section_mem": {
                "val": 1
            }
        }
        '''
    )

    def _get(self, config, section, option, default=None):
        if section not in config or option not in config[section]:
            return default
        return config[section][option]

    def _sections(self, config):
        return set(config.keys())

    def test_from_string(self):
        self.skipTest('The test-code is currenty no compatible with JSON files')


if __name__ == '__main__':
    unittest.main()
