"""
Run the code snippets from doc/migration.rst.

The snippets use third-party libraries that config_resolver does not depend
on. Each test is skipped unless its libraries are installed. To run them all:

    uv run --isolated --no-project --with pytest --with packaging \
        --with pydantic-settings --with platformdirs \
        pytest -o addopts="" tests/test_migration_snippets.py
"""

import importlib.util
import os
from pathlib import Path

import pytest

SNIPPETS = Path(__file__).parent.parent / "doc" / "migration"


def load_snippet(name):
    """
    Import doc/migration/<name>.py as a module.
    """
    spec = importlib.util.spec_from_file_location(
        "snippet_" + name, SNIPPETS / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def xdg(tmp_path, monkeypatch):
    """
    Point the XDG variables and the working directory into *tmp_path*.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_DIRS", str(tmp_path / "site"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_service_settings_from_env_and_secrets(tmp_path, monkeypatch):
    """
    Ensure settings come from prefixed env vars and the secrets directory.
    """
    pytest.importorskip("pydantic_settings")
    snippet = load_snippet("service_settings")
    monkeypatch.setenv("MYAPP_DEBUG", "true")
    monkeypatch.setenv("MYAPP_DATABASE__HOST", "db")
    monkeypatch.setenv("MYAPP_DATABASE__PORT", "6543")
    write(tmp_path / "myapp_db_password", "s3cret")

    settings = snippet.Settings(_secrets_dir=tmp_path)

    assert (
        settings.debug,
        settings.database.host,
        settings.database.port,
        settings.db_password.get_secret_value(),
    ) == (True, "db", 6543, "s3cret")
    assert "s3cret" not in repr(settings)


def test_service_settings_fail_fast(monkeypatch):
    """
    Ensure missing required settings stop the program with a message.
    """
    pytest.importorskip("pydantic_settings")
    snippet = load_snippet("service_settings")
    for name in list(os.environ):
        if name.startswith("MYAPP_"):
            monkeypatch.delenv(name)

    with pytest.warns(UserWarning, match="/run/secrets"):
        with pytest.raises(SystemExit, match="database"):
            snippet.load_settings()


def test_ini_files_cascade(xdg):
    """
    Ensure later INI files override earlier ones and are reported in order.
    """
    snippet = load_snippet("ini_files")
    site = write(
        xdg / "site/acme/app/app.ini", "[s]\nvar = site\nother = x\n"
    )
    home = write(xdg / "home/acme/app/app.ini", "[s]\nvar = home\n")
    local = write(xdg / ".acme/app/app.ini", "[s]\nvar = local\n")

    config, loaded = snippet.load_config("acme", "app")

    assert (config["s"]["var"], config["s"]["other"]) == ("local", "x")
    assert loaded == [str(site), str(home), str(local)]


def test_ini_files_none_found(xdg):
    """
    Ensure a missing config is an error, not an empty config.
    """
    snippet = load_snippet("ini_files")
    with pytest.raises(FileNotFoundError):
        snippet.load_config("acme", "app")


def test_cli_config_cascade(xdg, monkeypatch):
    """
    Ensure site, user and explicit TOML files merge in that order.
    """
    pytest.importorskip("platformdirs")
    snippet = load_snippet("cli_config")
    site = write(
        xdg / "site/bird-feeder/config.toml",
        "[feeder]\ncapacity_g = 500\nrefill_hour = 6\n",
    )
    user = write(
        xdg / "home/bird-feeder/config.toml",
        "[feeder]\ncapacity_g = 750\n",
    )
    explicit = write(xdg / "explicit.toml", "[feeder]\nrefill_hour = 7\n")
    monkeypatch.setenv("BIRD_FEEDER_CONFIG", str(explicit))

    config, loaded = snippet.load_config()

    assert config == {"feeder": {"capacity_g": 750, "refill_hour": 7}}
    assert loaded == [site, user, explicit]


def test_cli_config_missing_explicit_file(xdg):
    """
    Ensure an explicitly requested file that does not exist is an error.
    """
    pytest.importorskip("platformdirs")
    snippet = load_snippet("cli_config")
    with pytest.raises(FileNotFoundError):
        snippet.load_config(str(xdg / "nope.toml"))


def test_schema_version_accepts_current():
    """
    Ensure a config with the expected schema version validates.
    """
    pytest.importorskip("pydantic")
    snippet = load_snippet("schema_version")
    config = snippet.Config.model_validate(
        {"schema_version": 2, "feeder": {"capacity_g": 500}}
    )
    assert config.feeder.capacity_g == 500


def test_schema_version_rejects_old():
    """
    Ensure a config with another schema version fails validation.
    """
    pydantic = pytest.importorskip("pydantic")
    snippet = load_snippet("schema_version")
    with pytest.raises(pydantic.ValidationError):
        snippet.Config.model_validate(
            {"schema_version": 1, "feeder": {"capacity_g": 500}}
        )


def test_schema_version_plain_check():
    """
    Ensure the check without pydantic rejects another version.
    """
    pytest.importorskip("pydantic")
    snippet = load_snippet("schema_version")
    with pytest.raises(ValueError, match="2"):
        snippet.check_version({"schema_version": 1})


def test_private_file_accepts_0600(tmp_path):
    """
    Ensure a 0600 file owned by the current user passes.
    """
    snippet = load_snippet("private_file")
    path = write(tmp_path / "app.ini", "")
    path.chmod(0o600)
    snippet.check_private(path)


def test_private_file_rejects_group_readable(tmp_path):
    """
    Ensure a group-readable file is rejected.
    """
    snippet = load_snippet("private_file")
    path = write(tmp_path / "app.ini", "")
    path.chmod(0o640)
    with pytest.raises(PermissionError, match="0600"):
        snippet.check_private(path)


@pytest.mark.skipif(os.getuid() == 0, reason="root owns the test file")
def test_private_file_rejects_foreign_owner(tmp_path, monkeypatch):
    """
    Ensure a 0600 file owned by another (non-root) user is rejected.
    """
    snippet = load_snippet("private_file")
    path = write(tmp_path / "app.ini", "")
    path.chmod(0o600)
    monkeypatch.setattr(snippet.os, "getuid", lambda: path.stat().st_uid + 1)
    with pytest.raises(PermissionError, match="owned"):
        snippet.check_private(path)
