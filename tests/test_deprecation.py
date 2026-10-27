"""
Tests for the end-of-life deprecation warning.
"""

import inspect
import subprocess
import sys
import warnings

import pytest

import config_resolver
from config_resolver import (
    ConfigResolverDeprecationWarning,
    from_string,
    get_config,
)

SEARCH_PATH = {"search_path": "tests/examples/configs"}


def _caller_line() -> int:
    """
    Return the line number of the line that called this helper.
    """
    return inspect.currentframe().f_back.f_lineno


def test_get_config_warns():
    """
    Ensure get_config emits ConfigResolverDeprecationWarning.
    """
    with pytest.warns(ConfigResolverDeprecationWarning):
        get_config("myapp", "acme", SEARCH_PATH)


def test_from_string_warns():
    """
    Ensure from_string emits ConfigResolverDeprecationWarning.
    """
    with pytest.warns(ConfigResolverDeprecationWarning):
        from_string("[section]\nvar = value\n")


def test_get_config_warning_points_at_caller():
    """
    Ensure the get_config warning is attributed to the calling line.
    """
    with pytest.warns(ConfigResolverDeprecationWarning) as record:
        line = _caller_line() + 1
        get_config("myapp", "acme", SEARCH_PATH)
    assert (record[0].filename, record[0].lineno) == (__file__, line)


def test_from_string_warning_points_at_caller():
    """
    Ensure the from_string warning is attributed to the calling line.
    """
    with pytest.warns(ConfigResolverDeprecationWarning) as record:
        line = _caller_line() + 1
        from_string("[section]\nvar = value\n")
    assert (record[0].filename, record[0].lineno) == (__file__, line)


def test_warning_links_to_documentation():
    """
    Ensure the warning message points users to the migration docs.
    """
    with pytest.warns(
        ConfigResolverDeprecationWarning,
        match=r"https://config-resolver\.readthedocs\.io/",
    ):
        from_string("")


def test_warning_is_a_deprecation_warning():
    """
    Ensure existing DeprecationWarning filters also match the new warning.
    """
    assert issubclass(ConfigResolverDeprecationWarning, DeprecationWarning)


def test_warning_is_exported_from_exc():
    """
    Ensure the warning class is the one defined in config_resolver.exc.
    """
    assert (
        config_resolver.ConfigResolverDeprecationWarning
        is config_resolver.exc.ConfigResolverDeprecationWarning
    )


def test_import_does_not_warn():
    """
    Ensure importing the package emits no warning, even with -W error.
    """
    result = subprocess.run(
        [sys.executable, "-W", "error", "-c", "import config_resolver"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_documented_filter_silences_warning():
    """
    Ensure the filter shown in doc/migration.rst silences the warning.
    """
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        warnings.filterwarnings(
            "ignore",
            category=ConfigResolverDeprecationWarning,
        )
        from_string("")
    assert record == []
