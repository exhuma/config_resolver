"""
Settings for a containerised service.
"""

import sys

from pydantic import (
    BaseModel,
    SecretStr,
    ValidationError,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Database(BaseModel):
    host: str
    port: int = 5432


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MYAPP_",
        env_nested_delimiter="__",
        secrets_dir="/run/secrets",
    )

    debug: bool = False
    database: Database
    db_password: SecretStr


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        sys.exit(f"Invalid configuration:\n{exc}")
