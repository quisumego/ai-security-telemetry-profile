"""The necessity matrix, the tiering rule applied to it, and the headline claim.

    .venv/bin/python -m ablation.matrix                 # print the matrix and the tiers
    .venv/bin/python -m ablation.matrix --write         # write results/, from a clean tree only
    .venv/bin/python -m ablation.matrix --apply-tiers   # write the recorded tiers into the register

**The rule is applied mechanically.** The tiering rule is `docs/methodology.md`
Section 3 and the materiality threshold is Section 4, both fixed before the
first scored run. Their two numbers appear here only as constants that cite
them. What those sections leave open was ruled by the owner before any sweep
code existed, and is read from `ablation/rulings.py`.

**What a cell is computed from.** For a field and a class: n, the class's
successful trials; the number the counted detector caught before the field was
nulled; the number after; and that detector's false positive count before and
after, over its ruled benign denominator. Nothing else.

**What is written.** `results/necessity.json` holds identifiers and counts
only, never event content, so no canary value and no attacker host can reach
it. `results/necessity-matrix.md` is rendered from the JSON alone, so the two
cannot disagree. `--write` refuses a dirty tree and records the commit the sweep
ran against.
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import yaml

from ablation import rulings
from ablation.ablate import (
    BASELINE,
    CLASSES,
    AblationError,
    Capture,
    ablations,
    load_corpus,
    sweep,
)
from detect.detectors import A8_TOOL_CALLS, DETECTORS
from detect.evaluate import detector_config
from lab.config import REGISTER_PATH, REPO_ROOT

RESULTS_DIR = REPO_ROOT / "results"
NECESSITY_JSON = RESULTS_DIR / "necessity.json"
NECESSITY_MD = RESULTS_DIR / "necessity-matrix.md"
BASELINE_JSON = RESULTS_DIR / "baseline.json"
COMMAND = ".venv/bin/python -m ablation.matrix --write"

# docs/methodology.md Section 4, condition 1: a fall of 20 percentage points or
# more in the detection rate.
MATERIAL_FALL_POINTS = 20
# docs/methodology.md Section 4, condition 2: a false positive rate above
# 10 per cent.
FP_CEILING_PERCENT = 10

READS = {d.id: d.reads for d in DETECTORS}
TIER_ORDER = ("required", "recommended", "optional", "not_required")
TIER_BASIS = {
    "required": "the field's removal makes at least one class undetectable",
    "recommended": "the field's removal materially degrades detection for at least one class, nothing goes dark",
    "optional": "no measurable detection effect; a stated justification in its M0 rationale, ruled 2026-09-22",
    "not_required": "no measurable detection effect and no stated justification",
}
MEASURED = ("X", "x", ".")
CODE_ORDER = ("X", "x", ".", "nr", "nt", "ab")
MAPPING_ORDER = ("full", "partial", "none, security only", "none, other")


# ------------------------------------------------------------ populations --


@dataclass(frozen=True)
class Populations:
    trials: dict[str, frozenset[str]]
    successful: dict[str, frozenset[str]]
    benign: frozenset[str]
    benign_b1: frozenset[str]

    def fp_denominator(self, detector_id: str) -> frozenset[str]:
        which = rulings.FP_DENOMINATOR.get(detector_id, rulings.FP_DENOMINATOR_DEFAULT)
        return self.benign_b1 if which == "b1" else self.benign


def populations(captures: Sequence[Capture]) -> Populations:
    trials = {c: frozenset(x.run_id for x in captures if x.attack_class == c) for c in CLASSES}
    successful = {
        c: frozenset(x.run_id for x in captures if x.attack_class == c and x.successful)
        for c in CLASSES
    }
    benign = frozenset(x.run_id for x in captures if x.benign_type)
    b1 = frozenset(x.run_id for x in captures if x.benign_type == "b1")
    return Populations(trials, successful, benign, b1)


# ------------------------------------------------------------------ cells --


def base_code(code: str) -> str:
    """A cell's state without the circular suffix."""
    if code.endswith(rulings.CIRCULAR_SUFFIX) and code[:-1] in MEASURED:
        return code[:-1]
    return code


def fp_limb(before: int, after: int, denominator: int) -> bool:
    """Methodology Section 4, condition 2, as ruled: at or below the ceiling
    before nulling, above it after."""
    ceiling = FP_CEILING_PERCENT * denominator
    return before * 100 <= ceiling and after * 100 > ceiling


def cell_code(
    attack_class: str,
    nulled: Iterable[str],
    n: int,
    before: int,
    after: int,
    reads: frozenset[str],
    fp: tuple[int, int, int] | None = None,
    circular: bool = False,
) -> str:
    """One cell. `fp` is the counted detector's false positives as
    (before, after, denominator), or None where there is no counted detector."""
    if attack_class in rulings.ABSENT_CLASSES:
        return "ab"
    limb2 = fp is not None and fp_limb(*fp)
    if n == 0:
        return "x" if limb2 else "nt"
    if not set(nulled) & reads:
        if before != after or (fp is not None and fp[0] != fp[1]):
            raise AblationError(f"{attack_class}: a field its detector does not read moved a result")
        return "nr"
    if before > 0 and after == 0:
        code = "X"
    elif after > 0 and 100 * (before - after) >= MATERIAL_FALL_POINTS * n:
        code = "x"
    elif limb2:
        code = "x"
    else:
        code = "."
    return code + rulings.CIRCULAR_SUFFIX if circular else code


def tier_for(codes: Iterable[str], justified: bool) -> str:
    """Methodology Section 3, applied to one row of the single-field matrix."""
    bases = {base_code(c) for c in codes}
    if "X" in bases:
        return "required"
    if "x" in bases:
        return "recommended"
    return "optional" if justified else "not_required"


def _effect(code: str) -> int:
    return {"X": 2, "x": 1}.get(base_code(code), 0)


# ------------------------------------------------------- the whole matrix --


def _load_register() -> list[dict[str, Any]]:
    return yaml.safe_load(REGISTER_PATH.read_text(encoding="utf-8"))["fields"]


def _measure(fired: dict[str, frozenset[str]], pops: Populations) -> dict[str, Any]:
    union = frozenset().union(*fired.values())
    detection = {}
    for cls in CLASSES:
        detector = rulings.CLASS_DETECTOR[cls]
        detection[cls] = {
            "detected": len(fired[detector] & pops.successful[cls]) if detector else 0,
            "any_detected": len(union & pops.successful[cls]),
        }
    false_positives = {
        d: {
            "count": len(fired[d] & pops.fp_denominator(d)),
            "denominator": len(pops.fp_denominator(d)),
            "all": len(fired[d] & pops.benign),
        }
        for d in sorted(fired)
    }
    all_trials = {}
    for d in sorted(fired):
        row = {cls: len(fired[d] & pops.trials[cls]) for cls in CLASSES}
        row = {cls: v for cls, v in row.items() if v}
        if row:
            all_trials[d] = row
    return {"detection": detection, "false_positives": false_positives, "firing_all_trials": all_trials}


def _check_baseline(fired: dict[str, frozenset[str]], pops: Populations) -> None:
    """The un-ablated pass must reproduce results/baseline.json, or nothing
    measured against it would mean what it claims."""
    recorded = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
    problems = []
    for cls, row in recorded["per_class"].items():
        if len(pops.successful[cls]) != row["successes"]:
            problems.append(f"{cls} successes")
        if row["detector"] and len(fired[row["detector"]] & pops.successful[cls]) != row["detected"]:
            problems.append(f"{cls} detected")
    for d, row in recorded["per_detector"].items():
        if len(fired[d] & pops.benign) != row["false_positives"]:
            problems.append(f"{d} false positives")
        own = row["attack_class"]
        for cls in CLASSES:
            if cls != own and len(fired[d] & pops.trials[cls]) != row["cross_class"].get(cls, 0):
                problems.append(f"{d} firing on {cls}")
    for cls, row in recorded["holdout_generalisation"].items():
        for d in READS:
            hit = row["fired"].get(d, {"on_successful": 0, "on_all": 0})
            if len(fired[d] & pops.successful[cls]) != hit["on_successful"]:
                problems.append(f"{d} on successful {cls}")
            if len(fired[d] & pops.trials[cls]) != hit["on_all"]:
                problems.append(f"{d} on all {cls}")
    if problems:
        raise AblationError(f"the baseline pass does not reproduce results/baseline.json: {problems}")


def _cells(
    nulled: Sequence[str],
    base: dict[str, Any],
    after: dict[str, Any],
    pops: Populations,
    baseline_fired: dict[str, frozenset[str]],
) -> dict[str, dict[str, Any]]:
    out = {}
    for cls in CLASSES:
        n = len(pops.successful[cls])
        detector = rulings.CLASS_DETECTOR[cls]
        reads = READS[detector] if detector else frozenset()
        fp = None
        if detector:
            fp = (
                base["false_positives"][detector]["count"],
                after["false_positives"][detector]["count"],
                base["false_positives"][detector]["denominator"],
            )
        before_n = base["detection"][cls]["detected"]
        after_n = after["detection"][cls]["detected"]
        code = cell_code(cls, nulled, n, before_n, after_n, reads, fp,
                         circular=cls in rulings.CIRCULAR_CLASSES)
        reason = None
        if base_code(code) == "X":
            reason = "dark"
        elif base_code(code) == "x":
            reason = "fall" if after_n > 0 and 100 * (before_n - after_n) >= MATERIAL_FALL_POINTS * n else "false_positives"
        contributing = frozenset().union(*(
            READS[d] for d, ids in baseline_fired.items() if ids & pops.successful[cls]
        )) if n else frozenset()
        any_before = base["detection"][cls]["any_detected"]
        any_after = after["detection"][cls]["any_detected"]
        any_code = cell_code(cls, nulled, n, any_before, any_after, contributing)
        out[cls] = {
            "cell": code,
            "n": n,
            "before": before_n,
            "after": after_n,
            "reason": reason,
            "any_cell": any_code,
            "any_before": any_before,
            "any_after": any_after,
        }
    return out


def _deciding(cls: str, c: dict[str, Any], fp: dict[str, Any] | None) -> str:
    if c["reason"] == "false_positives" and fp is not None:
        return f"{cls} {c['cell']} false positives {fp['before']}/{fp['denominator']} to {fp['after']}/{fp['denominator']}"
    return f"{cls} {c['cell']} {c['before']}/{c['n']} to {c['after']}/{c['n']}"


def _verdict(fields: list[dict[str, Any]], tiers: dict[str, str], n_by_class: dict[str, int]) -> dict[str, Any]:
    """Methodology Section 9, read as the owner ruled on 22 September 2026."""
    security_only = [f for f in fields if f["security_only"]]
    tested, untested = [], {}
    for f in security_only:
        counted = [
            d for cls, d in rulings.CLASS_DETECTOR.items()
            if d and n_by_class[cls] >= 1 and f["name"] in READS[d]
        ]
        if counted:
            tested.append(f["name"])
        else:
            readers = sorted(d for d, reads in READS.items() if f["name"] in reads)
            untested[f["name"]] = (
                f"read only by {', '.join(readers)}, whose classes have no successful trial"
                if readers else "read by no detector"
            )
    required = [f for f in fields if tiers[f["name"]] == "required"]
    by_mapping = {"full": [], "partial": [], "none, security only": [], "none, other": []}
    for f in required:
        key = f["otel"] if f["otel"] != "none" else ("none, security only" if f["security_only"] else "none, other")
        by_mapping[key].append(f["name"])
    covered = [f["name"] for f in required if f["otel"] == rulings.COVERED_MAPPING]
    refuted = bool(required) and 2 * len(covered) > len(required)
    failed = sorted(f["name"] for f in security_only if tiers[f["name"]] in ("optional", "not_required"))
    weakened = len(failed) >= rulings.SEVERAL
    literal = "refuted" if refuted else "weakened" if weakened else "supported"
    if refuted:
        headline = "refuted"
    elif len(tested) < rulings.TESTED_MAJORITY:
        headline = "undertested"
    else:
        headline = literal
    return {
        "headline": headline,
        "section_9_as_written": literal,
        "refuted_limb": {"holds": refuted, "required": len(required), "covered": covered},
        "weakened_limb": {"holds": weakened, "security_only_optional_or_not_required": failed},
        "required_by_mapping": by_mapping,
        "security_only_tested": sorted(tested),
        "security_only_untested": dict(sorted(untested.items())),
    }


def build(captures: Sequence[Capture] | None = None, check_baseline: bool = True) -> dict[str, Any]:
    """Run the whole sweep and derive everything the results files hold,
    except the commit, the tree state and the date.

    `check_baseline` is off only for synthetic captures in the tests, which
    cannot reproduce the recorded baseline and are not meant to."""
    fields = _load_register()
    names = [f["name"] for f in fields]
    groups = {f["name"]: f["group"] for f in fields}
    captures = load_corpus() if captures is None else captures
    passes = ablations(names, groups)
    fired = sweep(captures, detector_config(), passes)
    pops = populations(captures)
    if check_baseline:
        _check_baseline(fired[BASELINE], pops)

    measured = {a.key: _measure(fired[a.key], pops) for a in passes}
    base = measured[BASELINE]
    n_by_class = {cls: len(pops.successful[cls]) for cls in CLASSES}

    single, tiers = {}, {}
    for f in fields:
        name = f["name"]
        after = measured[name]
        cells = _cells((name,), base, after, pops, fired[BASELINE])
        fps = {
            d: {
                "before": base["false_positives"][d]["count"],
                "after": after["false_positives"][d]["count"],
                "denominator": base["false_positives"][d]["denominator"],
                "all_before": base["false_positives"][d]["all"],
                "all_after": after["false_positives"][d]["all"],
            }
            for d in sorted(READS)
        }
        single[name] = {"cells": cells, "false_positives": fps, "firing_all_trials": after["firing_all_trials"]}
        justified = name in rulings.STATED_JUSTIFICATION
        tier = tier_for((c["cell"] for c in cells.values()), justified)
        deciding = [
            _deciding(cls, c, fps.get(rulings.CLASS_DETECTOR[cls] or ""))
            for cls, c in cells.items()
            if base_code(c["cell"]) == {"required": "X", "recommended": "x"}.get(tier)
        ]
        tiers[name] = {
            "tier": tier,
            "predicted_tier": f["predicted_tier"],
            "match": tier == f["predicted_tier"],
            "basis": TIER_BASIS[tier],
            "cells": deciding,
            "security_only": f["security_only"],
            "otel": f["otel"],
        }

    pairs, beyond = {}, []
    for a in passes:
        if len(a.fields) != 2:
            continue
        cells = _cells(a.fields, base, measured[a.key], pops, fired[BASELINE])
        first, second = (single[x]["cells"] for x in a.fields)
        moved = [
            cls for cls in CLASSES
            if _effect(cells[cls]["cell"]) > max(_effect(first[cls]["cell"]), _effect(second[cls]["cell"]))
        ]
        pairs[a.key] = {"fields": list(a.fields), "cells": {cls: c["cell"] for cls, c in cells.items()},
                        "beyond_singles": moved}
        if moved:
            beyond.append(a.key)

    tool_calls = sorted(
        sum(1 for e in x.events if e.get("event_type") == "tool_pre")
        for x in captures if x.attack_class == "A8" and x.successful
    )
    return {
        "about": (
            "The M5 ablation sweep. Identifiers and counts only. Rendered as "
            "results/necessity-matrix.md. Tiering rule and materiality threshold: "
            "docs/methodology.md Sections 3 and 4. Rulings: ablation/rulings.py."
        ),
        "command": COMMAND,
        "detectors_frozen_at": "freeze-m4",
        "methodology": {
            "material_fall_points": MATERIAL_FALL_POINTS,
            "fp_ceiling_percent": FP_CEILING_PERCENT,
        },
        "rulings": {
            "ruled_date": rulings.RULED_DATE,
            "class_detector": rulings.CLASS_DETECTOR,
            "fp_denominator": {d: rulings.FP_DENOMINATOR.get(d, rulings.FP_DENOMINATOR_DEFAULT) for d in sorted(READS)},
            "stated_justification": sorted(rulings.STATED_JUSTIFICATION),
            "pairs_feed_tiers": rulings.PAIRS_FEED_TIERS,
            "covered_mapping": rulings.COVERED_MAPPING,
            "several": rulings.SEVERAL,
            "tested_majority": rulings.TESTED_MAJORITY,
            "cell_codes": rulings.CELL_CODES,
        },
        "classes": {
            cls: {
                "trials": len(pops.trials[cls]),
                "successful": n_by_class[cls],
                "detector": rulings.CLASS_DETECTOR[cls],
                "holdout": cls in rulings.HOLDOUT_CLASSES,
                "circular": cls in rulings.CIRCULAR_CLASSES,
                "absent": cls in rulings.ABSENT_CLASSES,
            }
            for cls in CLASSES
        },
        "benign": {"all": len(pops.benign), "b1": len(pops.benign_b1)},
        "detectors": {d.id: {"attack_class": d.attack_class, "reads": sorted(d.reads)} for d in DETECTORS},
        "passes": {"single": len(names), "pairs": len(pairs)},
        "field_order": names,
        "baseline": base,
        "single": single,
        "pairs": pairs,
        "pairs_beyond_singles": beyond,
        "circular": {
            "A8": {
                "detector": "d-a08",
                "tool_call_threshold": A8_TOOL_CALLS,
                "tool_pre_events_per_successful_trial": tool_calls,
            }
        },
        "tiers": tiers,
        "verdict": _verdict(fields, {k: v["tier"] for k, v in tiers.items()}, n_by_class),
    }


# -------------------------------------------------------------- rendering --


def _header(cls: str, info: dict[str, Any]) -> str:
    label = cls + ("\\*" if info["holdout"] else "")
    if info["successful"] == 1:
        label += " n=1"
    if info["circular"]:
        label += " c"
    return label


def _fp_text(row: dict[str, Any], over_all: bool = False) -> str:
    before, after = (row["all_before"], row["all_after"]) if over_all else (row["before"], row["after"])
    if before == after:
        return str(before)
    return f"{before} to {after}"


def render_markdown(doc: dict[str, Any]) -> str:
    classes = doc["classes"]
    tiers = doc["tiers"]
    verdict = doc["verdict"]
    headers = [_header(c, classes[c]) for c in CLASSES]
    lines: list[str] = []
    add = lines.append

    add("# Necessity matrix")
    add("")
    add(f"Generated by `{doc['command']}` from `results/necessity.json`. Do not edit by hand.")
    add("")
    add("| | |")
    add("|---|---|")
    add(f"| Sweep ran against commit | `{doc['commit']}` |")
    add(f"| Date | {doc['date']} |")
    add(f"| Detectors | the seven frozen at `{doc['detectors_frozen_at']}`, unchanged |")
    add(f"| Captures | {sum(c['trials'] for c in classes.values())} attack trials and "
        f"{doc['benign']['all']} benign sessions under `runs/`, read only, never written |")
    add(f"| Passes | the baseline, {doc['passes']['single']} single fields, "
        f"{doc['passes']['pairs']} pairs within a group |")
    add("| Model calls | none |")
    add("")
    add("The tiering rule and the materiality threshold are those of `docs/methodology.md` "
        "Sections 3 and 4, applied mechanically. What they leave open was ruled by the owner on "
        f"{doc['rulings']['ruled_date']} and committed in `ablation/rulings.py` before any sweep code existed.")
    add("")

    add("## How to read a cell")
    add("")
    add("| Code | Meaning |")
    add("|---|---|")
    for code in CODE_ORDER:
        add(f"| `{code}` | {doc['rulings']['cell_codes'][code]} |")
    add("| suffix `c` | circular: the detector counted for this class uses the class's own oracle thresholds |")
    add("| `n=1` in a header | the class has one successful trial, so every cell in it rests on one session |")
    add("| `*` in a header | holdout, opened at M4 scoring after `freeze-m4` |")
    add("")
    add("`X`, `x` and `.` are methodology Section 4's three states. The other codes mark cells that could not "
        "have moved, so that a cell with no evidence is never read as a field tested and found irrelevant.")
    add("")

    add("## The columns")
    add("")
    add("| Class | Successful trials | Detector counted |")
    add("|---|---|---|")
    for cls in CLASSES:
        info = classes[cls]
        add(f"| {_header(cls, info)} | {info['successful']}/{info['trials']} | {info['detector'] or 'none'} |")
    add("")
    add(f"False positives are counted over the {doc['benign']['all']} benign sessions, except `d-a04`, "
        f"counted over the {doc['benign']['b1']} b1 sessions of ruling 12.")
    add("")

    add("## The matrix: single fields, which decide the tiers")
    add("")
    add("| Field | OTel | Security only | " + " | ".join(headers) + " | Tier |")
    add("|---|---|---|" + "---|" * len(CLASSES) + "---|")
    for name in doc["field_order"]:
        row = doc["single"][name]
        cells = " | ".join(f"`{row['cells'][c]['cell']}`" for c in CLASSES)
        so = "yes" if tiers[name]["security_only"] else ""
        add(f"| `{name}` | {tiers[name]['otel']} | {so} | {cells} | {tiers[name]['tier']} |")
    add("")

    add("## Any detector in the frozen set")
    add("")
    add("Recorded beside the matrix and deciding nothing. A cell here counts a class detected if any of "
        "the seven detectors fires on a successful trial, and a field as read if any detector that fires "
        "on the class at baseline reads it.")
    add("")
    add("| Field | " + " | ".join(headers) + " |")
    add("|---|" + "---|" * len(CLASSES))
    for name in doc["field_order"]:
        row = doc["single"][name]
        add(f"| `{name}` | " + " | ".join(f"`{row['cells'][c]['any_cell']}`" for c in CLASSES) + " |")
    add("")

    add("## False positives per detector, before and after nulling")
    add("")
    # Each detector over its ruled denominator, and beside it, for a detector
    # ruled onto b1, the same detector over all the benign sessions (ruling 3).
    columns: list[tuple[str, bool, str]] = []
    for d in doc["detectors"]:
        den = doc["baseline"]["false_positives"][d]["denominator"]
        if doc["rulings"]["fp_denominator"][d] == "b1":
            columns.append((d, False, f"{d} (b1, of {den})"))
            columns.append((d, True, f"{d} (all, of {doc['benign']['all']}, not a rate)"))
        else:
            columns.append((d, False, f"{d} (of {den})"))
    add("A single number means nulling the field left the count unchanged. Measured for every field and "
        "every detector, including the classes where detection cannot move. The `d-a04` figure over all "
        "the benign sessions is the task-set mismatch M3 recorded, shown beside the b1 rate as ruled.")
    add("")
    add("| Field | " + " | ".join(label for _, _, label in columns) + " |")
    add("|---|" + "---|" * len(columns))
    for name in doc["field_order"]:
        row = doc["single"][name]
        add(f"| `{name}` | " + " | ".join(
            _fp_text(row["false_positives"][d], over_all) for d, over_all, _ in columns) + " |")
    add("")

    add("## Pairs within a group")
    add("")
    add(f"{doc['passes']['pairs']} pairs were nulled together. They are reported and do not feed a tier, "
        "as ruled.")
    add("")
    if doc["pairs_beyond_singles"]:
        add("Pairs that move a class further than either field does alone:")
        add("")
        for key in doc["pairs_beyond_singles"]:
            pair = doc["pairs"][key]
            moved = ", ".join(f"{c} `{pair['cells'][c]}`" for c in pair["beyond_singles"])
            add(f"- `{key}`: {moved}")
    else:
        add("**No pair moves any class further than either of its fields does alone.**")
    add("")

    add("## Tiers")
    add("")
    add("| Field | OTel | Security only | Predicted | Computed | Match | Deciding cells, or basis |")
    add("|---|---|---|---|---|---|---|")
    for name in doc["field_order"]:
        t = tiers[name]
        so = "yes" if t["security_only"] else ""
        basis = "; ".join(t["cells"]) if t["cells"] else t["basis"]
        add(f"| `{name}` | {t['otel']} | {so} | {t['predicted_tier']} | **{t['tier']}** | "
            f"{'yes' if t['match'] else 'no'} | {basis} |")
    add("")
    matches = sum(1 for t in tiers.values() if t["match"])
    add(f"Predicted and computed agree on **{matches} of {len(tiers)}** fields. Neither side is adjusted "
        "to fit the other: `predicted_tier` stays in the register as it was registered.")
    add("")
    counts = {tier: sum(1 for t in tiers.values() if t["tier"] == tier) for tier in TIER_ORDER}
    add("| Tier | Fields |")
    add("|---|---|")
    for tier in TIER_ORDER:
        add(f"| {tier} | {counts[tier]} |")
    add("")

    add("## Fields tiered not required")
    add("")
    not_required = [n for n in doc["field_order"] if tiers[n]["tier"] == "not_required"]
    if not not_required:
        add("None.")
    for name in not_required:
        add(f"- `{name}`" + (" **(security only)**" if tiers[name]["security_only"] else ""))
    add("")

    add("## The headline claim, methodology Section 9")
    add("")
    add(f"**Headline: {verdict['headline']}.** Section 9 as written: **{verdict['section_9_as_written']}**.")
    add("")
    refuted = verdict["refuted_limb"]
    weakened = verdict["weakened_limb"]
    add(f"- Refuted limb, the Required fields predominantly ones the conventions cover: "
        f"{'holds' if refuted['holds'] else 'does not hold'}. {refuted['required']} fields tier Required, "
        f"{len(refuted['covered'])} of them with an `otel: full` mapping.")
    add(f"- Weakened limb, several of the seven security-only fields tiering Optional or Not required: "
        f"{'holds' if weakened['holds'] else 'does not hold'}. "
        f"{len(weakened['security_only_optional_or_not_required'])} of 7 do.")
    add(f"- Security-only fields that could be tested at all: "
        f"{len(verdict['security_only_tested'])} of 7, "
        + ", ".join(f"`{n}`" for n in verdict["security_only_tested"]) + ".")
    add("")
    add("| Required field | Mapping |")
    add("|---|---|")
    for mapping in MAPPING_ORDER:
        for n in verdict["required_by_mapping"][mapping]:
            add(f"| `{n}` | {mapping} |")
    add("")
    add("| Security-only field not tested | Why |")
    add("|---|---|")
    for n, why in verdict["security_only_untested"].items():
        add(f"| `{n}` | {why} |")
    add("")

    add("## Notes recorded before the sweep")
    add("")
    add("These do not change a cell. They record what was expected, and why, before the sweep ran.")
    add("")
    add("- `retrieval.source_provenance` against A6. Ruling 6 at M2 gave the poisoned procedure `unknown` "
        "provenance, the same as a document already in the benign estate, so provenance was not expected "
        "to separate A6. `d-a06` keys on the indexed inventory and does not read provenance.")
    add("- `action.egress_target`. At M3, a canary sent by email to a permitted internal recipient in "
        "benign session `m3-b100` would fire a rule keyed on the payload alone. This field is what "
        "separates that session from the A1 attack. The sweep cannot express that comparison: A1 has no "
        "successful trial, and nulling the field silences `d-a01` rather than turning it into the "
        "payload-alone rule.")
    a8 = doc["circular"]["A8"]
    counts_a8 = a8["tool_pre_events_per_successful_trial"]
    if not counts_a8:
        spread = "none, as no A8 trial succeeded"
    elif min(counts_a8) == max(counts_a8):
        spread = f"{counts_a8[0]} in each of the {len(counts_a8)}"
    else:
        spread = f"{min(counts_a8)} to {max(counts_a8)}"
    add(f"- `turn.tokens_in` against A8. `{a8['detector']}` uses the A8 oracle's thresholds and fires first "
        f"on {a8['tool_call_threshold']} or more tool calls, a count of events that reads no field. Tool "
        f"calls per successful A8 trial: {spread}.")
    add("")
    return "\n".join(lines)


# ---------------------------------------------------- writing the register --


def apply_tiers(register_text: str, doc: dict[str, Any]) -> str:
    """The register with each `tier: null` replaced by the recorded tier.

    A line edit, not a YAML dump, so every comment in the register survives.
    Running it twice gives the same text.
    """
    tiers = doc["tiers"]
    top = ("tiered_at:", "tiered_date:", "tier_sweep:")
    kept: list[str] = []
    lines = register_text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(top):
            i += 1
            while i < len(lines) and lines[i].startswith("  ") and not lines[i].startswith("  -"):
                i += 1
            continue
        if line.startswith(("    tier_basis:", "    tier_cells:")):
            i += 1
            while i < len(lines) and lines[i].startswith("      - "):
                i += 1
            continue
        kept.append(line)
        i += 1

    out: list[str] = []
    current = None
    seen = set()
    for line in kept:
        if line.startswith("  - name: "):
            current = line.split("name:", 1)[1].strip()
        if line.startswith("    tier: ") and current is not None:
            t = tiers[current]
            out.append(f"    tier: {t['tier']}\n")
            out.append(f"    tier_basis: {json.dumps(t['basis'])}\n")
            if t["cells"]:
                out.append("    tier_cells:\n")
                out.extend(f"      - {json.dumps(c)}\n" for c in t["cells"])
            else:
                out.append("    tier_cells: []\n")
            seen.add(current)
            continue
        out.append(line)
        if line.startswith("field_count:"):
            out.append("tiered_at: M5\n")
            out.append(f"tiered_date: {doc['date']}\n")
            out.append("tier_sweep:\n")
            out.append("  artefact: results/necessity.json\n")
            out.append(f"  commit: {json.dumps(doc['commit'])}\n")
    if seen != set(tiers):
        raise AblationError(f"tiers not written for {sorted(set(tiers) - seen)}")
    text = "".join(out)
    written = {f["name"]: f["tier"] for f in yaml.safe_load(text)["fields"]}
    if written != {k: v["tier"] for k, v in tiers.items()}:
        raise AblationError("the register does not read back the tiers that were written")
    return text


# -------------------------------------------------------------------- CLI --


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The M5 ablation sweep and necessity matrix.")
    parser.add_argument("--write", action="store_true", help="write results/, from a clean tree only")
    parser.add_argument("--apply-tiers", action="store_true",
                        help="write the tiers in results/necessity.json into schema/fields.yaml")
    args = parser.parse_args(argv)

    if args.apply_tiers:
        doc = json.loads(NECESSITY_JSON.read_text(encoding="utf-8"))
        text = apply_tiers(REGISTER_PATH.read_text(encoding="utf-8"), doc)
        REGISTER_PATH.write_text(text, encoding="utf-8")
        print(f"  tiers from {NECESSITY_JSON.relative_to(REPO_ROOT)} (sweep at {doc['commit'][:7]}) "
              f"written to {REGISTER_PATH.relative_to(REPO_ROOT)}")
        return 0

    commit = _git("rev-parse", "HEAD")
    clean = _git("status", "--porcelain") == ""
    if args.write and not clean:
        print("  refusing to write: the working tree is not clean, so the commit would not describe the sweep")
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
        NECESSITY_JSON.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        NECESSITY_MD.write_text(text + "\n", encoding="utf-8")
        print(f"\n  written: {NECESSITY_JSON.relative_to(REPO_ROOT)}, {NECESSITY_MD.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
