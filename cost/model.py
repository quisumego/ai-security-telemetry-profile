"""The M6 cost and volume model, read from the real captures.

    .venv/bin/python -m cost.model            # print the tables
    .venv/bin/python -m cost.model --write    # write results/, from a clean tree only

**Two quantities, never blended.** Model spend is what the captures cost to run:
tokens and the SDK's estimated USD, read from each manifest. Telemetry volume is
what the profile would log: events and bytes, read from each events file. They
sit in separate sections of the output and no figure combines them.

**No model call, no network, no Azure resource.** This module reads files and
does arithmetic. Nothing under `runs/` is written: every events file is opened
for reading and every posture is applied to an in-memory copy.

**How bytes are counted**, as ruled in `cost/rulings.py`:

- *Raw captured bytes* are the UTF-8 bytes on disk. Every scored line is checked
  to re-serialise to exactly the bytes the lab wrote, so each group can be
  credited with its own `"group": {...}` member as written and the remainder
  called the envelope. Groups and envelope sum to the file size exactly.
- *Value bytes* are, per field, the UTF-8 length of the value's string form, with
  nulls and keys counting zero. An approximation of a column store's size, never
  a billed size.

**What is written.** `results/volume.json` holds identifiers and counts only,
never event content. `results/volume.md` is rendered from the JSON alone, so the
two cannot disagree. `--write` refuses a dirty tree and records the commit the
model ran against.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml

from attacks.oracles import load_scenario
from cost import rulings
from lab.config import REGISTER_PATH, REPO_ROOT

RUNS_DIR = REPO_ROOT / "runs"
RESULTS_JSON = REPO_ROOT / rulings.RESULTS_JSON
RESULTS_MD = REPO_ROOT / rulings.RESULTS_MD
NECESSITY_JSON = REPO_ROOT / "results" / "necessity.json"
COMMAND = ".venv/bin/python -m cost.model --write"

GROUPS = ("session", "turn", "content", "retrieval", "action", "control")
ENVELOPE_KEYS = ("astp_version", "event_type")
EVENT_TYPES = ("session_start", "turn", "retrieval", "tool_pre", "tool_post", "session_end")
TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)
CLASSES = tuple(f"A{i}" for i in range(1, 11))
BENIGN_TYPES = ("b1", "b2", "b3", "b4")
CORPORA = ("attack", "benign")
TIER_ORDER = ("required", "recommended", "optional", "not_required")
UNMEASURED = frozenset({"nr", "nt", "ab"})
TOP_FIELDS = 10


class VolumeError(RuntimeError):
    """The model met something it cannot count honestly, and stopped."""


# ----------------------------------------------------------------- loading --
@dataclass(frozen=True)
class Capture:
    """One scored session, loaded once and never mutated."""

    run_id: str
    corpus: str
    label: str
    events: tuple[dict[str, Any], ...]
    file_bytes: int
    tokens: int
    cost_usd: float


def serialise(event: dict[str, Any]) -> bytes:
    """One event as the lab's emitter writes it, newline included."""
    return json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n"


def read_capture(run_dir: Path, corpus: str, label: str) -> Capture:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    data = (REPO_ROOT / manifest["session"]["events_path"]).read_bytes()
    parts = data.split(b"\n")
    if parts[-1] != b"":
        raise VolumeError(f"{run_dir.name}: the events file does not end in a newline")
    events = []
    for line in parts[:-1]:
        event = json.loads(line)
        if serialise(event) != line + b"\n":
            raise VolumeError(
                f"{run_dir.name}: a line does not re-serialise to the bytes on disk, "
                "so its bytes cannot be split between groups exactly"
            )
        events.append(event)
    if len(events) != manifest["session"]["events_written"]:
        raise VolumeError(f"{run_dir.name}: event count disagrees with the manifest")
    return Capture(
        run_id=manifest["run_id"],
        corpus=corpus,
        label=label,
        events=tuple(events),
        file_bytes=len(data),
        tokens=sum(manifest["tokens"][k] for k in TOKEN_KEYS),
        cost_usd=sum(v.get("costUSD", 0) for v in (manifest.get("model_usage_raw") or {}).values()),
    )


def load_corpus(runs_dir: Path = RUNS_DIR) -> tuple[Capture, ...]:
    """The hundred attack trials and the hundred benign sessions, read only.

    The three pre-freeze runs belong to no corpus and are not read.
    """
    captures = []
    for number in range(1, 11):
        for run_dir in sorted(runs_dir.glob(f"m2-a{number:02d}-t[0-9][0-9]")):
            captures.append(read_capture(run_dir, "attack", f"A{number}"))
    for run_dir in sorted(runs_dir.glob("m3-b[0-9][0-9][0-9]")):
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        captures.append(read_capture(run_dir, "benign", str(manifest["task"]["type"])))
    return tuple(captures)


def registered_names() -> list[str]:
    """Every field in the register, in register order."""
    register = yaml.safe_load(REGISTER_PATH.read_text(encoding="utf-8"))
    return [str(entry["name"]) for entry in register["fields"]]


# ---------------------------------------------------------------- counting --
def value_bytes(value: Any) -> int:
    """The UTF-8 length of a value's string form. Null counts zero."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return len("true" if value else "false")
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def member_bytes(key: str, value: Any) -> int:
    """The bytes of `"key": value` as the lab serialises one member."""
    return len(json.dumps({key: value}, ensure_ascii=False).encode("utf-8")) - 2


def raw_parts(event: dict[str, Any]) -> dict[str, int]:
    """Raw bytes of one event, split into its groups and the envelope."""
    total = len(serialise(event))
    parts = {g: member_bytes(g, event[g]) for g in GROUPS if g in event}
    parts["envelope"] = total - sum(parts.values())
    parts["total"] = total
    return parts


def field_values(event: dict[str, Any]) -> dict[str, int]:
    """Value bytes per registered field carried by one event."""
    out = {}
    for group in GROUPS:
        for leaf, value in (event.get(group) or {}).items():
            out[f"{group}.{leaf}"] = value_bytes(value)
    return out


def envelope_values(event: dict[str, Any]) -> int:
    return sum(value_bytes(event.get(k)) for k in ENVELOPE_KEYS)


def event_value_total(event: dict[str, Any]) -> int:
    return sum(field_values(event).values()) + envelope_values(event)


def null_members(event: dict[str, Any]) -> tuple[int, int]:
    """How many members are null, and the raw bytes they take as written."""
    count = size = 0
    for group in GROUPS:
        for leaf, value in (event.get(group) or {}).items():
            if value is None:
                count += 1
                size += member_bytes(leaf, value)
    return count, size


def apply_posture(event: dict[str, Any], posture: str,
                  chars: int = rulings.TRUNCATE_CHARS) -> dict[str, Any]:
    """A copy of `event` under one retention posture. The original is untouched.

    Only the two content text fields change. The hashes are kept. An event with
    no content group is returned as it is.
    """
    if posture not in rulings.POSTURES:
        raise VolumeError(f"unknown posture {posture!r}")
    if posture == "full" or "content" not in event:
        return event
    content = dict(event["content"])
    for name in rulings.POSTURE_FIELDS:
        leaf = name.partition(".")[2]
        if leaf not in content:
            raise VolumeError(f"a content group without {leaf!r}: an absent key is not a null one")
        text = content[leaf]
        if text is None:
            continue
        content[leaf] = text[:chars] if posture == "truncate" else None
    copied = dict(event)
    copied["content"] = content
    return copied


def posture_bytes(events: Iterable[dict[str, Any]], posture: str,
                  chars: int = rulings.TRUNCATE_CHARS) -> tuple[int, int]:
    """Raw and value bytes of a session under one posture."""
    raw = value = 0
    for event in events:
        shaped = apply_posture(event, posture, chars)
        raw += len(serialise(shaped))
        value += event_value_total(shaped)
    return raw, value


# -------------------------------------------------------------- statistics --
def nearest_rank(ordered: Sequence[float], fraction: float) -> float:
    """The nearest-rank percentile of an already sorted sequence."""
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def spread(values: Iterable[float]) -> dict[str, Any]:
    ordered = sorted(values)
    if not ordered:
        raise VolumeError("no values to summarise")
    return {
        "n": len(ordered),
        "min": ordered[0],
        "median": round(statistics.median(ordered), 2),
        "mean": round(statistics.fmean(ordered), 2),
        "p90": nearest_rank(ordered, 0.9),
        "max": ordered[-1],
    }


def pct(part: float, whole: float) -> float:
    return round(100 * part / whole, 2) if whole else 0.0


# ------------------------------------------------------------- model spend --
def model_spend(captures: Sequence[Capture]) -> dict[str, Any]:
    def row(subset: Sequence[Capture]) -> dict[str, Any]:
        cost = sum(c.cost_usd for c in subset)
        return {
            "sessions": len(subset),
            "tokens": sum(c.tokens for c in subset),
            "cost_usd": round(cost, 6),
            "cost_usd_per_session": round(cost / len(subset), 6),
        }

    attack = [c for c in captures if c.corpus == "attack"]
    benign = [c for c in captures if c.corpus == "benign"]
    a8 = [c for c in attack if c.label == "A8"]
    others = [c for c in attack if c.label != "A8"]
    attack_cost = sum(c.cost_usd for c in attack)
    return {
        "attack": {
            "per_class": {cls: row([c for c in attack if c.label == cls]) for cls in CLASSES},
            "total": row(attack),
            "a8_share_of_cost_percent": pct(sum(c.cost_usd for c in a8), attack_cost),
            "without_a8": row(others),
        },
        "benign": {
            "per_type": {t: row([c for c in benign if c.label == t]) for t in BENIGN_TYPES},
            "total": row(benign),
        },
    }


# --------------------------------------------------------- telemetry volume --
def corpus_volume(captures: Sequence[Capture], labels: Sequence[str]) -> dict[str, Any]:
    events = [e for c in captures for e in c.events]
    raw_total = sum(c.file_bytes for c in captures)
    counted = sum(len(serialise(e)) for e in events)
    if counted != raw_total:
        raise VolumeError(f"re-serialised bytes {counted} disagree with {raw_total} on disk")

    group_raw = {g: 0 for g in (*GROUPS, "envelope")}
    carrying = {g: 0 for g in GROUPS}
    field_totals: dict[str, int] = dict.fromkeys(registered_names(), 0)
    field_present: dict[str, int] = {}
    envelope_value = 0
    nulls = null_raw = 0
    by_type: dict[str, list[int]] = {t: [] for t in EVENT_TYPES}
    largest_value = {"bytes": 0, "field": None}
    for event in events:
        parts = raw_parts(event)
        for g in GROUPS:
            if g in parts:
                group_raw[g] += parts[g]
                carrying[g] += 1
        group_raw["envelope"] += parts["envelope"]
        by_type[event["event_type"]].append(parts["total"])
        for name, size in field_values(event).items():
            field_totals[name] = field_totals.get(name, 0) + size
            if size:
                field_present[name] = field_present.get(name, 0) + 1
            if size > largest_value["bytes"]:
                largest_value = {"bytes": size, "field": name}
        envelope_value += envelope_values(event)
        n_null, b_null = null_members(event)
        nulls += n_null
        null_raw += b_null
    value_total = sum(field_totals.values()) + envelope_value

    def per_session(subset: Sequence[Capture]) -> dict[str, Any]:
        return {
            "sessions": len(subset),
            "events": sum(len(c.events) for c in subset),
            "raw_bytes": sum(c.file_bytes for c in subset),
            "events_per_session": spread(len(c.events) for c in subset),
            "raw_bytes_per_session": spread(c.file_bytes for c in subset),
            "value_bytes_per_session": spread(
                sum(event_value_total(e) for e in c.events) for c in subset),
        }

    groups = {}
    for g in GROUPS:
        value = sum(v for name, v in field_totals.items() if name.startswith(g + "."))
        groups[g] = {
            "raw_bytes": group_raw[g],
            "raw_share_percent": pct(group_raw[g], raw_total),
            "raw_per_event": round(group_raw[g] / len(events), 2),
            "events_carrying": carrying[g],
            "raw_per_carrying_event": round(group_raw[g] / carrying[g], 2) if carrying[g] else 0.0,
            "value_bytes": value,
            "value_share_percent": pct(value, value_total),
        }
    groups["envelope"] = {
        "raw_bytes": group_raw["envelope"],
        "raw_share_percent": pct(group_raw["envelope"], raw_total),
        "raw_per_event": round(group_raw["envelope"] / len(events), 2),
        "events_carrying": len(events),
        "raw_per_carrying_event": round(group_raw["envelope"] / len(events), 2),
        "value_bytes": envelope_value,
        "value_share_percent": pct(envelope_value, value_total),
    }
    if sum(v["raw_bytes"] for v in groups.values()) != raw_total:
        raise VolumeError("groups and envelope do not sum to the bytes on disk")

    return {
        **per_session(captures),
        "value_bytes": value_total,
        "raw_bytes_per_event": spread(len(serialise(e)) for e in events),
        "per_label": {label: per_session([c for c in captures if c.label == label]) for label in labels},
        "per_event_type": {
            t: {
                "events": len(sizes),
                "per_session": round(len(sizes) / len(captures), 2),
                "raw_bytes_per_event": spread(sizes),
            }
            for t, sizes in by_type.items() if sizes
        },
        "groups": groups,
        "fields": {
            name: {
                "value_bytes": size,
                "value_share_percent": pct(size, value_total),
                "events_with_a_value": field_present.get(name, 0),
            }
            for name, size in field_totals.items()
        },
        "nulls": {
            "members": nulls,
            "raw_bytes": null_raw,
            "raw_share_percent": pct(null_raw, raw_total),
        },
        "largest_value": largest_value,
        "largest_event_raw_bytes": max(len(serialise(e)) for e in events),
    }


def postures(captures: Sequence[Capture]) -> dict[str, Any]:
    n = len(captures)
    totals = {}
    for posture in rulings.POSTURES:
        raw = value = 0
        for c in captures:
            r, v = posture_bytes(c.events, posture)
            raw += r
            value += v
        totals[posture] = {"raw": raw, "value": value}
    full = totals["full"]
    out = {
        "per_session_mean": {
            p: {"raw": round(t["raw"] / n, 2), "value": round(t["value"] / n, 2)}
            for p, t in totals.items()
        },
        "totals": totals,
        "change_vs_full_percent": {
            p: {"raw": pct(t["raw"] - full["raw"], full["raw"]),
                "value": pct(t["value"] - full["value"], full["value"])}
            for p, t in totals.items()
        },
        "sensitivity": {},
        "texts_longer_than": {},
    }
    texts = [
        e["content"][name.partition(".")[2]]
        for c in captures for e in c.events if "content" in e
        for name in rulings.POSTURE_FIELDS
        if e["content"][name.partition(".")[2]] is not None
    ]
    out["texts"] = len(texts)
    for chars in (rulings.TRUNCATE_CHARS, *rulings.TRUNCATE_SENSITIVITY):
        out["texts_longer_than"][str(chars)] = sum(1 for t in texts if len(t) > chars)
    for chars in rulings.TRUNCATE_SENSITIVITY:
        raw = value = 0
        for c in captures:
            r, v = posture_bytes(c.events, "truncate", chars)
            raw += r
            value += v
        out["sensitivity"][str(chars)] = {
            "raw_per_session": round(raw / n, 2),
            "value_per_session": round(value / n, 2),
            "raw_change_vs_full_percent": pct(raw - full["raw"], full["raw"]),
            "value_change_vs_full_percent": pct(value - full["value"], full["value"]),
        }
    return out


def projections(benign: Sequence[Capture], posture_doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Daily ingest at each ruled user count, from the benign corpus only."""
    n = len(benign)
    events = sum(len(c.events) for c in benign)
    rows = []
    for users in rulings.USER_COUNTS:
        sessions = users * rulings.SESSIONS_PER_USER_PER_DAY
        row: dict[str, Any] = {
            "users": users,
            "sessions_per_day": sessions,
            "events_per_day": round(sessions * events / n),
            "postures": {},
        }
        for posture, total in posture_doc["totals"].items():
            row["postures"][posture] = {
                measure: {
                    "bytes_per_day": round(sessions * total[measure] / n),
                    "gb_per_day": round(sessions * total[measure] / n / rulings.BYTES_PER_GB, 4),
                }
                for measure in rulings.BYTE_MEASURES
            }
        rows.append(row)
    return rows


# --------------------------------------------------------------- retention --
def retention(volume: dict[str, Any]) -> dict[str, Any]:
    """The register's tiers beside each field's M5 row and its volume.

    Tiers are read from schema/fields.yaml and the cells from
    results/necessity.json. Neither is written.
    """
    register = yaml.safe_load(REGISTER_PATH.read_text(encoding="utf-8"))["fields"]
    necessity = json.loads(NECESSITY_JSON.read_text(encoding="utf-8"))
    rows = []
    for entry in register:
        name = entry["name"]
        cells = necessity["single"][name]["cells"]
        measured = [f"{cls} `{c['cell']}`" for cls, c in sorted(cells.items(), key=lambda kv: int(kv[0][1:]))
                    if c["cell"] not in UNMEASURED]
        rows.append({
            "field": name,
            "tier": entry["tier"],
            "security_only": bool(entry["security_only"]),
            "measured_cells": measured,
            "value_share_percent": {
                corpus: volume[corpus]["fields"][name]["value_share_percent"] for corpus in CORPORA
            },
        })
    tiers = {}
    for tier in TIER_ORDER:
        members = [r for r in rows if r["tier"] == tier]
        tiers[tier] = {
            "fields": len(members),
            "value_share_percent": {
                corpus: round(sum(volume[corpus]["fields"][r["field"]]["value_share_percent"]
                                  for r in members), 2)
                for corpus in CORPORA
            },
        }
    not_required = [r for r in rows if r["tier"] == "not_required"]
    carve_outs = {}
    for name, reason in rulings.CARVE_OUTS.items():
        tier = next(r["tier"] for r in rows if r["field"] == name)
        if tier != "not_required":
            raise VolumeError(f"{name} is carved out of a Not required tier it no longer holds")
        carve_outs[name] = reason
    pair = necessity["pairs"].get("+".join(rulings.POSTURE_FIELDS))
    posture_cells = sorted({necessity["single"][f]["cells"][cls]["cell"]
                            for f in rulings.POSTURE_FIELDS for cls in CLASSES}
                           | set((pair or {}).get("cells", {}).values()))
    return {
        "rows": rows,
        "tiers": tiers,
        "not_required": len(not_required),
        "not_required_unmeasured": sum(1 for r in not_required if not r["measured_cells"]),
        "not_required_measured": {r["field"]: r["measured_cells"] for r in not_required if r["measured_cells"]},
        "carve_outs": carve_outs,
        "posture_fields_m5_cells": posture_cells,
        "posture_fields_pair_swept": pair is not None,
    }


# ------------------------------------------------------------------- build --
def build(captures: Sequence[Capture] | None = None) -> dict[str, Any]:
    """Everything the results file holds, except the commit, tree state and date."""
    captures = load_corpus() if captures is None else captures
    attack = [c for c in captures if c.corpus == "attack"]
    benign = [c for c in captures if c.corpus == "benign"]
    if not attack or not benign:
        raise VolumeError("both corpora are needed")
    volume = {
        "attack": corpus_volume(attack, CLASSES),
        "benign": corpus_volume(benign, BENIGN_TYPES),
    }
    posture_doc = {"attack": postures(attack), "benign": postures(benign)}
    class_names = {f"A{n}": load_scenario(f"a{n:02d}")["class"] for n in range(1, 11)}
    return {
        "command": COMMAND,
        "rulings": {
            "ruled_date": rulings.RULED_DATE,
            "sessions_per_user_per_day": rulings.SESSIONS_PER_USER_PER_DAY,
            "sessions_per_user_per_day_basis": rulings.SESSIONS_PER_USER_PER_DAY_BASIS,
            "user_counts": list(rulings.USER_COUNTS),
            "truncate_chars": rulings.TRUNCATE_CHARS,
            "truncate_sensitivity": list(rulings.TRUNCATE_SENSITIVITY),
            "postures": list(rulings.POSTURES),
            "posture_fields": list(rulings.POSTURE_FIELDS),
            "kept_hashes": list(rulings.KEPT_HASHES),
            "free_text_beside": list(rulings.FREE_TEXT_BESIDE),
            "projection_corpus": rulings.PROJECTION_CORPUS,
            "price_per_gb": rulings.PRICE_PER_GB,
            "retention_periods_days": list(rulings.RETENTION_PERIODS_DAYS),
            "bytes_per_gb": rulings.BYTES_PER_GB,
        },
        "class_names": class_names,
        "model_spend": model_spend(captures),
        "volume": volume,
        "postures": posture_doc,
        "projections": projections(benign, posture_doc["benign"]),
        "retention": retention(volume),
    }


# ------------------------------------------------------------------ render --
def _n(x: float) -> str:
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.2f}"


def _spread_row(label: str, s: dict[str, Any]) -> str:
    return (f"| {label} | {s['n']:,} | {_n(s['min'])} | {_n(s['median'])} | {_n(s['mean'])} "
            f"| {_n(s['p90'])} | {_n(s['max'])} |")


def _assumption(doc: dict[str, Any]) -> str:
    r = doc["rulings"]
    return (f"**Assumption: {r['sessions_per_user_per_day']} sessions per user per day**, "
            f"{r['sessions_per_user_per_day_basis']}.")


def _benign_corpus_line(doc: dict[str, Any]) -> str:
    per = doc["volume"]["benign"]["per_label"]
    mix = ", ".join(f"{t} {per[t]['sessions']}" for t in BENIGN_TYPES)
    return (f"Corpus: M3 benign, n={doc['volume']['benign']['sessions']}, at its captured mix "
            f"({mix}), which is the generator's design and not a measured traffic mix.")


def render_markdown(doc: dict[str, Any]) -> str:
    out: list[str] = []
    add = out.append
    spend = doc["model_spend"]
    vol = doc["volume"]
    rul = doc["rulings"]
    names = doc["class_names"]

    add("# Cost and volume model")
    add("")
    add(f"Generated by `{doc['command']}` from the captures under `runs/`. Do not edit by hand.")
    add("")
    add("| | |")
    add("|---|---|")
    add(f"| Model ran against commit | `{doc['commit']}` |")
    add(f"| Date | {doc['date']} |")
    add(f"| Captures | {vol['attack']['sessions']} attack trials (M2) and {vol['benign']['sessions']} "
        "benign sessions (M3) under `runs/`, read only, never written |")
    add("| Model calls | none |")
    add("| Azure | nothing deployed, no resource created, no Azure spend |")
    add(f"| Rulings | ruled by the owner on {rul['ruled_date']}, committed in `cost/rulings.py` "
        "before the model existed |")
    add("")
    add("Two different quantities are both called cost, and this page keeps them apart. **Model spend** "
        "(Section 1) is what the captures cost to run, in tokens and estimated US dollars. **Telemetry "
        "volume** (Sections 2 to 4) is what the profile would log, in events and bytes. No figure on this "
        "page combines the two. No price is attached to telemetry volume: the reader supplies one, and "
        "`docs/sentinel-mapping.md` says where to read it.")
    add("")

    # ------------------------------------------------------------ spend --
    add("## 1. Model spend of the captures")
    add("")
    add("Tokens are the sum of uncached input, output, cache creation and cache read tokens in each "
        "manifest. US dollars are the SDK's own estimate from each manifest's model usage, **not money "
        "spent**: the captures drew on a subscription. Not projected to any user count, as ruled.")
    add("")
    add(f"Corpus: M2 attack, n={spend['attack']['total']['sessions']}, ten trials per class.")
    add("")
    add("| Class | Name | Sessions | Tokens | Estimated USD | USD per session |")
    add("|---|---|---|---|---|---|")
    for cls in CLASSES:
        r = spend["attack"]["per_class"][cls]
        add(f"| {cls} | {names[cls]} | {r['sessions']} | {r['tokens']:,} | {r['cost_usd']:.4f} "
            f"| {r['cost_usd_per_session']:.4f} |")
    t = spend["attack"]["total"]
    add(f"| **All** | | {t['sessions']} | {t['tokens']:,} | **{t['cost_usd']:.4f}** "
        f"| {t['cost_usd_per_session']:.4f} |")
    w = spend["attack"]["without_a8"]
    add(f"| All but A8 | | {w['sessions']} | {w['tokens']:,} | {w['cost_usd']:.4f} "
        f"| {w['cost_usd_per_session']:.4f} |")
    add("")
    add(f"A8 is **{spend['attack']['a8_share_of_cost_percent']:.1f} per cent** of the attack corpus's "
        "estimated spend on its own, so no single mean describes it.")
    add("")
    add(f"Corpus: M3 benign, n={spend['benign']['total']['sessions']}.")
    add("")
    add("| Task type | Sessions | Tokens | Estimated USD | USD per session |")
    add("|---|---|---|---|---|")
    for typ in BENIGN_TYPES:
        r = spend["benign"]["per_type"][typ]
        add(f"| {typ} | {r['sessions']} | {r['tokens']:,} | {r['cost_usd']:.4f} | {r['cost_usd_per_session']:.4f} |")
    t = spend["benign"]["total"]
    add(f"| **All** | {t['sessions']} | {t['tokens']:,} | **{t['cost_usd']:.4f}** | {t['cost_usd_per_session']:.4f} |")
    add("")

    # ----------------------------------------------------------- volume --
    add("## 2. Telemetry volume")
    add("")
    add("### How bytes are counted")
    add("")
    add("- **Raw captured bytes** are the UTF-8 bytes on disk, as the lab serialised them: every "
        "registered key of a group present, null where a value does not apply. Every scored line "
        "re-serialises to exactly those bytes, so each group is credited with its own member as "
        "written and the rest of the line (braces, separators, `astp_version`, `event_type` and the "
        "newline) is the envelope. Groups and envelope sum to the file size exactly.")
    add("- **Value bytes** are, per field, the UTF-8 length of the value's string form: strings as "
        "they are, numbers as JSON text, booleans as `true` or `false`, arrays and objects as compact "
        "JSON. Nulls and keys count zero. `astp_version` and `event_type` are counted as envelope "
        "values. This approximates a column store's size. It is **not a billed size**: the vendor "
        "publishes no per-type formula.")
    add("- **What neither measure carries.** A production pipeline adds a time column and other system "
        "columns, request framing and batching, and whatever its shipper adds. The captures are the "
        "lab's own serialisation and carry none of that.")
    add("")
    add("| Corpus | Sessions | Events | Raw bytes | Value bytes | Value as share of raw |")
    add("|---|---|---|---|---|---|")
    for corpus, label in (("attack", "M2 attack"), ("benign", "M3 benign")):
        v = vol[corpus]
        add(f"| {label} | {v['sessions']} | {v['events']:,} | {v['raw_bytes']:,} | {v['value_bytes']:,} "
            f"| {pct(v['value_bytes'], v['raw_bytes']):.1f}% |")
    add("")
    add("### Events and bytes per session, with the spread")
    add("")
    add("p90 is the nearest-rank 90th percentile.")
    add("")
    for corpus, label in (("benign", "M3 benign"), ("attack", "M2 attack")):
        v = vol[corpus]
        add(f"Corpus: {label}, n={v['sessions']}.")
        add("")
        add("| Measure | n | min | median | mean | p90 | max |")
        add("|---|---|---|---|---|---|---|")
        add(_spread_row("Events per session", v["events_per_session"]))
        add(_spread_row("Raw bytes per session", v["raw_bytes_per_session"]))
        add(_spread_row("Value bytes per session", v["value_bytes_per_session"]))
        add(_spread_row("Raw bytes per event", v["raw_bytes_per_event"]))
        add("")
    add("### Per attack class and per benign task type")
    add("")
    add("Corpus: M2 attack, n=10 per class. Means, with the range in brackets.")
    add("")
    add("| Class | Events per session | Raw bytes per session | Value bytes per session |")
    add("|---|---|---|---|")
    for cls in CLASSES:
        p = vol["attack"]["per_label"][cls]
        e, r, val = p["events_per_session"], p["raw_bytes_per_session"], p["value_bytes_per_session"]
        add(f"| {cls} | {_n(e['mean'])} ({_n(e['min'])} to {_n(e['max'])}) "
            f"| {_n(r['mean'])} ({_n(r['min'])} to {_n(r['max'])}) "
            f"| {_n(val['mean'])} ({_n(val['min'])} to {_n(val['max'])}) |")
    add("")
    a8_raw = vol["attack"]["per_label"]["A8"]["raw_bytes"]
    add(f"A8 is **{pct(a8_raw, vol['attack']['raw_bytes']):.1f} per cent** of the attack corpus's raw "
        f"bytes, against {spend['attack']['a8_share_of_cost_percent']:.1f} per cent of its estimated "
        "spend. The fetched pages that make A8 expensive enter the model's context and never the log, "
        "which records a result's hash and size and not the result.")
    add("")
    add("Corpus: M3 benign, per task type.")
    add("")
    add("| Task type | Sessions | Events per session | Raw bytes per session | Value bytes per session |")
    add("|---|---|---|---|---|")
    for typ in BENIGN_TYPES:
        p = vol["benign"]["per_label"][typ]
        e, r, val = p["events_per_session"], p["raw_bytes_per_session"], p["value_bytes_per_session"]
        add(f"| {typ} | {p['sessions']} | {_n(e['mean'])} ({_n(e['min'])} to {_n(e['max'])}) "
            f"| {_n(r['mean'])} ({_n(r['min'])} to {_n(r['max'])}) "
            f"| {_n(val['mean'])} ({_n(val['min'])} to {_n(val['max'])}) |")
    add("")
    add("### Events by type")
    add("")
    add("| Event type | M2 attack events | per session | raw bytes per event, mean | M3 benign events "
        "| per session | raw bytes per event, mean |")
    add("|---|---|---|---|---|---|---|")
    for et in EVENT_TYPES:
        a = vol["attack"]["per_event_type"].get(et)
        b = vol["benign"]["per_event_type"].get(et)
        cells = []
        for x in (a, b):
            cells.append(f"{x['events']:,} | {_n(x['per_session'])} | {_n(x['raw_bytes_per_event']['mean'])}"
                         if x else "0 | 0 | ")
        add(f"| `{et}` | {cells[0]} | {cells[1]} |")
    add("")
    add("### Bytes per event by field group")
    add("")
    add("Raw bytes per event are averaged over every event in the corpus; the per carrying event figure "
        "divides by the events that carry the group. Shares are of the corpus total.")
    add("")
    add("| Group | Benign raw per event | Benign raw per carrying event | Benign raw share "
        "| Benign value share | Attack raw per event | Attack raw share | Attack value share |")
    add("|---|---|---|---|---|---|---|---|")
    for g in (*GROUPS, "envelope"):
        b = vol["benign"]["groups"][g]
        a = vol["attack"]["groups"][g]
        add(f"| {g} | {_n(b['raw_per_event'])} | {_n(b['raw_per_carrying_event'])} "
            f"| {b['raw_share_percent']:.1f}% | {b['value_share_percent']:.1f}% "
            f"| {_n(a['raw_per_event'])} | {a['raw_share_percent']:.1f}% | {a['value_share_percent']:.1f}% |")
    add("")
    largest = max(GROUPS, key=lambda g: vol["benign"]["groups"][g]["raw_bytes"])
    add(f"The largest group in benign raw bytes is **{largest}**, at "
        f"{vol['benign']['groups'][largest]['raw_share_percent']:.1f} per cent. The session group is "
        "carried whole on every event, so that each line stands alone.")
    add("")
    for corpus, label in (("benign", "M3 benign"), ("attack", "M2 attack")):
        nl = vol[corpus]["nulls"]
        add(f"{label}: {nl['members']:,} null members take {nl['raw_bytes']:,} raw bytes, "
            f"{nl['raw_share_percent']:.1f} per cent of the corpus. The lab writes every registered key "
            "so that the M5 sweep could null a field without deleting one; a pipeline need not.")
        add("")
    add("### The largest fields, by value bytes")
    add("")
    add("| Field | Tier | Benign value share | Attack value share |")
    add("|---|---|---|---|")
    tiers_by_field = {r["field"]: r["tier"] for r in doc["retention"]["rows"]}
    top = sorted(vol["benign"]["fields"].items(), key=lambda kv: (-kv[1]["value_bytes"], kv[0]))[:TOP_FIELDS]
    for name, b in top:
        a = vol["attack"]["fields"][name]
        add(f"| `{name}` | {tiers_by_field[name]} | {b['value_share_percent']:.1f}% "
            f"| {a['value_share_percent']:.1f}% |")
    add("")
    add("### Limits")
    add("")
    for corpus, label in (("benign", "M3 benign"), ("attack", "M2 attack")):
        lv = vol[corpus]["largest_value"]
        add(f"- {label}: the largest single field value is {lv['bytes']:,} bytes (`{lv['field']}`), and "
            f"the largest event is {vol[corpus]['largest_event_raw_bytes']:,} raw bytes.")
    add("")

    # --------------------------------------------------------- postures --
    add("## 3. Retention postures")
    add("")
    add(f"From `docs/methodology.md` Section 8.2, measured from the same logs. Each posture is applied "
        f"to an in-memory copy. **Full** is as captured. **Truncate** keeps the first "
        f"{rul['truncate_chars']:,} characters of each text field. **Hash** nulls both text fields. "
        "The postures reach `content.prompt_text` and `content.response_text` only, and keep "
        "`content.prompt_hash` and `content.response_hash` under every posture. A nulled field keeps "
        "its key, so the raw measure still carries its member.")
    add("")
    add("| Corpus | Posture | Raw bytes per session | Change | Value bytes per session | Change |")
    add("|---|---|---|---|---|---|")
    for corpus, label in (("benign", "M3 benign"), ("attack", "M2 attack")):
        p = doc["postures"][corpus]
        for posture in rul["postures"]:
            m = p["per_session_mean"][posture]
            ch = p["change_vs_full_percent"][posture]
            add(f"| {label} | {posture} | {_n(m['raw'])} | {ch['raw']:+.1f}% | {_n(m['value'])} "
                f"| {ch['value']:+.1f}% |")
    add("")
    add("Sensitivity, per session only:")
    add("")
    add("| Corpus | Truncate at | Raw bytes per session | Change | Value bytes per session | Change |")
    add("|---|---|---|---|---|---|")
    for corpus, label in (("benign", "M3 benign"), ("attack", "M2 attack")):
        p = doc["postures"][corpus]
        for chars in rul["truncate_sensitivity"]:
            s = p["sensitivity"][str(chars)]
            add(f"| {label} | {chars:,} | {_n(s['raw_per_session'])} | {s['raw_change_vs_full_percent']:+.1f}% "
                f"| {_n(s['value_per_session'])} | {s['value_change_vs_full_percent']:+.1f}% |")
    add("")
    for corpus, label in (("benign", "M3 benign"), ("attack", "M2 attack")):
        p = doc["postures"][corpus]
        longer = ", ".join(f"{int(k):,}: {v}" for k, v in sorted(p["texts_longer_than"].items(),
                                                                  key=lambda kv: int(kv[0])))
        add(f"- {label}: of {p['texts']:,} non-null text values, the number longer than each "
            f"truncation length is {longer}.")
    add("")
    b_content = vol["benign"]["groups"]["content"]["raw_share_percent"]
    a_content = vol["attack"]["groups"]["content"]["raw_share_percent"]
    ta = rul["free_text_beside"][0]
    add(f"**The content group does not dominate these captures.** It is {b_content:.1f} per cent of "
        f"benign raw bytes and {a_content:.1f} per cent of attack raw bytes. `content.prompt_text` "
        "carries the user's instruction, repeated on each turn, and tool results are never logged, only "
        "their hash and size. The postures are therefore a smaller lever here than a deployment that "
        f"logged tool results would find. `{ta}` carries free text the postures do not reach: "
        f"{vol['benign']['fields'][ta]['value_share_percent']:.1f} per cent of benign value bytes and "
        f"{vol['attack']['fields'][ta]['value_share_percent']:.1f} per cent of attack value bytes.")
    add("")
    codes = [f"`{c}`" for c in doc["retention"]["posture_fields_m5_cells"]]
    cells = ", ".join(codes[:-1]) + (" or " if len(codes) > 1 else "") + codes[-1]
    add("**What the postures cost in detection is not measured here.** The M5 sweep nulled both text "
        "fields singly and as a pair, and every cell reads " + cells + ": no detector counted for a "
        "class with a successful trial reads either field, so the sweep could not measure what a "
        "posture loses, and this page does not claim it loses nothing. The Required field "
        "`control.canary_triggered` is computed by the lab from the full response text at the source. "
        "A hash or truncate posture keeps that field only if the flag is computed before the text is "
        "hashed or cut.")
    add("")

    # ------------------------------------------------------ projections --
    add("## 4. Projections")
    add("")
    add(_assumption(doc) + " Daily figures are users times sessions per user per day times the benign "
        "mean per session. The spread in Section 2 applies to every figure here.")
    add("")
    for row in doc["projections"]:
        add(f"**{row['users']:,} users.** {_benign_corpus_line(doc)} {_assumption(doc)}")
        add("")
        add(f"{row['sessions_per_day']:,} sessions and {row['events_per_day']:,} events a day.")
        add("")
        add("| Posture | Raw bytes a day | Raw GB a day | Value bytes a day | Value GB a day |")
        add("|---|---|---|---|---|")
        for posture in rul["postures"]:
            p = row["postures"][posture]
            add(f"| {posture} | {p['raw']['bytes_per_day']:,} | {p['raw']['gb_per_day']:.4f} "
                f"| {p['value']['bytes_per_day']:,} | {p['value']['gb_per_day']:.4f} |")
        add("")
    add(f"A GB is {rul['bytes_per_gb']:,} bytes. Daily ingest only: no retention period is assumed and "
        "no stored volume is computed, as ruled. The attack corpus is never projected: attack sessions "
        "are not ordinary traffic.")
    add("")

    # -------------------------------------------------------- retention --
    ret = doc["retention"]
    add("## 5. Retention guidance by tier")
    add("")
    add("Each field's tier is the one in `schema/fields.yaml` when the model ran, beside the cells that "
        "decided it in `results/necessity.json`. Neither file is written here. Read the field's row "
        "before quoting its tier.")
    add("")
    add("| Tier | Fields | Benign value share | Attack value share | Guidance |")
    add("|---|---|---|---|---|")
    guidance = {
        "required": "Retain at full fidelity. Removing any one of these made a class undetectable.",
        "recommended": "No field holds this tier.",
        "optional": "Retain. Each carries a stated incident response, forensic or regulatory "
                    "justification, ruled at M5, and most are hashes and identifiers.",
        "not_required": "**Not a recommendation to discard.** Decide per field, with the volume "
                        "beside it, and read the caution below.",
    }
    for tier in TIER_ORDER:
        t = ret["tiers"][tier]
        add(f"| {tier} | {t['fields']} | {t['value_share_percent']['benign']:.1f}% "
            f"| {t['value_share_percent']['attack']:.1f}% | {guidance[tier]} |")
    add("")
    exceptions = "; ".join(f"`{f}`, {', '.join(c)}" for f, c in ret["not_required_measured"].items())
    add(f"**The caution.** {ret['not_required_unmeasured']} of the {ret['not_required']} Not required "
        "fields read `nr`, `nt` or `ab` in every column of the necessity matrix. That means no detector "
        "counted for a class with a successful trial ever read them. It does not mean they were shown to "
        "carry nothing, and a Not required tier on its own is not a reason to drop a field. "
        + (f"The measured exception: {exceptions}." if exceptions else ""))
    add("")
    add("**Two carve-outs, retained whatever their tier says:**")
    add("")
    for name, reason in ret["carve_outs"].items():
        add(f"- `{name}`: {reason}.")
    add("")
    add("**Content text.** Hash always, truncate as a middle path, full text opt-in, as "
        "`docs/methodology.md` Section 8.2 sets out, with the detection caveat in Section 3 above.")
    add("")
    add("| Field | Tier | Security only | Measured cells | Benign value share | Attack value share |")
    add("|---|---|---|---|---|---|")
    for r in ret["rows"]:
        cells_text = ", ".join(r["measured_cells"]) if r["measured_cells"] else "none"
        mark = " (carve-out)" if r["field"] in ret["carve_outs"] else ""
        add(f"| `{r['field']}`{mark} | {r['tier']} | {'yes' if r['security_only'] else ''} | {cells_text} "
            f"| {r['value_share_percent']['benign']:.1f}% | {r['value_share_percent']['attack']:.1f}% |")
    return "\n".join(out)


# -------------------------------------------------------------------- main --
def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The M6 cost and volume model.")
    parser.add_argument("--write", action="store_true", help="write results/, from a clean tree only")
    args = parser.parse_args(argv)

    commit = _git("rev-parse", "HEAD")
    clean = _git("status", "--porcelain") == ""
    if args.write and not clean:
        print("  refusing to write: the working tree is not clean, so the commit would not describe the model")
        return 1
    doc = build()
    doc["commit"] = commit
    doc["tree_clean"] = clean
    doc["date"] = datetime.date.today().isoformat()
    # Rendered from the sorted JSON form, so the page is a function of the
    # committed file alone and a test can regenerate it from that file.
    doc = json.loads(json.dumps(doc, sort_keys=True))
    text = render_markdown(doc)
    print(text)
    if args.write:
        RESULTS_JSON.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        RESULTS_MD.write_text(text + "\n", encoding="utf-8")
        print(f"\n  written: {RESULTS_JSON.relative_to(REPO_ROOT)}, {RESULTS_MD.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
