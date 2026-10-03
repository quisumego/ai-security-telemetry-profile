"""The vendor gap analysis: what each vendor's records carry, and what that leaves detectable.

    .venv/bin/python -m vendor_gap.analysis           # print the class answers
    .venv/bin/python -m vendor_gap.analysis --write   # write results/vendor-gap.json and the doc's generated blocks

**Evidence first.** Every verdict is read from `vendor_gap/evidence.yaml`, where
each carries the numbers of the vendor pages it rests on. Those pages were read
in the M7 session, and nothing in this package reaches the network: a test
loads it in a fresh interpreter and checks. The rulings it applies are
`vendor_gap/rulings.py`.

**The vendor pass** (ruling 11). A class's answer on a vendor column is
computed, not argued. The captures are loaded once, read only, by the M5
harness. For each column the counted detector (M5 ruling 1) is re-run over the
class's successful trials and its benign denominator, with every input the
column does not count as available taken away: a field is nulled, an event
type the surface keeps no record of is dropped, and where the surface carries
no key that groups a session's records, each record runs as a session of one
(ruling 12). The deployment's own configuration is held as scored. The result
is compared with the baseline by `ablation.matrix.cell_code`, which is
methodology Section 4 as M5 ruling 2 reads it. An input the pages do not
settle is run both ways, and a class whose answer differs across those
combinations is `uc` (ruling 13).

**What a detector needs beyond its declared reads.** `DETECTOR_NEEDS` records
the event types each frozen detector iterates or counts, and whether it reads a
session's events together. The declarations in `detect/detectors.py` name
fields only, so these were read from its source, and a test checks every one
against the corpus.

**What is written.** `results/vendor-gap.json` holds identifiers, codes and
counts only, never event content. The doc's generated blocks are rendered from
the same data, so the two cannot disagree.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable, Sequence

import yaml

from ablation import rulings as m5
from ablation.ablate import CLASSES, Capture, fires, load_corpus, null_fields
from ablation.matrix import NECESSITY_JSON, TIER_ORDER, Populations, cell_code, populations
from detect.detectors import DETECTORS, Detector, DetectorConfig
from detect.evaluate import detector_config
from lab.config import REGISTER_PATH, REPO_ROOT
from vendor_gap import rulings

EVIDENCE_PATH = REPO_ROOT / rulings.EVIDENCE
DOC_PATH = REPO_ROOT / rulings.DOC
# Since 3 October 2026 the page is a hub with three topic pages, and each
# generated block lives on exactly one of them.
TOPIC_DIR = DOC_PATH.with_suffix("")
PAGES = {
    DOC_PATH: ("headline",),
    TOPIC_DIR / "surfaces.md": ("surfaces", "counts"),
    TOPIC_DIR / "classes.md": ("classes", "additions"),
    TOPIC_DIR / "sources.md": ("sources", "quotes"),
}
RESULTS_PATH = REPO_ROOT / rulings.RESULTS
COMMAND = ".venv/bin/python -m vendor_gap.analysis --write"

VERDICT = {
    "D": "available_by_default",
    "C": "available_with_configuration",
    "A": "absent",
    "U": "unconfirmed",
}
FORM = {
    "own": "own_field",
    "body": "body_documented",
    "content": "content_only",
    "caller": "caller_supplied",
    "derived": "derivable",
}
assert set(VERDICT.values()) == set(rulings.VERDICTS)
assert set(FORM.values()) == set(rulings.FORMS)

# Ruling 15 asks for short quotations. This is how short, checked by test.
QUOTE_MAX_WORDS = 30

# Read from detect/detectors.py: the event types each detector iterates or
# counts, and whether it reads a session's events together rather than one at
# a time. d-a07 reasons from the absence of retrieval events, and d-a08 fires
# first on a count of tool_pre events that reads no field. Neither shows in the
# declared reads, which name fields only.
DETECTOR_NEEDS: dict[str, tuple[frozenset[str], bool]] = {
    "d-a01": (frozenset({"tool_pre"}), False),
    "d-a02": (frozenset({"retrieval", "tool_pre"}), True),
    "d-a03": (frozenset({"retrieval", "turn"}), True),
    "d-a04": (frozenset({"tool_pre"}), False),
    "d-a06": (frozenset({"retrieval"}), False),
    "d-a07": (frozenset({"retrieval", "turn"}), True),
    "d-a08": (frozenset({"tool_pre", "turn"}), True),
}
# The register field whose availability decides session grouping (ruling 12).
GROUPING_FIELD = "session.id"
DETECTOR_BY_ID = {d.id: d for d in DETECTORS}
VENDORS = ("azure", "aws")
VENDOR_NAME = {"azure": "Azure", "aws": "AWS"}
YES, NO, MAYBE = "yes", "no", "maybe"


class EvidenceError(ValueError):
    """The evidence file breaks a rule it is held to."""


# --------------------------------------------------------------- evidence --


@lru_cache(maxsize=1)
def evidence() -> dict[str, Any]:
    return yaml.safe_load(EVIDENCE_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def register() -> tuple[dict[str, Any], ...]:
    return tuple(yaml.safe_load(REGISTER_PATH.read_text(encoding="utf-8"))["fields"])


def field_names() -> tuple[str, ...]:
    return tuple(f["name"] for f in register())


def surface(surface_id: str) -> dict[str, Any]:
    for item in evidence()["surfaces"]:
        if item["id"] == surface_id:
            return item
    raise KeyError(surface_id)


def source_numbers() -> set[int]:
    return {s["n"] for s in evidence()["sources"]}


def form_of(row: dict[str, Any]) -> str:
    return row.get("form", "own")


DATE = re.compile(r"\d{1,2} (January|February|March|April|May|June|July|August|September|October|November|December) 20\d\d")


def problems(ev: dict[str, Any] | None = None) -> list[str]:
    """Every way the evidence breaks its rules. Empty when it holds."""
    ev = ev or evidence()
    out: list[str] = []
    numbers = [s["n"] for s in ev["sources"]]
    if numbers != list(range(1, len(numbers) + 1)):
        out.append("sources are not numbered 1 to N in order")
    listed = set(numbers)
    if not DATE.fullmatch(str(ev["retrieved"])):
        out.append(f"retrieval date {ev['retrieved']!r} is not a date")
    for s in ev["sources"]:
        if not (DATE.fullmatch(str(s["updated"])) or s["updated"] == "no date on the page"):
            out.append(f"source {s['n']} has no page date and does not say so")
        if not str(s["url"]).startswith("https://"):
            out.append(f"source {s['n']} has no https URL")
    for qid, q in ev["quotes"].items():
        if q["source"] not in listed:
            out.append(f"quote {qid} cites an unlisted source")
        if len(str(q["text"]).split()) > QUOTE_MAX_WORDS:
            out.append(f"quote {qid} runs over {QUOTE_MAX_WORDS} words")
    cited: set[int] = {q["source"] for q in ev["quotes"].values()}
    names = set(field_names())
    ids = [s["id"] for s in ev["surfaces"]]
    expected_ids = [f"{v}-{layer}" for v in VENDORS for layer in ("as-shipped", *rulings.LAYERS)]
    if ids != expected_ids:
        out.append(f"surfaces are {ids}, not {expected_ids}")
    for s in ev["surfaces"]:
        for key in ("switch_src", "records_src"):
            cited |= set(s[key])
        for qid in s.get("switch_quotes", []):
            if qid not in ev["quotes"]:
                out.append(f"{s['id']} names an unknown quote {qid}")
        for block in ("full_field_list", "full_record_kinds"):
            if s.get(block):
                cited |= set(s[block]["src"])
                for qid in s[block].get("quotes", []):
                    if qid not in ev["quotes"]:
                        out.append(f"{s['id']} {block} names an unknown quote {qid}")
        if set(s["fields"]) != names:
            out.append(f"{s['id']} does not carry exactly the register's fields")
        if tuple(s["events"]) != rulings.EVENT_TYPES:
            out.append(f"{s['id']} does not carry exactly the six event types in order")
        for kind, rows in (("field", s["fields"]), ("event", s["events"])):
            for name, row in rows.items():
                where = f"{s['id']} {name}"
                if row.get("v") not in VERDICT:
                    out.append(f"{where}: verdict {row.get('v')!r}")
                    continue
                form = form_of(row)
                if form not in FORM:
                    out.append(f"{where}: form {form!r}")
                if "path" in row and (form != "body" or row["path"] != "undocumented"):
                    out.append(f"{where}: a path note belongs to a body form only")
                if "partial" in row and not str(row["partial"]).strip():
                    out.append(f"{where}: a partial meaning must state the difference")
                if (row["v"] == "C") != ("setting" in row):
                    out.append(f"{where}: a setting goes with verdict C and only C")
                src = row.get("src") or []
                if not src or not set(src) <= listed:
                    out.append(f"{where}: sources {src} are missing or unlisted")
                cited |= set(src)
                if not str(row.get("note", "")).strip():
                    out.append(f"{where}: no note")
                if row["v"] == "A" and FORM[form] not in rulings.NOT_PRODUCED_BY_VENDOR:
                    basis = s.get("full_field_list") if kind == "field" else s.get("full_record_kinds")
                    if not basis:
                        out.append(f"{where}: absent with no full list on the surface (ruling 3)")
                if FORM[form] in rulings.NOT_PRODUCED_BY_VENDOR and row["v"] != "A":
                    out.append(f"{where}: a value the vendor does not produce is absent (ruling 7)")
    for vendor, item in ev["combined"].items():
        cited |= set(item["src"])
        if vendor not in VENDORS or not isinstance(item["linked"], bool):
            out.append(f"combined entry {vendor} is malformed")
    if cited != listed:
        out.append(f"sources cited {sorted(cited)} differ from sources listed {sorted(listed)}")
    return out


# ---------------------------------------------------------------- columns --


@dataclass(frozen=True)
class Column:
    key: str
    vendor: str
    surfaces: tuple[str, ...]
    parsed: bool
    label: str

    @property
    def combined(self) -> bool:
        return len(self.surfaces) > 1


def columns() -> tuple[Column, ...]:
    out: list[Column] = []
    for v in VENDORS:
        out += [
            Column(f"{v}-as-shipped", v, (f"{v}-as-shipped",), False, "as shipped"),
            Column(f"{v}-model", v, (f"{v}-model",), False, "model layer on"),
            Column(f"{v}-model-parsed", v, (f"{v}-model",), True, "model layer on, body parsed"),
            Column(f"{v}-agent", v, (f"{v}-agent",), False, "agent layer on"),
            Column(f"{v}-agent-parsed", v, (f"{v}-agent",), True, "agent layer on, body parsed"),
            Column(f"{v}-combined", v, (f"{v}-model", f"{v}-agent"), False, "model and agent layers together"),
        ]
    return tuple(out)


def headline(vendor: str) -> Column:
    return next(c for c in columns() if c.key == f"{vendor}-{rulings.HEADLINE_LAYER}")


def row_status(row: dict[str, Any], parsed: bool) -> str:
    """Whether a column counts a row as available: yes, no, or maybe.

    Rulings 2, 6, 7 and 9. Only a default verdict counts under vendor
    defaults. The form must be one the column counts. A partial meaning, a
    body path the pages do not document, or an unconfirmed verdict makes it a
    maybe, which the pass runs both ways.
    """
    counted = rulings.COUNTS_WHEN_BODY_PARSED if parsed else rulings.COUNTS_IN_HEADLINE
    if row["v"] in ("A", "C") or FORM[form_of(row)] not in counted:
        return NO
    if row["v"] == "U" or row.get("partial") or row.get("path") == "undocumented":
        return MAYBE
    return YES


def status(column: Column, kind: str, name: str) -> str:
    (surface_id,) = column.surfaces
    rows = surface(surface_id)["fields" if kind in ("field", "group") else "events"]
    return row_status(rows[name], column.parsed)


# ------------------------------------------------------------------ passes --


def inputs_of(detector: Detector) -> list[tuple[str, str]]:
    """Everything the detector needs: its fields, event types and grouping."""
    events, grouped = DETECTOR_NEEDS[detector.id]
    out = [("field", f) for f in sorted(detector.reads)]
    out += [("event", e) for e in sorted(events)]
    if grouped:
        out.append(("group", GROUPING_FIELD))
    return out


def transform(
    captured: Sequence[dict[str, Any]],
    fields_off: Iterable[str],
    events_off: Iterable[str],
    grouped: bool,
) -> list[list[dict[str, Any]]]:
    """One capture as the vendor would hold it, split into sessions to run."""
    dropped = set(events_off)
    events = [e for e in captured if e.get("event_type") not in dropped]
    events = list(null_fields(events, fields_off))
    return [events] if grouped else [[e] for e in events]


def run_pass(
    detector: Detector,
    captures: Iterable[Capture],
    config: DetectorConfig,
    fields_off: Iterable[str] = (),
    events_off: Iterable[str] = (),
    grouped: bool = True,
) -> frozenset[str]:
    """The run identifiers the detector fires on, under one vendor pass."""
    fields_off, events_off = tuple(fields_off), tuple(events_off)
    fired = set()
    for capture in captures:
        sessions = transform(capture.events, fields_off, events_off, grouped)
        if any(fires(detector, s, config) for s in sessions):
            fired.add(capture.run_id)
    return frozenset(fired)


@dataclass(frozen=True)
class Corpus:
    captures: dict[str, Capture]
    pops: Populations
    config: DetectorConfig

    def of(self, run_ids: Iterable[str]) -> list[Capture]:
        return [self.captures[r] for r in sorted(run_ids)]


def load() -> Corpus:
    captures = load_corpus()
    return Corpus({c.run_id: c for c in captures}, populations(captures), detector_config())


def baseline(corpus: Corpus) -> dict[str, dict[str, Any]]:
    """The un-ablated pass. It must reproduce the M5 sweep's baseline."""
    recorded = json.loads(NECESSITY_JSON.read_text(encoding="utf-8"))["baseline"]
    out = {}
    for cls in CLASSES:
        detector_id = m5.CLASS_DETECTOR[cls]
        if detector_id is None:
            out[cls] = {"detector": None, "n": len(corpus.pops.successful[cls])}
            continue
        d = DETECTOR_BY_ID[detector_id]
        fp_pop = corpus.pops.fp_denominator(d.id)
        fired = run_pass(d, corpus.of(corpus.pops.successful[cls] | fp_pop), corpus.config)
        row = {
            "detector": d.id,
            "n": len(corpus.pops.successful[cls]),
            "detected": len(fired & corpus.pops.successful[cls]),
            "false_positives": len(fired & fp_pop),
            "fp_denominator": len(fp_pop),
        }
        if row["detected"] != recorded["detection"][cls]["detected"]:
            raise EvidenceError(f"{cls}: the baseline pass does not reproduce results/necessity.json")
        if row["false_positives"] != recorded["false_positives"][d.id]["count"]:
            raise EvidenceError(f"{d.id}: the baseline false positives differ from results/necessity.json")
        out[cls] = row
    return out


def _base(code: str) -> str:
    return code[:-1] if code.endswith(m5.CIRCULAR_SUFFIX) and code[:-1] in ("X", "x", ".") else code


def measure(
    corpus: Corpus,
    base: dict[str, Any],
    cls: str,
    available: dict[tuple[str, str], bool],
    column: Column,
) -> dict[str, Any]:
    """One pass for one class, with the named inputs available or not."""
    d = DETECTOR_BY_ID[base["detector"]]
    events, grouped_need = DETECTOR_NEEDS[d.id]
    fields_off = sorted(name for (kind, name), ok in available.items() if kind == "field" and not ok)
    events_off = {name for (kind, name), ok in available.items() if kind == "event" and not ok}
    # Event types the detector does not need are dropped where the surface has
    # no record of them. A test shows this never moves a result.
    events_off |= {t for t in rulings.EVENT_TYPES if t not in events and status(column, "event", t) == NO}
    grouped = available.get(("group", GROUPING_FIELD), True) if grouped_need else True
    fp_pop = corpus.pops.fp_denominator(d.id)
    fired = run_pass(d, corpus.of(corpus.pops.successful[cls] | fp_pop), corpus.config,
                     fields_off, sorted(events_off), grouped)
    detected = len(fired & corpus.pops.successful[cls])
    false_positives = len(fired & fp_pop)
    code = cell_code(
        cls, d.reads, base["n"], base["detected"], detected, d.reads,
        fp=(base["false_positives"], false_positives, base["fp_denominator"]),
        circular=cls in m5.CIRCULAR_CLASSES,
    )
    return {"detected": detected, "false_positives": false_positives, "code": code}


def answer(corpus: Corpus, base: dict[str, Any], cls: str, column: Column) -> dict[str, Any]:
    """A class's answer on one column (rulings 11 to 13)."""
    if cls in m5.ABSENT_CLASSES:
        return {"code": "ab"}
    if column.combined:
        linked = evidence()["combined"][column.vendor]["linked"]
        if not linked:
            return {"code": "nt" if base["n"] == 0 else rulings.UNCONFIRMED_CODE,
                    "reason": "no documented key links the two layers' records"}
        raise EvidenceError("a linked combination has no pass defined; the evidence found none")
    d = DETECTOR_BY_ID[base["detector"]]
    inputs = inputs_of(d)
    states = {inp: status(column, *inp) for inp in inputs}
    maybes = [inp for inp in inputs if states[inp] == MAYBE]
    passes = []
    for choice in itertools.product((True, False), repeat=len(maybes)):
        available = {inp: states[inp] == YES for inp in inputs}
        available.update(zip(maybes, choice))
        result = measure(corpus, base, cls, available, column)
        result["available"] = sorted(f"{k}:{n}" for (k, n), ok in available.items() if ok)
        passes.append(result)
    codes = {_base(p["code"]) for p in passes}
    if len(codes) == 1:
        code = passes[0]["code"]
    else:
        code = rulings.UNCONFIRMED_CODE
    return {
        "code": code,
        "detector": d.id,
        "n": base["n"],
        "inputs": {f"{k}:{n}": states[(k, n)] for k, n in inputs},
        "passes": passes,
    }


def any_detector(corpus: Corpus, column: Column) -> dict[str, dict[str, int]]:
    """Ruling 10: the any-detector result, beside the answer, deciding nothing.

    Two bounds rather than every combination: each maybe taken as available,
    then each taken as not.
    """
    out: dict[str, dict[str, int]] = {}
    for cls in CLASSES:
        n = len(corpus.pops.successful[cls])
        if cls in m5.ABSENT_CLASSES or n == 0:
            continue
        row = {"n": n}
        for bound, keep in (("optimistic", (YES, MAYBE)), ("pessimistic", (YES,))):
            fields_off = [f for f in field_names() if status(column, "field", f) not in keep]
            events_off = [e for e in rulings.EVENT_TYPES if status(column, "event", e) not in keep]
            grouped = status(column, "group", GROUPING_FIELD) in keep
            caught: set[str] = set()
            for d in DETECTORS:
                caught |= run_pass(d, corpus.of(corpus.pops.successful[cls]), corpus.config,
                                   fields_off, events_off, grouped)
            row[bound] = len(caught)
        out[cls] = row
    return out


def restoring_sets(corpus: Corpus, base: dict[str, Any], cls: str, column: Column) -> list[list[str]]:
    """The smallest sets of missing inputs whose addition returns a class to
    its baseline on this column.

    Each candidate set is added with every other missing input left out,
    unsettled ones included, and a set counts only if no smaller counted set
    sits inside it. A detector with two routes to firing has two sets: d-a08
    fires on a single turn's token count, or on a session's count of tool
    calls.
    """
    d = DETECTOR_BY_ID[base["detector"]]
    inputs = inputs_of(d)
    missing = [inp for inp in inputs if status(column, *inp) != YES]
    found: list[frozenset[tuple[str, str]]] = []
    for size in range(1, len(missing) + 1):
        for chosen in itertools.combinations(missing, size):
            chosen_set = frozenset(chosen)
            if any(earlier <= chosen_set for earlier in found):
                continue
            available = {inp: status(column, *inp) == YES or inp in chosen_set for inp in inputs}
            if _base(measure(corpus, base, cls, available, column)["code"]) == ".":
                found.append(chosen_set)
    return [sorted(f"{k}:{n}" for k, n in s) for s in found]


def additions(corpus: Corpus, bases: dict[str, Any], answers: dict[str, Any], vendor: str) -> dict[str, Any]:
    """Ruling 17: the fields a deployment has to add itself, in order.

    Measured first: for each class the headline column does not leave
    detectable, the smallest sets of its counted detector's missing inputs
    whose addition returns it to its baseline, by vendor pass. A field in any
    such set is measured, ordered by how many classes need it, then by tier,
    then register order. Then every other field the headline column does not
    count, by tier and register order.
    """
    column = headline(vendor)
    tiers = {f["name"]: f["tier"] for f in register()}
    order = {name: i for i, name in enumerate(field_names())}
    per_class: dict[str, list[list[str]]] = {}
    needed_fields: dict[str, set[str]] = {}
    for cls in CLASSES:
        code = answers[column.key][cls]["code"]
        if _base(code) in (".", "nt", "ab"):
            continue
        sets = restoring_sets(corpus, bases[cls], cls, column)
        per_class[cls] = sets
        for chosen in sets:
            for item in chosen:
                kind, _, name = item.partition(":")
                if kind in ("field", "group"):
                    needed_fields.setdefault(name, set()).add(cls)
    measured = sorted(
        needed_fields,
        key=lambda f: (-len(needed_fields[f]), TIER_ORDER.index(tiers[f]), order[f]),
    )
    others = sorted(
        (f for f in field_names() if f not in needed_fields and status(column, "field", f) != YES),
        key=lambda f: (TIER_ORDER.index(tiers[f]), order[f]),
    )
    return {
        "column": column.key,
        "restoring_sets": per_class,
        "measured": [{"field": f, "classes": sorted(needed_fields[f]), "tier": tiers[f]} for f in measured],
        "others": [{"field": f, "tier": tiers[f]} for f in others],
    }


def counts(surface_id: str) -> dict[str, Any]:
    s = surface(surface_id)
    security_only = {f["name"] for f in register() if f["security_only"]}
    out: dict[str, Any] = {"fields": {}, "security_only": {}, "forms": {}, "events": {}}
    for name, row in s["fields"].items():
        verdict = VERDICT[row["v"]]
        out["fields"][verdict] = out["fields"].get(verdict, 0) + 1
        if name in security_only:
            out["security_only"][verdict] = out["security_only"].get(verdict, 0) + 1
        form = FORM[form_of(row)]
        out["forms"][form] = out["forms"].get(form, 0) + 1
    for name, row in s["events"].items():
        out["events"][name] = VERDICT[row["v"]]
    return out


def build(corpus: Corpus | None = None) -> dict[str, Any]:
    found = problems()
    if found:
        raise EvidenceError("; ".join(found))
    corpus = corpus or load()
    bases = baseline(corpus)
    answers = {c.key: {cls: answer(corpus, bases[cls], cls, c) for cls in CLASSES} for c in columns()}
    return {
        "about": "The M7 vendor gap analysis: verdicts from vendor_gap/evidence.yaml, class answers from vendor passes over the captures. Identifiers, codes and counts only.",
        "command": COMMAND,
        "retrieved": evidence()["retrieved"],
        "model_calls": rulings.MODEL_CALLS,
        "cloud_resources": rulings.CLOUD_RESOURCES,
        "detectors_frozen_at": "freeze-m4",
        "baseline": bases,
        "surfaces": {s["id"]: counts(s["id"]) for s in evidence()["surfaces"]},
        "columns": {c.key: {"vendor": c.vendor, "surfaces": list(c.surfaces), "parsed": c.parsed, "label": c.label}
                    for c in columns()},
        "answers": answers,
        "any_detector": {c.key: any_detector(corpus, c) for c in columns() if not c.combined},
        "additions": {v: additions(corpus, bases, answers, v) for v in VENDORS},
    }


def dumps(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


# --------------------------------------------------------------- the page --

LEGEND_CODES = {
    ".": "stays detectable: no measurable effect",
    "x": "degrades materially",
    "X": "becomes undetectable",
    "uc": "unconfirmed: the answer depends on what the pages do not settle",
    "nt": "not computable: the class has no successful trial",
    "ab": "absent from the corpus",
}


def _cite(src: Iterable[int]) -> str:
    return "".join(f"[{n}]" for n in src)


FORM_WORDS = {
    "own": "as its own field",
    "body": "inside a request or response body",
    "content": "only as content the application wrote",
    "caller": "held by the deployment, or supplied by it",
    "derived": "derivable by the deployment",
}


def block_sources() -> str:
    lines = ["| # | Source | Page updated | Retrieved |", "|---|---|---|---|"]
    for s in evidence()["sources"]:
        where = s["url"]
        if s.get("requested"):
            where += f", requested at {s['requested']}"
        note = f" ({s['note']})" if s.get("note") else ""
        lines.append(f"| {s['n']} | {s['publisher']}, *{s['title']}*, {where}{note} | {s['updated']} | {evidence()['retrieved']} |")
    return "\n".join(lines)


def block_quotes() -> str:
    lines = []
    for qid, q in evidence()["quotes"].items():
        lines.append(f"- [{q['source']}] *{q['text']}*")
    return "\n".join(lines)


def block_surfaces() -> str:
    lines = ["| Vendor | Layer | Surface | Switch | What it records |", "|---|---|---|---|---|"]
    for s in evidence()["surfaces"]:
        layer = s["layer"].replace("_", " ")
        lines.append(
            f"| {VENDOR_NAME[s['vendor']]} | {layer} | {s['name']} | {s['switch']} {_cite(s['switch_src'])} "
            f"| {' '.join(str(s['records']).split())} {_cite(s['records_src'])} |"
        )
    return "\n".join(lines)


def block_counts(doc: dict[str, Any]) -> str:
    order = list(rulings.VERDICTS)
    head = "| Surface | " + " | ".join(v.replace("_", " ") for v in order) + " | Security-only fields, in the same order |"
    lines = [head, "|---|" + "---|" * len(order) + "---|"]
    for s in evidence()["surfaces"]:
        c = doc["surfaces"][s["id"]]
        sec = ", ".join(str(c["security_only"].get(v, 0)) for v in order)
        lines.append(f"| {s['name']} | " + " | ".join(str(c["fields"].get(v, 0)) for v in order) + f" | {sec} |")
    return "\n".join(lines)


def block_classes(doc: dict[str, Any]) -> str:
    cols = [c for c in columns()]
    head = "| Class | Counted detector | n | " + " | ".join(f"{VENDOR_NAME[c.vendor]}: {c.label}" for c in cols) + " |"
    lines = [head, "|---|---|---|" + "---|" * len(cols)]
    for cls in CLASSES:
        base = doc["baseline"][cls]
        label = cls + ("\\*" if cls in m5.HOLDOUT_CLASSES else "")
        if base["n"] == 1:
            label += " n=1"
        if cls in m5.CIRCULAR_CLASSES:
            label += " c"
        cells = [f"`{doc['answers'][c.key][cls]['code']}`" for c in cols]
        lines.append(f"| {label} | {base['detector'] or 'none'} | {base['n']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def block_passes(doc: dict[str, Any]) -> str:
    """For each computable class on each single-surface column: what the
    counted detector could still use, and what it caught."""
    lines = ["| Column | Class | Inputs not counted, or unsettled | Caught, of n | False positives |",
             "|---|---|---|---|---|"]
    for c in columns():
        if c.combined:
            continue
        for cls in CLASSES:
            a = doc["answers"][c.key][cls]
            if "passes" not in a or a["n"] == 0:
                continue
            missing = [f"{k} ({s})" for k, s in a["inputs"].items() if s != YES]
            caught = sorted({p["detected"] for p in a["passes"]})
            fps = sorted({p["false_positives"] for p in a["passes"]})
            span = lambda xs: str(xs[0]) if len(xs) == 1 else f"{xs[0]} to {xs[-1]}"
            lines.append(f"| {VENDOR_NAME[c.vendor]}: {c.label} | {cls} | {', '.join(missing) or 'none'} "
                         f"| {span(caught)} of {a['n']} | {span(fps)} of {doc['baseline'][cls]['fp_denominator']} |")
    return "\n".join(lines)


def block_additions(doc: dict[str, Any]) -> str:
    lines = []
    for v in VENDORS:
        a = doc["additions"][v]
        lines.append(f"**{VENDOR_NAME[v]}, on the headline column ({headline(v).label}).**")
        lines.append("")
        lines.append("What returns each class to its baseline, by vendor pass. Each line is one smallest set; "
                     "where a class has two, either will do.")
        lines.append("")
        for cls, sets in a["restoring_sets"].items():
            described = []
            for chosen in sets:
                parts = []
                for item in chosen:
                    kind, _, name = item.partition(":")
                    parts.append(f"`{name}` records" if kind == "event" else f"`{name}`")
                described.append(parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1])
            lines.append(f"- {cls}: " + ("; or ".join(described) if described else "no set found") + ".")
        lines.append("")
        lines.append("Measured fields, in order:")
        lines.append("")
        for i, item in enumerate(a["measured"], 1):
            lines.append(f"{i}. `{item['field']}`, {item['tier']}, in a set for {', '.join(item['classes'])}")
        if not a["measured"]:
            lines.append("None.")
        lines.append("")
        rest = ", ".join(f"`{o['field']}` ({o['tier']})" for o in a["others"])
        lines.append(f"Then, by tier and register order: {rest}.")
        lines.append("")
    return "\n".join(lines).rstrip()


MEASURED_CLASSES = ("A5", "A6", "A7", "A8", "A9")


def block_headline(doc: dict[str, Any]) -> str:
    """The answer in words, computed from the answers so it cannot drift."""
    single = [c for c in columns() if not c.combined]
    stays = [(c.key, cls) for c in single for cls in MEASURED_CLASSES
             if _base(doc["answers"][c.key][cls]["code"]) == "."]
    lines = []
    for v in VENDORS:
        col = headline(v)
        parts = [f"{cls} `{doc['answers'][col.key][cls]['code']}`" for cls in MEASURED_CLASSES]
        lines.append(f"- **{VENDOR_NAME[v]}, {col.label}:** " + ", ".join(parts) + ".")
    lines.append("")
    if stays:
        lines.append("Stays detectable on a single surface: " + ", ".join(f"{cls} on {key}" for key, cls in stays) + ".")
    else:
        lines.append("**No class stays detectable on any single surface of either vendor**, as shipped or switched "
                     "on, with or without the bodies parsed.")
    by_code: dict[str, set[str]] = {}
    for cls in MEASURED_CLASSES:
        codes = sorted({doc["answers"][c.key][cls]["code"] for c in single})
        by_code.setdefault(", ".join(f"`{x}`" for x in codes), set()).add(cls)
    lines.append("Across the ten single-surface columns: " + "; ".join(
        f"{', '.join(sorted(classes))} {'reads' if len(classes) == 1 else 'read'} {codes}"
        for codes, classes in sorted(by_code.items(), key=lambda kv: sorted(kv[1]))) + ".")
    security_only = [f["name"] for f in register() if f["security_only"]]
    counted = sorted({f for c in single for f in security_only if status(c, "field", f) == YES})
    lines.append("")
    forms = sorted({FORM[form_of(s["fields"][f])].replace("_", " ")
                    for s in evidence()["surfaces"] for f in security_only})
    verdicts = sorted({VERDICT[s["fields"][f]["v"]].replace("_", " ")
                       for s in evidence()["surfaces"] for f in security_only})
    lines.append(f"**Security-only fields a vendor column counts as available: {len(counted)} of {len(security_only)}.**"
                 + (" " + ", ".join(f"`{f}`" for f in counted) + "." if counted else "")
                 + f" On all six surfaces every one reads {' or '.join(verdicts)}, in the form "
                 + " or ".join(forms) + ".")
    return "\n".join(lines)


def blocks(doc: dict[str, Any]) -> dict[str, str]:
    """The blocks the page carries. Since the page was condensed on 2 October
    2026, the field-by-field tables, the deciding rows, the passes, the combined
    answer and the any-detector table stay in results/vendor-gap.json and
    vendor_gap/evidence.yaml, and main() still prints the passes."""
    return {
        "headline": block_headline(doc),
        "sources": block_sources(),
        "quotes": block_quotes(),
        "surfaces": block_surfaces(),
        "counts": block_counts(doc),
        "classes": block_classes(doc),
        "additions": block_additions(doc),
    }


def render_doc(text: str, doc: dict[str, Any], names: Sequence[str] | None = None) -> str:
    """The page with its generated blocks rewritten; `names` limits it to the
    blocks one page carries, and every named block must be there once."""
    for name, body in blocks(doc).items():
        if names is not None and name not in names:
            continue
        pattern = re.compile(
            rf"(<!-- generated:{re.escape(name)} -->\n)(?:.*?\n)?(<!-- /generated:{re.escape(name)} -->)", re.S
        )
        if len(pattern.findall(text)) != 1:
            raise EvidenceError(f"the doc does not have exactly one generated block {name!r}")
        text = pattern.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)
    return text


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="write results/vendor-gap.json and the doc's generated blocks")
    args = parser.parse_args(argv)
    doc = build()
    print(block_classes(doc))
    print()
    print(block_passes(doc))
    if args.write:
        RESULTS_PATH.write_text(dumps(doc), encoding="utf-8")
        for path, names in PAGES.items():
            path.write_text(render_doc(path.read_text(encoding="utf-8"), doc, names), encoding="utf-8")
        print(f"\nwrote {rulings.RESULTS}, {rulings.DOC} and its {len(PAGES) - 1} topic pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
