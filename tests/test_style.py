"""House style, enforced mechanically rather than promised.

The style rules are: UK English, plain English, no em-dashes, and six words that
are never used. Checking them by eye at the end of a stage does not scale, so
they are a test.

This file and CLAUDE.md are exempt, because both have to name the banned words
in order to state the rule.
"""

import re
from pathlib import Path

import pytest

EM_DASH = "—"

BANNED_WORDS = ("robust", "seamless", "proven", "flexible", "leverage", "various")
BANNED_RE = re.compile(r"\b(" + "|".join(BANNED_WORDS) + r")\b", re.IGNORECASE)

# .kql added at M6 by the owner's ruling of 23 September 2026, for the
# generated Sentinel rule queries. .tape and .example added at M8 by the
# owner's ruling of 1 October 2026, for the demo GIF's vhs tape and for
# .env.example, before either was written.
SCANNED_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".json", ".toml", ".txt", ".kql", ".tape", ".example"}

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "runs", "results"}
SKIP_FILES = {"CLAUDE.md", "test_style.py"}


def _text_files(repo_root: Path) -> list[Path]:
    out = []
    for path in repo_root.rglob("*"):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        if SKIP_DIRS & set(path.relative_to(repo_root).parts):
            continue
        if path.name in SKIP_FILES:
            continue
        out.append(path)
    return sorted(out)


def test_there_is_something_to_scan(repo_root):
    assert _text_files(repo_root), "style scan found no files, the filter is wrong"


def test_no_em_dashes(repo_root):
    offenders = []
    for path in _text_files(repo_root):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if EM_DASH in line:
                offenders.append(f"{path.relative_to(repo_root)}:{lineno}")
    assert not offenders, "em-dashes found in: " + ", ".join(offenders)


def test_no_banned_words(repo_root):
    offenders = []
    for path in _text_files(repo_root):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in BANNED_RE.finditer(line):
                offenders.append(
                    f"{path.relative_to(repo_root)}:{lineno} ({match.group(0)})"
                )
    assert not offenders, "banned words found in: " + ", ".join(offenders)


@pytest.mark.parametrize("secret_marker", ["sk-ant-", "ANTHROPIC_API_KEY="])
def test_no_api_key_material_is_committed(repo_root, secret_marker):
    """Guardrail 4: the key exists only in the environment or a local .env."""
    offenders = []
    for path in _text_files(repo_root):
        text = path.read_text(encoding="utf-8")
        if secret_marker in text and path.name not in {".env.example"}:
            offenders.append(str(path.relative_to(repo_root)))
    assert not offenders, f"{secret_marker!r} appears in: " + ", ".join(offenders)


def test_gitignore_covers_the_env_file(repo_root):
    ignored = (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in [line.strip() for line in ignored]
