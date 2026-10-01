"""results/benign.json, held to the captures it is computed from.

Written by `.venv/bin/python -m benign.report --write`, added at M8 by the
owner's ruling of 1 October 2026 so that a published figure from the benign
report has a committed source. A fresh build must reproduce the file exactly,
apart from the commit, the tree state and the date it was written at.
"""

from __future__ import annotations

import hashlib
import json
import subprocess

import pytest

from benign import report
from lab.config import REPO_ROOT


def _runs_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted((REPO_ROOT / "runs").rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(REPO_ROOT)).encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _recorded() -> dict:
    if not report.RESULTS_JSON.is_file():
        pytest.skip("results/benign.json is written from a clean tree after this code is committed")
    return json.loads(report.RESULTS_JSON.read_text(encoding="utf-8"))


def test_a_fresh_build_reproduces_the_committed_results():
    recorded = _recorded()
    before = _runs_digest()
    fresh = json.loads(json.dumps(report.build(), sort_keys=True))
    assert _runs_digest() == before, "building the results must leave every capture as it was"
    assert fresh == {k: v for k, v in recorded.items() if k not in report.METADATA}


def test_the_results_were_written_from_a_clean_tree_on_this_history():
    recorded = _recorded()
    assert recorded["tree_clean"] is True
    result = subprocess.run(["git", "merge-base", "--is-ancestor", recorded["commit"], "HEAD"],
                            cwd=REPO_ROOT, capture_output=True)
    assert result.returncode == 0, f"{recorded['commit']} is not an ancestor of HEAD"


def test_the_printed_report_is_the_rendered_results():
    recorded = {k: v for k, v in _recorded().items() if k not in report.METADATA}
    assert report.render(recorded) == report.render(report.build())


def test_the_holdouts_stay_out_and_every_other_oracle_is_counted():
    recorded = _recorded()
    assert recorded["holdouts_left_out"] == ["a05", "a09"]
    assert sorted(recorded["oracle_false_positives"]) == sorted(report.SCORABLE)
    for entry in recorded["oracle_false_positives"].values():
        assert entry["of"] == recorded["total"]["sessions"] == 100
        assert entry["fired"] == len(entry["sessions"])
