"""The committed M6 results, held to the captures they came from.

A fresh run of the model over `runs/` must reproduce `results/volume.json`
exactly, apart from the commit, the tree state and the date, and the page must
be what the JSON renders to. So no figure in either file can drift from the
captures or be edited by hand. The model reads the captures and must leave them
byte for byte as they were. This is the one place the suite reads the real
corpus for M6; the arithmetic is tested on fixtures in tests/test_cost_model.py.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess

import pytest
import yaml

from attacks.report import SCENARIO_IDS, scenario_figures
from benign import report as benign_report
from cost import rulings
from cost.model import RESULTS_JSON, RESULTS_MD, UNMEASURED, build, render_markdown
from lab.config import REGISTER_PATH, REPO_ROOT

METADATA = ("commit", "tree_clean", "date")


def _runs_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted((REPO_ROOT / "runs").rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(REPO_ROOT)).encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _manifests(pattern: str) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((REPO_ROOT / "runs").glob(f"{pattern}/manifest.json"))]


@pytest.fixture(scope="module")
def recorded() -> dict:
    return json.loads(RESULTS_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fresh_and_runs() -> tuple[dict, str, str]:
    before = _runs_digest()
    doc = json.loads(json.dumps(build(), sort_keys=True))
    return doc, before, _runs_digest()


def test_a_fresh_run_reproduces_the_recorded_results(recorded, fresh_and_runs):
    fresh, _, _ = fresh_and_runs
    assert fresh == {k: v for k, v in recorded.items() if k not in METADATA}


def test_the_model_leaves_every_capture_as_it_was(fresh_and_runs):
    _, before, after = fresh_and_runs
    assert before == after


def test_the_page_is_what_the_json_renders_to(recorded):
    assert RESULTS_MD.read_text(encoding="utf-8") == render_markdown(recorded) + "\n"


def test_the_model_ran_against_a_clean_commit_in_this_history(recorded):
    assert recorded["tree_clean"] is True
    result = subprocess.run(["git", "merge-base", "--is-ancestor", recorded["commit"], "HEAD"],
                            cwd=REPO_ROOT, capture_output=True)
    assert result.returncode == 0, f"{recorded['commit']} is not an ancestor of HEAD"


def test_the_results_hold_no_address_and_no_url():
    """Identifiers and counts only. An email address or a URL in the results
    would mean event content had leaked into them."""
    text = RESULTS_JSON.read_text(encoding="utf-8") + RESULTS_MD.read_text(encoding="utf-8")
    assert "@" not in text
    assert "://" not in text


# ------------------------------------------ agreement with what exists --
def test_the_corpora_are_the_two_scored_hundreds(recorded):
    for corpus, pattern in (("attack", "m2-a[0-9][0-9]-t[0-9][0-9]"), ("benign", "m3-b[0-9][0-9][0-9]")):
        manifests = _manifests(pattern)
        volume = recorded["volume"][corpus]
        assert volume["sessions"] == len(manifests) == 100
        assert volume["events"] == sum(m["session"]["events_written"] for m in manifests)
        assert volume["raw_bytes"] == sum(
            (REPO_ROOT / m["session"]["events_path"]).stat().st_size for m in manifests)


def test_attack_spend_agrees_with_the_attack_report(recorded):
    """Within the model's stated precision of a millionth of a dollar. The two
    sum the same floats in a different way, sum() against +=, and A5's total
    falls on a rounding boundary at the sixth place, so exact equality after
    rounding would test the summation, not the figures."""
    per_class = recorded["model_spend"]["attack"]["per_class"]
    for number, scenario_id in enumerate(SCENARIO_IDS, 1):
        figures = scenario_figures(scenario_id)
        row = per_class[f"A{number}"]
        assert row["tokens"] == figures["tokens"]
        assert row["cost_usd"] == pytest.approx(figures["cost"], abs=1e-6)
        assert f"{row['cost_usd']:.4f}" == f"{figures['cost']:.4f}"


def test_benign_spend_agrees_with_the_benign_report(recorded, capsys):
    benign_report.main()
    printed = capsys.readouterr().out
    per_type = recorded["model_spend"]["benign"]["per_type"]
    for task_type, row in per_type.items():
        match = re.search(rf"^\s+{task_type}\s+(\d+)\s+([\d,]+)\s+([\d.]+)$", printed, re.MULTILINE)
        assert match, task_type
        assert row["sessions"] == int(match.group(1))
        assert row["tokens"] == int(match.group(2).replace(",", ""))
        assert f"{row['cost_usd']:.4f}" == match.group(3)


def test_the_retention_caution_is_counted_not_typed(recorded):
    register = yaml.safe_load(REGISTER_PATH.read_text(encoding="utf-8"))["fields"]
    necessity = json.loads((REPO_ROOT / "results" / "necessity.json").read_text(encoding="utf-8"))
    not_required = [f["name"] for f in register if f["tier"] == "not_required"]
    unmeasured = [n for n in not_required
                  if all(c["cell"] in UNMEASURED for c in necessity["single"][n]["cells"].values())]
    retention = recorded["retention"]
    assert retention["not_required"] == len(not_required)
    assert retention["not_required_unmeasured"] == len(unmeasured)
    assert set(retention["carve_outs"]) == set(rulings.CARVE_OUTS)
    for name in rulings.CARVE_OUTS:
        assert name in not_required


def test_projections_come_from_the_benign_corpus_alone(recorded):
    benign = recorded["volume"]["benign"]
    for row in recorded["projections"]:
        sessions = row["users"] * rulings.SESSIONS_PER_USER_PER_DAY
        assert row["sessions_per_day"] == sessions
        assert row["events_per_day"] == round(sessions * benign["events"] / benign["sessions"])
        full = row["postures"]["full"]["raw"]["bytes_per_day"]
        assert full == round(sessions * benign["raw_bytes"] / benign["sessions"])
