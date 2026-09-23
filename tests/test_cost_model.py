"""The M6 volume model, held to its rulings on synthetic events.

Every test here builds its own events, so none reads a capture. The real corpus
is read once, in tests/test_volume_results.py, which holds the committed results
to the captures they came from.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from cost import rulings
from cost.model import (
    BENIGN_TYPES,
    CLASSES,
    Capture,
    VolumeError,
    apply_posture,
    build,
    corpus_volume,
    field_values,
    member_bytes,
    model_spend,
    nearest_rank,
    null_members,
    posture_bytes,
    projections,
    raw_parts,
    read_capture,
    registered_names,
    render_markdown,
    retention,
    serialise,
    spread,
    value_bytes,
)
from lab.config import REGISTER_PATH, REPO_ROOT
from lab.telemetry import register_group_keys
from test_style import BANNED_RE, EM_DASH

KEYS = register_group_keys(REGISTER_PATH)


def _group(name: str, **values) -> dict:
    """A group carrying every registered key, null where not given, as the emitter writes it."""
    return {key: values.get(key) for key in KEYS[name]}


def _event(event_type: str, **groups) -> dict:
    event = {
        "astp_version": "0.1.0",
        "event_type": event_type,
        "session": _group("session", id="s-1", tenant_id="t"),
    }
    for name, values in groups.items():
        event[name] = _group(name, **values)
    event["control"] = _group("control", canary_triggered=False, policy_version="0.1.0")
    return event


def _turn(response: str = "a reply", prompt: str = "an instruction") -> dict:
    return _event(
        "turn",
        turn={"index": 0, "tokens_in": 10},
        content={"prompt_text": prompt, "prompt_hash": "sha256:p",
                 "response_text": response, "response_hash": "sha256:r"},
    )


def _capture(events, corpus="benign", label="b1", tokens=100, cost=0.01, run_id="x") -> Capture:
    events = tuple(events)
    return Capture(run_id=run_id, corpus=corpus, label=label, events=events,
                   file_bytes=sum(len(serialise(e)) for e in events), tokens=tokens, cost_usd=cost)


def _synthetic_corpus() -> list[Capture]:
    """One small session per attack class and per benign task type."""
    captures = []
    for i, cls in enumerate(CLASSES):
        events = [_event("session_start"), _turn("r" * (i + 1)), _event("session_end")]
        captures.append(_capture(events, "attack", cls, cost=0.01 * (i + 1), run_id=f"a{i}"))
    for i, typ in enumerate(BENIGN_TYPES):
        events = [_event("session_start"), _turn("é" * (i + 1)),
                  _event("tool_pre", action={"tool_name": "t", "tool_arguments": {"q": "x"}}),
                  _event("session_end")]
        captures.append(_capture(events, "benign", typ, run_id=f"b{i}"))
    return captures


def _finished(doc: dict) -> dict:
    doc = dict(doc, commit="0" * 40, tree_clean=True, date="2026-09-23")
    return json.loads(json.dumps(doc, sort_keys=True))


# ---------------------------------------------------------------- rulings --
def test_the_rulings_are_what_the_owner_ruled():
    assert rulings.SESSIONS_PER_USER_PER_DAY == 10
    assert rulings.USER_COUNTS == (1_000, 10_000)
    assert rulings.BYTE_MEASURES == ("raw", "value")
    assert rulings.TRUNCATE_CHARS == 1_024
    assert rulings.TRUNCATE_SENSITIVITY == (256, 4_096)
    assert rulings.POSTURES == ("full", "truncate", "hash")
    assert rulings.PROJECTION_CORPUS == "benign"
    assert rulings.ATTACK_CORPUS_PROJECTED is False
    assert rulings.MODEL_SPEND_PROJECTED is False
    assert rulings.PRICE_PER_GB is None
    assert rulings.RETENTION_PERIODS_DAYS == ()
    assert rulings.TAG == "volume-m6"
    assert rulings.BYTES_PER_GB == 10**9


def test_every_field_the_rulings_name_is_registered():
    names = set(registered_names())
    for name in (*rulings.POSTURE_FIELDS, *rulings.KEPT_HASHES,
                 *rulings.FREE_TEXT_BESIDE, *rulings.CARVE_OUTS):
        assert name in names, name


def test_the_postures_reach_the_content_text_fields_only():
    assert set(rulings.POSTURE_FIELDS) == {"content.prompt_text", "content.response_text"}
    assert not set(rulings.POSTURE_FIELDS) & set(rulings.KEPT_HASHES)


# --------------------------------------------------------------- counting --
def test_a_member_is_counted_as_the_lab_writes_it():
    assert member_bytes("a", None) == len('"a": null')
    assert member_bytes("a", {"b": 1}) == len('"a": {"b": 1}')
    assert member_bytes("é", "é") == len('"é": "é"'.encode("utf-8"))


def test_groups_and_envelope_sum_to_the_serialised_line():
    event = _turn()
    parts = raw_parts(event)
    assert parts["total"] == len(serialise(event))
    assert sum(v for k, v in parts.items() if k != "total") == parts["total"]


def test_the_envelope_is_what_no_group_carries():
    event = _event("session_end")
    parts = raw_parts(event)
    rest = serialise({k: v for k, v in event.items() if k not in ("session", "control")})
    # The remainder is the envelope keys, the braces, the separators and the newline.
    assert parts["envelope"] == len(rest) + len(", ") * 2


@pytest.mark.parametrize("value, expected", [
    (None, 0),
    (True, 4),
    (False, 5),
    ("abc", 3),
    ("é", 2),
    (12, 2),
    (1.5, 3),
    ([1, "a"], len('[1,"a"]')),
    ({"a": 1}, len('{"a":1}')),
    ([], 2),
])
def test_value_bytes_follow_the_ruled_string_forms(value, expected):
    assert value_bytes(value) == expected


def test_a_null_value_counts_zero_but_its_field_is_still_listed():
    values = field_values(_event("session_end"))
    assert values["control.block_reason"] == 0
    assert set(values) == {f"session.{k}" for k in KEYS["session"]} | {f"control.{k}" for k in KEYS["control"]}


def test_null_members_are_counted_with_their_bytes():
    event = _event("session_end")
    nulls = [(k, v) for g in ("session", "control") for k, v in event[g].items() if v is None]
    count, size = null_members(event)
    assert count == len(nulls)
    assert size == sum(len(f'"{k}": null') for k, _ in nulls)


# --------------------------------------------------------------- postures --
def test_full_is_the_event_as_captured():
    event = _turn()
    assert apply_posture(event, "full") is event


def test_truncate_keeps_the_leading_characters_and_the_hashes():
    event = _turn(response="é" * 2_000)
    shaped = apply_posture(event, "truncate")
    assert shaped["content"]["response_text"] == "é" * rulings.TRUNCATE_CHARS
    assert shaped["content"]["prompt_text"] == "an instruction"
    assert shaped["content"]["response_hash"] == "sha256:r"
    assert shaped["content"]["prompt_hash"] == "sha256:p"


def test_truncate_takes_a_length_for_the_sensitivity_rows():
    shaped = apply_posture(_turn(response="x" * 600), "truncate", 256)
    assert len(shaped["content"]["response_text"]) == 256


def test_hash_nulls_both_texts_and_keeps_their_keys_and_hashes():
    shaped = apply_posture(_turn(), "hash")
    assert shaped["content"]["prompt_text"] is None
    assert shaped["content"]["response_text"] is None
    assert "response_text" in shaped["content"]
    assert shaped["content"]["prompt_hash"] == "sha256:p"


def test_a_posture_never_writes_to_the_captured_event():
    event = _turn(response="y" * 3_000)
    before = json.dumps(event)
    apply_posture(event, "truncate")
    apply_posture(event, "hash")
    assert json.dumps(event) == before


def test_an_event_without_content_is_untouched_by_any_posture():
    event = _event("tool_pre", action={"tool_name": "t"})
    for posture in rulings.POSTURES:
        assert apply_posture(event, posture) is event


def test_an_unknown_posture_raises():
    with pytest.raises(VolumeError):
        apply_posture(_turn(), "summarise")


def test_a_content_group_missing_a_text_key_raises():
    event = _turn()
    del event["content"]["response_text"]
    with pytest.raises(VolumeError):
        apply_posture(event, "hash")


def test_the_full_posture_counts_the_bytes_on_disk():
    events = [_event("session_start"), _turn(), _event("session_end")]
    raw, _ = posture_bytes(events, "full")
    assert raw == sum(len(serialise(e)) for e in events)


def test_hashing_removes_exactly_the_text_value_bytes():
    event = _turn(response="twelve bytes", prompt="six b.")
    _, full = posture_bytes([event], "full")
    _, hashed = posture_bytes([event], "hash")
    assert full - hashed == len("twelve bytes") + len("six b.")


# ------------------------------------------------------------- statistics --
def test_p90_is_the_nearest_rank():
    assert nearest_rank(list(range(1, 11)), 0.9) == 9
    assert nearest_rank(list(range(1, 101)), 0.9) == 90
    assert nearest_rank([7], 0.9) == 7


def test_the_spread_carries_every_ruled_statistic():
    s = spread([4, 1, 3, 2])
    assert tuple(s) == rulings.SPREAD
    assert (s["n"], s["min"], s["median"], s["mean"], s["p90"], s["max"]) == (4, 1, 2.5, 2.5, 4, 4)


def test_an_empty_spread_raises():
    with pytest.raises(VolumeError):
        spread([])


# ----------------------------------------------------------------- loading --
def _write_run(tmp_path: Path, lines: list[bytes], events_written: int | None = None) -> Path:
    run = tmp_path / "m3-b001"
    run.mkdir()
    events_path = run / "session-s.jsonl"
    events_path.write_bytes(b"".join(lines))
    manifest = {
        "run_id": "m3-b001",
        "task": {"type": "b1"},
        "session": {"events_path": str(events_path),
                    "events_written": len(lines) if events_written is None else events_written},
        "tokens": {"input_tokens": 1, "output_tokens": 2,
                   "cache_creation_input_tokens": 3, "cache_read_input_tokens": 4},
        "model_usage_raw": {"m1": {"costUSD": 0.25}, "m2": {"costUSD": 0.5}},
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run


def test_a_capture_is_read_with_its_bytes_tokens_and_estimate(tmp_path):
    line = serialise(_turn())
    capture = read_capture(_write_run(tmp_path, [line, line]), "benign", "b1")
    assert capture.file_bytes == 2 * len(line)
    assert capture.tokens == 10
    assert capture.cost_usd == 0.75
    assert len(capture.events) == 2


def test_a_line_that_does_not_round_trip_is_refused(tmp_path):
    compact = json.dumps(_turn(), separators=(",", ":")).encode("utf-8") + b"\n"
    with pytest.raises(VolumeError):
        read_capture(_write_run(tmp_path, [compact]), "benign", "b1")


def test_a_file_without_a_final_newline_is_refused(tmp_path):
    with pytest.raises(VolumeError):
        read_capture(_write_run(tmp_path, [serialise(_turn())[:-1]]), "benign", "b1")


def test_an_event_count_that_disagrees_with_the_manifest_is_refused(tmp_path):
    with pytest.raises(VolumeError):
        read_capture(_write_run(tmp_path, [serialise(_turn())], events_written=2), "benign", "b1")


# ------------------------------------------------------------------ volume --
def test_a_corpus_whose_bytes_disagree_with_disk_is_refused():
    good = _capture([_turn()])
    bad = Capture(**{**good.__dict__, "file_bytes": good.file_bytes + 1})
    with pytest.raises(VolumeError):
        corpus_volume([bad], ["b1"])


def test_every_registered_field_appears_even_when_no_event_carries_it():
    volume = corpus_volume([_capture([_event("session_end")])], ["b1"])
    assert set(volume["fields"]) == set(registered_names())
    assert volume["fields"]["retrieval.scores"]["value_bytes"] == 0


def test_model_spend_rows_sum_to_their_totals():
    spend = model_spend(_synthetic_corpus())
    per_class = spend["attack"]["per_class"]
    assert sum(r["sessions"] for r in per_class.values()) == spend["attack"]["total"]["sessions"]
    assert sum(r["tokens"] for r in per_class.values()) == spend["attack"]["total"]["tokens"]
    a8 = per_class["A8"]["cost_usd"]
    assert spend["attack"]["a8_share_of_cost_percent"] == round(100 * a8 / spend["attack"]["total"]["cost_usd"], 2)
    assert spend["attack"]["without_a8"]["sessions"] == 9


def test_projections_are_users_times_sessions_times_the_benign_mean():
    benign = [_capture([_turn()], run_id="1"), _capture([_turn(), _turn()], run_id="2")]
    totals = {"full": {"raw": 3_000, "value": 1_000}, "truncate": {"raw": 2_000, "value": 800},
              "hash": {"raw": 1_000, "value": 500}}
    rows = projections(benign, {"totals": totals})
    first = rows[0]
    assert first["users"] == 1_000
    assert first["sessions_per_day"] == 1_000 * rulings.SESSIONS_PER_USER_PER_DAY
    assert first["events_per_day"] == first["sessions_per_day"] * 3 // 2
    assert first["postures"]["full"]["raw"]["bytes_per_day"] == first["sessions_per_day"] * 3_000 // 2
    assert first["postures"]["hash"]["value"]["gb_per_day"] == round(
        first["sessions_per_day"] * 500 / 2 / 10**9, 4)
    assert [r["users"] for r in rows] == list(rulings.USER_COUNTS)


# --------------------------------------------------------------- retention --
def test_a_carve_out_that_no_longer_tiers_not_required_stops_the_model(monkeypatch):
    volume = {c: corpus_volume([_capture([_turn()])], ["b1"]) for c in ("attack", "benign")}
    monkeypatch.setattr(rulings, "CARVE_OUTS", {"control.canary_triggered": "a reason"})
    with pytest.raises(VolumeError):
        retention(volume)


def test_retention_reads_every_tier_from_the_register(fields):
    volume = {c: corpus_volume([_capture([_turn()])], ["b1"]) for c in ("attack", "benign")}
    rows = retention(volume)["rows"]
    assert [(r["field"], r["tier"]) for r in rows] == [(f["name"], f["tier"]) for f in fields]


# -------------------------------------------------------------------- page --
def test_build_needs_both_corpora():
    with pytest.raises(VolumeError):
        build([c for c in _synthetic_corpus() if c.corpus == "benign"])


def test_the_page_is_a_function_of_the_json_alone():
    doc = _finished(build(_synthetic_corpus()))
    assert render_markdown(doc) == render_markdown(json.loads(json.dumps(doc, sort_keys=True)))


def test_the_page_keeps_the_house_style_and_holds_no_address():
    """The page is generated and results/ is outside the style scan, so the
    generator is held to the same rule here, using the style test's own terms."""
    text = render_markdown(_finished(build(_synthetic_corpus())))
    assert EM_DASH not in text
    assert not BANNED_RE.search(text)
    assert "@" not in text
    assert "://" not in text


def test_every_projection_restates_its_assumption():
    text = render_markdown(_finished(build(_synthetic_corpus())))
    section = text.split("## 4. Projections")[1].split("## 5.")[0]
    tables = section.count("| Posture |")
    assert tables == len(rulings.USER_COUNTS)
    assert section.count(f"{rulings.SESSIONS_PER_USER_PER_DAY} sessions per user per day") >= tables + 1


def test_the_page_never_puts_a_price_on_telemetry():
    text = render_markdown(_finished(build(_synthetic_corpus())))
    telemetry = text.split("## 2. Telemetry volume")[1]
    assert "USD" not in telemetry
    assert "$" not in telemetry


def test_the_cost_package_loads_nothing_that_can_call_a_model_or_the_network():
    """Checked in a fresh interpreter, because this test process has already
    imported the lab agent through other tests."""
    probe = (
        "import sys, cost.model, cost.rulings\n"
        "roots = {m.split('.')[0] for m in sys.modules}\n"
        "bad = sorted(roots & {'anthropic', 'claude_agent_sdk', 'requests', 'httpx', 'urllib3',"
        " 'azure', 'socket', 'http'})\n"
        "bad += [m for m in sys.modules if m in ('lab.agent', 'lab.harness', 'lab.tools', 'lab.hooks')]\n"
        "print(','.join(bad))\n"
    )
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                         cwd=REPO_ROOT, check=True)
    assert out.stdout.strip() == ""
