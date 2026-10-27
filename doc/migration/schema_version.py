"""
Check the schema version while validating.
"""

from typing import Literal

from pydantic import BaseModel


class Feeder(BaseModel):
    capacity_g: int
    refill_hour: int = 6


class Config(BaseModel):
    # Bump on every incompatible change to the
    # file format. Older files fail validation.
    schema_version: Literal[2]
    feeder: Feeder


def check_version(data: dict) -> None:
    """The same check without pydantic."""
    version = data.get("schema_version")
    if version != 2:
        raise ValueError(
            f"schema_version {version!r} != 2"
        )
