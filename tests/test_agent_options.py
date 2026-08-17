"""Session assembly: the overlay, and the extended thinking override.

Neither makes a model call. Both exist so a setting can be varied under
otherwise identical conditions, which is what M2 needs to put scenario
documents in front of the agent without touching lab/corpus/.
"""

from pathlib import Path

import pytest

from lab.agent import build_options, build_session
from lab.config import load_config
from lab.tools import QUALIFIED_TOOL_NAMES, SERVER_NAME

FIXTURE = """---
id: zz-test-overlay-001
title: Throwaway overlay document
doc_type: third_party_correspondence
tenant: thornfield-mutual
provenance: external_supplied
scope: claims_handler
---

A document that exists only for this test. It mentions kestrel plinth
quantifier, a phrase that appears nowhere in the corpus.
"""


@pytest.fixture
def overlay(tmp_path: Path) -> Path:
    d = tmp_path / "overlay"
    d.mkdir()
    (d / "zz-test-overlay-001.md").write_text(FIXTURE, encoding="utf-8")
    return d


@pytest.fixture
def config():
    return load_config()


# ------------------------------------------------------------------ overlay --


def test_a_session_without_an_overlay_sees_only_the_corpus(config, tmp_path):
    session = build_session(config, tmp_path / "run", "s-test")
    try:
        assert len(session.index.documents) == 24
        assert not session.index.search("kestrel plinth quantifier", 5)
    finally:
        session.emitter.close()


def test_an_overlay_document_joins_the_index_and_is_retrievable(config, tmp_path, overlay):
    session = build_session(config, tmp_path / "run", "s-test", overlay_dirs=(overlay,))
    try:
        assert len(session.index.documents) == 25
        assert "zz-test-overlay-001" in session.index.documents
        hits = session.index.search("kestrel plinth quantifier", 5)
        assert hits and hits[0].document.id == "zz-test-overlay-001"
    finally:
        session.emitter.close()


def test_an_overlay_does_not_touch_the_corpus_on_disk(config, tmp_path, overlay):
    """The overlay is an index-time addition, not a write into lab/corpus/."""
    from lab.config import CORPUS_DIR

    before = sorted(p.name for p in CORPUS_DIR.glob("*.md"))
    session = build_session(config, tmp_path / "run", "s-test", overlay_dirs=(overlay,))
    session.emitter.close()
    assert sorted(p.name for p in CORPUS_DIR.glob("*.md")) == before


# ----------------------------------------------------------------- thinking --


def _options(config, tmp_path, thinking):
    session = build_session(config, tmp_path / "run", "s-test")
    try:
        server = {"type": "sdk", "name": SERVER_NAME, "instance": None}
        return build_options(config, session, server, [], thinking=thinking)
    finally:
        session.emitter.close()


def test_the_thinking_override_can_disable_it(config, tmp_path):
    options = _options(config, tmp_path, "disabled")
    assert options.thinking == {"type": "disabled"}


def test_the_thinking_override_can_leave_it_enabled(config, tmp_path):
    """Anything other than "disabled" leaves the SDK default in force."""
    options = _options(config, tmp_path, "enabled")
    assert options.thinking is None


def test_omitting_the_override_takes_the_configured_value(config, tmp_path):
    options = _options(config, tmp_path, None)
    expected = {"type": "disabled"} if config.thinking == "disabled" else None
    assert options.thinking == expected


# -------------------------------------------------- options that must hold --


def test_the_lab_options_stay_isolated_from_filesystem_settings(config, tmp_path):
    """setting_sources=[] and tools=[] keep personal configuration, project
    settings and CLAUDE.md out of the instrument."""
    options = _options(config, tmp_path, None)
    assert options.setting_sources == []
    assert options.tools == []
    assert options.model == "claude-haiku-4-5"
    assert options.fallback_model is None
    assert set(options.allowed_tools) == set(QUALIFIED_TOOL_NAMES)


def test_building_options_with_a_fallback_model_raises(config, tmp_path, monkeypatch):
    raw = dict(config.raw)
    raw["model"] = dict(raw["model"], fallback_model="claude-sonnet-4-5")
    broken = type(config)(raw=raw, path=config.path)
    session = build_session(config, tmp_path / "run", "s-test")
    try:
        with pytest.raises(ValueError, match="fallback_model is set"):
            build_options(broken, session, {"instance": None}, [])
    finally:
        session.emitter.close()
