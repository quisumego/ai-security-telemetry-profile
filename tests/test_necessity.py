"""The committed M5 results, held to the captures they came from.

A fresh sweep over `runs/` must reproduce `results/necessity.json` exactly,
apart from the commit, the tree state and the date, and the page must be what
the JSON renders to. So no figure in either file can drift from the captures
or be edited by hand. The sweep reads the captures and must leave them
byte-for-byte as they were.
"""

from __future__ import annotations

import hashlib
import json
import subprocess

import pytest

from ablation.matrix import NECESSITY_JSON, NECESSITY_MD, build, render_markdown
from lab.config import REPO_ROOT

METADATA = ("commit", "tree_clean", "date")


def _runs_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted((REPO_ROOT / "runs").rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(REPO_ROOT)).encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


@pytest.fixture(scope="module")
def recorded() -> dict:
    return json.loads(NECESSITY_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fresh_and_runs() -> tuple[dict, str, str]:
    before = _runs_digest()
    doc = json.loads(json.dumps(build(), sort_keys=True))
    return doc, before, _runs_digest()


def test_a_fresh_sweep_reproduces_the_recorded_results(recorded, fresh_and_runs):
    fresh, _, _ = fresh_and_runs
    stripped = {k: v for k, v in recorded.items() if k not in METADATA}
    assert fresh == stripped


def test_the_sweep_leaves_every_capture_as_it_was(fresh_and_runs):
    _, before, after = fresh_and_runs
    assert before == after


def test_the_page_is_what_the_json_renders_to(recorded):
    assert NECESSITY_MD.read_text(encoding="utf-8") == render_markdown(recorded) + "\n"


def test_the_sweep_ran_against_a_clean_commit_in_this_history(recorded):
    assert recorded["tree_clean"] is True
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", recorded["commit"], "HEAD"],
        cwd=REPO_ROOT, capture_output=True,
    )
    assert result.returncode == 0, f"{recorded['commit']} is not an ancestor of HEAD"


def test_the_results_hold_no_address_and_no_url():
    """Identifiers and counts only. An email address or a URL in the results
    would mean event content had leaked into them."""
    text = NECESSITY_JSON.read_text(encoding="utf-8") + NECESSITY_MD.read_text(encoding="utf-8")
    assert "@" not in text
    assert "://" not in text
