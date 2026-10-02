"""The generated blocks of SPEC.md, rendered from the register and the results.

Ruled at M8 (spec/rulings.py, ruling 4): the verdict, the field register with
its tier evidence, the field definitions, the M7b comparison and the quoted
tiering rule are written by code from schema/fields.yaml, results/necessity.json,
results/m7b-necessity.json and docs/methodology.md, so no figure in them is
typed by hand. A test requires a fresh render to reproduce SPEC.md exactly. The
prose around the blocks is written by hand and held by the figure ledger.

    .venv/bin/python -m spec.render            # exit 1 if SPEC.md differs from a fresh render
    .venv/bin/python -m spec.render --write    # rewrite SPEC.md's generated blocks
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

from lab.config import REPO_ROOT
from spec import rulings

SPEC = REPO_ROOT / rulings.SPEC
REGISTER = REPO_ROOT / "schema" / "fields.yaml"
NECESSITY = REPO_ROOT / "results" / "necessity.json"
M7B = REPO_ROOT / "results" / "m7b-necessity.json"
METHODOLOGY = REPO_ROOT / "docs" / "methodology.md"

CLASSES = tuple(f"A{i}" for i in range(1, 11))
TIERS = ("required", "recommended", "optional", "not_required")
TIER_WORDS = {"required": "Required", "recommended": "Recommended", "optional": "Optional",
              "not_required": "Not required"}
MEASURED = {"X", "x", ".", "Xc", "xc", ".c"}
BLOCKS = ("verdict", "register", "definitions", "m7b", "rule")
A9_EXPOSURE = (
    "That A9 result carries its exposure: the working session that built the detectors "
    f"{rulings.A9_EXPOSURE_PHRASES[0]}, the project's private working notes at M4 "
    f"{rulings.A9_EXPOSURE_PHRASES[1]} to any session that read them, the detectors were "
    f"{rulings.A9_EXPOSURE_PHRASES[2]}, and the result is "
    f"{rulings.A9_EXPOSURE_PHRASES[3]}."
)


def load() -> tuple[dict, dict, dict]:
    register = yaml.safe_load(REGISTER.read_text(encoding="utf-8"))
    necessity = json.loads(NECESSITY.read_text(encoding="utf-8"))
    m7b = json.loads(M7B.read_text(encoding="utf-8"))
    return register, necessity, m7b


def _code(name: str) -> str:
    return f"`{name}`"


def _join(names: list[str]) -> str:
    names = [_code(n) for n in names]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _type(field: dict) -> str:
    return f"array of {field['items']}" if field["type"] == "array" else field["type"]


def verdict_block(register: dict, necessity: dict) -> str:
    v = necessity["verdict"]
    fields = register["fields"]
    counts = {t: sum(1 for f in fields if f["tier"] == t) for t in TIERS}
    security = [f["name"] for f in fields if f["security_only"]]
    required = [f["name"] for f in fields if f["tier"] == "required"]
    tested = v["security_only_tested"]
    untested = v["security_only_untested"]
    if not set(tested) <= set(required) or v["refuted_limb"]["holds"]:
        raise ValueError("the fixed wording of the verdict block no longer matches the results")
    by_mapping = {f["name"]: f["otel"] for f in fields}
    lines = [
        f"**Headline: {v['headline']}.** Read literally, methodology Section 9 says "
        f"**{v['section_9_as_written']}**. The claim is not refuted.",
        "",
        f"- Tiers over the {len(fields)} fields: "
        + ", ".join(f"{counts[t]} {TIER_WORDS[t]}" for t in TIERS) + ".",
        f"- Security-only fields that could be tested at all: {len(tested)} of {len(security)}, "
        f"{_join(sorted(tested))}. Each tiers Required.",
        f"- The other {len(untested)} tier Not required without ever being tested: "
        + "; ".join(f"{_code(k)}, {r}" for k, r in sorted(untested.items())) + ".",
        "- Refuted limb, that the Required fields are predominantly ones the conventions "
        "already cover: does not hold. None of the "
        f"{len(required)} Required fields has a full OpenTelemetry mapping: "
        + "; ".join(f"{_code(n)} {by_mapping[n]}" for n in required) + ".",
        "- Weakened limb, that several of the seven security-only fields tier Optional or "
        f"Not required: holds, {len(v['weakened_limb']['security_only_optional_or_not_required'])} "
        f"of {len(security)}.",
    ]
    return "\n".join(lines)


def register_block(register: dict, necessity: dict) -> str:
    out = [
        "| Field | OTel | Security only | Tier | Why | Deciding cells | Cells, A1 to A10 |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in register["fields"]:
        cells = necessity["single"][f["name"]]["cells"]
        codes = " ".join(cells[c]["cell"] for c in CLASSES)
        deciding = "; ".join(f["tier_cells"]) if f["tier_cells"] else "none"
        out.append(
            f"| {_code(f['name'])} | {f['otel']} | {'yes' if f['security_only'] else ''} | "
            f"**{TIER_WORDS[f['tier']]}** | {f['tier_basis']} | {deciding} | `{codes}` |"
        )
    holdouts = sorted((c for c, v in necessity["classes"].items() if v["holdout"]), key=CLASSES.index)
    single = sorted((c for c, v in necessity["classes"].items() if v["successful"] == 1), key=CLASSES.index)
    on_a9 = [f["name"] for f in register["fields"] if any(c.startswith("A9 ") for c in f["tier_cells"])]
    out += [
        "",
        "Codes, as in `results/necessity-matrix.md`: `X` the class became undetectable with the "
        "field nulled, `.` tested with no measurable effect, `nr` not read by the class's counted "
        "detector, `nt` no successful trial, `ab` absent, and the suffix `c` the circular A8 "
        f"column. {_join(holdouts).replace('`', '')} were the holdouts, and the "
        f"{_join(single).replace('`', '')} cells each rest on one successful trial. The tiers of "
        f"{_join(on_a9)} rest on A9 cells, which record how the detector counted for A9, "
        "`d-a03`, did when a field was nulled. " + A9_EXPOSURE,
    ]
    return "\n".join(out)


def definitions_block(register: dict) -> str:
    out = [
        "| Field | Group | Type | OTel mapping | Attribute at the pinned commit | Rationale |",
        "|---|---|---|---|---|---|",
    ]
    for f in register["fields"]:
        rationale = re.sub(r"\s+", " ", f["rationale"]).strip()
        attribute = _code(f["otel_attribute"]) if f.get("otel_attribute") else "none"
        out.append(
            f"| {_code(f['name'])} | {f['group']} | {_type(f)} | {f['otel']} | {attribute} | "
            f"{rationale} |"
        )
    return "\n".join(out)


def m7b_block(register: dict, necessity: dict, m7b: dict) -> str:
    fields = len(register["fields"])
    measured = [d for d in m7b["differences"] if d["m5"] in MEASURED or d["local"] in MEASURED]
    order = {f["name"]: i for i, f in enumerate(register["fields"])}
    measured.sort(key=lambda d: (order[d["field"]], CLASSES.index(d["class"])))
    out = [
        "| Field | Tier at M5, applied | Tier the rule would give over the local pass, not applied |",
        "|---|---|---|",
    ]
    for t in m7b["tier_differences"]:
        out.append(f"| {_code(t['field'])} | {TIER_WORDS[t['m5']]} | {TIER_WORDS[t['local']]} |")
    out += [
        "",
        f"Cells that differ from M5: {len(m7b['differences'])} of {fields * len(CLASSES)}, "
        f"of which {len(measured)} are in measured states:",
        "",
    ]
    for d in measured:
        out.append(f"- {_code(d['field'])}, {d['class']}: `{d['m5']}` at M5, `{d['local']}` on the local pass.")
    out += [
        "",
        f"The rest are `nr` and `nt` changing places as classes gained or lost successful trials. "
        + (f"The headline the rule would give is {m7b['headline_if_applied']}, as at M5. "
           if m7b["headline_if_applied"] == m7b["m5_headline"] else
           f"The headline the rule would give is {m7b['headline_if_applied']}, against "
           f"{m7b['m5_headline']} at M5. ")
        + f"Local model `{m7b['model']}`; false positive denominator: {m7b['benign_denominator']}.",
    ]
    return "\n".join(out)


def rule_block() -> str:
    text = METHODOLOGY.read_text(encoding="utf-8")
    start = text.index("## 3. The tiering rule")
    end = text.index("## 5. The holdout commitment")
    out = []
    for line in text[start:end].rstrip().splitlines():
        if line.strip() == "---":
            continue
        heading = re.match(r"^#{2,3} (.*)$", line)
        if heading:
            line = f"**{heading.group(1)}**"
        out.append(">" if not line else f"> {line}")
    while out and out[-1] == ">":
        out.pop()
    return "\n".join(re.sub(r"(>\n)+(?=>)", ">\n", "\n".join(out)).splitlines())


def blocks() -> dict[str, str]:
    register, necessity, m7b = load()
    return {
        "verdict": verdict_block(register, necessity),
        "register": register_block(register, necessity),
        "definitions": definitions_block(register),
        "m7b": m7b_block(register, necessity, m7b),
        "rule": rule_block(),
    }


def render_doc(text: str, rendered: dict[str, str] | None = None) -> str:
    rendered = rendered if rendered is not None else blocks()
    for name in BLOCKS:
        pattern = re.compile(
            rf"(<!-- generated:{name} -->\n).*?(<!-- /generated:{name} -->)", re.S)
        if len(pattern.findall(text)) != 1:
            raise ValueError(f"SPEC.md must carry exactly one generated:{name} block")
        text = pattern.sub(lambda m: m.group(1) + rendered[name] + "\n" + m.group(2), text)
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the generated blocks of SPEC.md.")
    parser.add_argument("--write", action="store_true", help="rewrite SPEC.md's generated blocks")
    args = parser.parse_args(argv)
    current = SPEC.read_text(encoding="utf-8")
    fresh = render_doc(current)
    if args.write:
        SPEC.write_text(fresh, encoding="utf-8")
        print(f"wrote {len(BLOCKS)} generated blocks to {SPEC.relative_to(REPO_ROOT)}")
        return 0
    if fresh != current:
        print(f"{SPEC.relative_to(REPO_ROOT)} differs from a fresh render")
        return 1
    print(f"{SPEC.relative_to(REPO_ROOT)} matches a fresh render")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
