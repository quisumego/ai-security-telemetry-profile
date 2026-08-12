"""Shared fixtures: locate and load the M0 schema artefacts."""

import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

GROUPS = ("session", "turn", "content", "retrieval", "action", "control")
TIERS = ("required", "recommended", "optional", "not_required")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def register() -> dict:
    """The field register, schema/fields.yaml."""
    with (REPO_ROOT / "schema" / "fields.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="session")
def fields(register: dict) -> list[dict]:
    return register["fields"]


@pytest.fixture(scope="session")
def event_schema() -> dict:
    """The JSON Schema for a single event."""
    with (REPO_ROOT / "schema" / "event.schema.json").open(encoding="utf-8") as fh:
        return json.load(fh)
