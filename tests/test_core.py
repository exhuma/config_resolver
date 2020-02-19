import logging

import config_resolver.core as core


def test_readability_error(caplog):
    """
    If an exception occurs when checking the readability of a file, we don't
    want to crash out.
    """
    result = core.is_readable(
        core.ConfigID("acme", "myapp"),
        "tests/examples/broken.ini"
    )
    assert result.is_readable is False
    matching_logs = [
        msg for msg in caplog.messages
        if "broken.ini" in msg and "Unable to read" in msg
    ]
