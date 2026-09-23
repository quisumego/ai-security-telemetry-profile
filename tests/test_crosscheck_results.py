"""The M7b report and matrix: the arithmetic on synthetic runs, and the results.

The arithmetic is tested on synthetic run directories, with the oracle and the
delivery count stubbed so each figure is set by the test. The committed results
are held to the captures: a fresh build must reproduce each file exactly, apart
from the commit, the tree state and the date. Before the results exist those
tests have nothing to compare and hold trivially.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from crosscheck import matrix, report, rulings
from lab.config import REGISTER_PATH, REPO_ROOT

METADATA = ("commit", "tree_clean", "date")


def _write_trial(runs: Path, scenario: str, trial: int, *, subtype="success", tool_calls=0,
                 contamination=(), tokens_in=100, failed=False) -> Path:
    run_dir = runs / f"m7b-{scenario}-t{trial:02d}"
    run_dir.mkdir(parents=True)
    if failed:
        (run_dir / "failure.json").write_text("{}", encoding="utf-8")
        return run_dir
    events = [{"event_type": "turn", "turn": {"index": 1, "tokens_in": tokens_in}}]
    (run_dir / "session-s.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    (run_dir / "manifest.json").write_text(json.dumps({
        "run_id": run_dir.name,
        "session": {"subtype": subtype, "is_error": False, "tool_calls": tool_calls},
        "local": {"contamination_check": list(contamination), "digest": "d" * 64,
                  "ollama_version": "0.34.3", "cli_spawned_version": "2.1.233",
                  "context_length_in_force": 65536},
    }))
    return run_dir


@pytest.fixture
def runs(tmp_path, monkeypatch):
    """Success is set by a marker file the test writes, and delivery by count."""
    monkeypatch.setattr(report, "score_run", lambda scenario, d: (d / "WIN").exists())
    monkeypatch.setattr(report, "delivery_count", lambda scenario, dirs: sum((d / "SAW").exists() for d in dirs))
    return tmp_path


def test_the_denominator_is_the_completed_trials(runs):
    _write_trial(runs, "a01", 1, tool_calls=2)
    (_write_trial(runs, "a01", 2, tool_calls=3) / "WIN").touch()
    _write_trial(runs, "a01", 3, failed=True)
    _write_trial(runs, "a01", 4, contamination=["claude-haiku-4-5 is a Claude model"])
    row = report.class_row("a01", runs)
    assert row["local"]["trials"] == 2 and row["local"]["successes"] == 1
    assert row["local"]["tool_calls"] == 5
    assert row["local"]["failed"] == ["m7b-a01-t03", "m7b-a01-t04"]
    assert row["m2"] == {"trials": 10, "successes": 0, "delivery": None}
    assert row["change_points"] == 50.0


def test_an_overlay_class_with_no_delivery_is_unmeasured_not_refused(runs):
    _write_trial(runs, "a10", 1)
    row = report.class_row("a10", runs)
    assert row["local"]["delivery"] == 0 and row["unmeasured"]
    delivered = report.class_row("a02", runs)  # no trials at all
    assert delivered["local"]["trials"] == 0 and delivered["change_points"] is None
    assert not delivered["unmeasured"]


def test_a08_flags_a_trial_decided_by_the_token_count_alone(runs):
    _write_trial(runs, "a08", 1, tool_calls=15, tokens_in=10)
    _write_trial(runs, "a08", 2, tool_calls=2, tokens_in=60_000)
    _write_trial(runs, "a08", 3, subtype="error_max_turns", tokens_in=10)
    row = report.class_row("a08", runs)
    assert row["a08_conditions"] == {
        "m7b-a08-t01": ["tool_calls"],
        "m7b-a08-t02": ["tokens_in"],
        "m7b-a08-t03": ["error_max_turns"],
    }
    assert row["a08_token_only"] == ["m7b-a08-t02"]


def test_the_report_renders_every_class_and_the_totals(runs):
    (_write_trial(runs, "a01", 1) / "WIN").touch()
    doc = report.build(runs)
    page = report.render_markdown(doc)
    assert len(doc["per_class"]) == 10
    assert doc["total"]["local_trials"] == 1 and doc["total"]["m2_successes"] == 32
    assert "| A1 | 1/1 (100%)" in page and "32/100 (32%)" in page


def test_the_comparison_lists_every_cell_and_tier_that_moved():
    m5 = json.loads(matrix.NECESSITY_JSON.read_text(encoding="utf-8"))
    local = json.loads(json.dumps(m5))
    local["single"]["turn.tokens_in"]["cells"]["A8"]["cell"] = "X"
    local["tiers"]["turn.tokens_in"]["tier"] = "required"
    out = matrix.compare(local, m5)
    assert out["differences"] == [{"field": "turn.tokens_in", "class": "A8", "m5": m5["single"]["turn.tokens_in"]["cells"]["A8"]["cell"], "local": "X"}]
    assert out["tier_differences"] == [{"field": "turn.tokens_in", "m5": "not_required", "local": "required"}]
    assert matrix.compare(m5, m5)["differences"] == []


def test_the_comparison_never_targets_the_m5_results_or_the_register():
    assert matrix.RESULTS_JSON.name == "m7b-necessity.json"
    assert matrix.RESULTS_MD.name == "m7b-necessity-matrix.md"
    for target in (matrix.RESULTS_JSON, matrix.RESULTS_MD, report.RESULTS_JSON, report.RESULTS_MD):
        assert target not in (matrix.NECESSITY_JSON, REPO_ROOT / "results" / "necessity-matrix.md", REGISTER_PATH)
    assert rulings.APPLY_TIERS is False


# ------------------------------------------------------ the committed results --


def _runs_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted((REPO_ROOT / "runs").rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(REPO_ROOT)).encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


@pytest.mark.parametrize("module", [report, matrix], ids=["report", "matrix"])
def test_a_fresh_build_reproduces_the_committed_results(module):
    if not module.RESULTS_JSON.is_file():
        return
    recorded = json.loads(module.RESULTS_JSON.read_text(encoding="utf-8"))
    before = _runs_digest()
    fresh = json.loads(json.dumps(module.build(), sort_keys=True))
    assert _runs_digest() == before, "building the results must leave every capture as it was"
    assert fresh == {k: v for k, v in recorded.items() if k not in METADATA}
    assert module.RESULTS_MD.read_text(encoding="utf-8") == module.render_markdown(recorded) + "\n"


def test_the_m5_results_and_the_register_are_untouched_by_m7b():
    """Byte for byte as tagged at tiers-m5 and left by M6 and M7."""
    import subprocess

    for path in ("results/necessity.json", "results/necessity-matrix.md", "schema/fields.yaml"):
        committed = subprocess.run(("git", "show", f"gap-m7:{path}"), cwd=REPO_ROOT,
                                   capture_output=True, check=True).stdout
        assert (REPO_ROOT / path).read_bytes() == committed, path
