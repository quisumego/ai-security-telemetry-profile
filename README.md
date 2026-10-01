# AI Security Telemetry Profile (ASTP)

A security logging profile for LLM applications and agents, published with the
measurement that produced it: build an agent, attack it, then remove each field
from the captured logs and see which detections go dark.

## The result

**The headline claim came back undertested.** The claim was that the fields
with the most detection value are the ones the OpenTelemetry GenAI conventions
do not cover, the seven this profile flags `security_only`. Read literally, the
falsification rule committed before any capture says **weakened**, because five
of the seven tier Not required. Both words are published, and the claim is not
refuted. Undertested is the reading ruled at M5, before the ablation sweep ran
but after the M4 baseline was known: only two of the seven could be tested at
all, and both tier Required. The other five were never
read by a detector with a successful attack to detect.

- Of the 37 fields, 3 tier Required: `retrieval.document_ids`,
  `retrieval.permission_context` and `control.canary_triggered`. 0 tier
  Recommended, 10 Optional and 24 Not required, and a Not required tier is not
  evidence that a field carries no signal.
- The A1 oracle fired on 1 of 100 benign sessions and on none of the 10 A1
  attack trials. What separates the attack from that benign email is where it
  went, which `action.egress_target` records, and the tiering rule has no way to
  credit a field for the false positives it prevents. Its tier stays Not
  required, with that evidence beside it.
- Vendor defaults on Microsoft Foundry and Amazon Bedrock carry none of the
  seven security-only fields on any of the 6 surfaces assessed, from
  documentation alone. That supports the case for a profile and does not test
  the headline.
- On a second, local model the attacks that succeeded changed, 18/91 against
  32/100, and one tier would move. That is one comparison, never applied.

[`SPEC.md`](SPEC.md) is the profile: the event model, every field with the
evidence behind its tier, retention and volume guidance, a Microsoft Sentinel
mapping, the framework mapping and the limitations.

## The question

Everyone agrees you should log your LLM applications. Nobody says which fields.
The OpenTelemetry GenAI semantic conventions are the closest thing to a standard,
and they are built for observability, cost attribution and quality evaluation
rather than for detection. This project measured which fields carry detection
signal for which attack classes, on one agent, one model and a synthetic corpus.

## How it was measured

| Stage | What happened |
|---|---|
| Rules first | The tiering rule, the materiality threshold and the falsification rule were committed before any capture, as the second commit, `c8b28dd` |
| Instrument | A small agent on the Claude Agent SDK, pinned to `claude-haiku-4-5`, emits every field of the register as JSON Lines over a synthetic document estate for a fictional insurer |
| Attack | Ten attack classes, ten trials each, every one scored by a machine-checkable oracle written before the runs |
| Denominator | 100 benign sessions, so every detection rate has a false positive rate beside it |
| Detect | Seven detectors, written against throwaway fixtures and never against a capture, scored with two classes held out |
| Ablate | Each field nulled in the captured logs and every detector re-run, 37 singly and 103 pairs, with no model call |
| Tier | The pre-committed rule applied mechanically to the resulting matrix |

There is no manual adjudication anywhere in the scoring path: every outcome is
computed by tested code from the captured logs.

## Reproduce it

Every result is a committed file under `results/`, built from the captures
committed under `runs/`. No command below calls a model.

```bash
python -m venv .venv
.venv/bin/pip install -e ".[lab,dev]"
.venv/bin/python -m pytest
```

The `lab` extra installs the Claude Agent SDK, which six test files and the two
cross-check reports load; the captures were taken with version 0.2.139. Run
everything from the repository root. Then any of these:

| Command | What it prints | What it is held to |
|---|---|---|
| `.venv/bin/python -m attacks.report` | attack success per class on the main model | the same counts in `results/baseline.json` and `results/m7b-crosscheck.json` |
| `.venv/bin/python -m benign.report` | the denominator: cost, canary sinks, oracle false positives | `results/benign.json` |
| `.venv/bin/python -m detect.evaluate` | the detector baseline, holdouts closed | `results/baseline.json` |
| `.venv/bin/python -m detect.evaluate --include-holdouts` | the baseline with the two holdouts opened | `results/baseline.json` |
| `.venv/bin/python -m ablation.matrix` | the necessity matrix, the tiers and the verdict | `results/necessity.json`, `results/necessity-matrix.md`, the tiers in `schema/fields.yaml` |
| `.venv/bin/python -m cost.model` | model spend, telemetry volume, retention postures and projections | `results/volume.json`, `results/volume.md` |
| `.venv/bin/python -m siem.sentinel` | the Sentinel table, rule and queries | `siem/sentinel/`, `docs/sentinel-mapping.md` |
| `.venv/bin/python -m vendor_gap.analysis` | the vendor gap class answers | `results/vendor-gap.json`, `docs/vendor-gap-analysis.md` |
| `.venv/bin/python -m crosscheck.report` | attack success on the local model beside the main one | `results/m7b-crosscheck.json`, `results/m7b-crosscheck.md` |
| `.venv/bin/python -m crosscheck.matrix` | the necessity matrix over the local pass, beside M5 | `results/m7b-necessity.json`, `results/m7b-necessity-matrix.md` |
| `.venv/bin/python -m spec.render` | whether `SPEC.md`'s generated blocks match a fresh render | `SPEC.md` |

The suite rebuilds each of these files from the captures and fails if the
committed copy differs. Both `detect.evaluate` forms print a holdout note
written before the holdouts were opened, kept because the detector file it comes
from is frozen; read the holdout result in `SPEC.md` Section 9, with the
exposure it carries. The captures ran on a subscription allowance: no money was
spent, and extra usage was off throughout.

## What it does not claim

- It does not show that the security-only fields are the most valuable. That
  claim came back undertested.
- The tiers are evidence about this schema, these detectors and one model on a
  synthetic corpus, not a ranking of logging fields in general.
- It does not certify compliance with the DSIT Code of Practice, the NCSC
  guidelines or ETSI TS 104 223.
- The Sentinel queries have never been run, and the vendor gap rests on
  documentation, with no vendor log record observed.
- The holdout result is weakened evidence, for the reasons `SPEC.md` Section 9
  gives.

## Where to read further

- [`SPEC.md`](SPEC.md): the profile and its limitations.
- [`docs/methodology.md`](docs/methodology.md): the rules, committed before any
  capture.
- [`docs/build-log.md`](docs/build-log.md): what happened at each stage, including
  what went wrong.
- [`results/`](results/): every measured result, and
  [`spec/figures.yaml`](spec/figures.yaml), the source of every figure the
  published documents quote.
- [`docs/vendor-gap-analysis.md`](docs/vendor-gap-analysis.md) and
  [`docs/sentinel-mapping.md`](docs/sentinel-mapping.md).

## The history of this repository

This repository was created on 30 September 2026, after every capture. Before
it was published, its history was rewritten once to take the owner's personal
data out, with every commit's recorded dates copied unchanged.
[`docs/history-rewrite.md`](docs/history-rewrite.md) records what changed, how
it was checked, and the old and new hash of every commit. Git dates are set by
whoever commits, so the history shows the order work was recorded in: the
pre-committed rules are the second commit, before the schema, any detector and
any capture.

## Layout

```
schema/      the field register, the event schema, the OpenTelemetry mapping
lab/         the instrumented agent and its synthetic corpus
attacks/     scenarios, oracles, overlays and the capture runner
benign/      the false positive denominator
detect/      the seven detectors and their Sigma rules
ablation/    the sweep, the necessity matrix and the tiers
cost/        the volume and cost model
siem/        the Microsoft Sentinel table, rule and queries
vendor_gap/  the vendor gap evidence and passes
crosscheck/  the local model cross-check
spec/        the M8 rulings, the SPEC.md renderer and the figure ledger
runs/        every capture, committed
results/     every measured result, generated
docs/        methodology, build log, references and analyses
```

## Standards and references

Every external identifier in this repository was verified against a live source
with a retrieval date recorded, and re-checked on 1 October 2026. See
[`docs/attack-class-references.md`](docs/attack-class-references.md) for the
OWASP and MITRE ATLAS mappings,
[`docs/framework-references.md`](docs/framework-references.md) for DSIT, NCSC and
ETSI, and [`schema/otel-mapping.md`](schema/otel-mapping.md) for the pinned
OpenTelemetry snapshot. No text is reproduced from any standard: identifiers are
cited and intent is paraphrased in original wording.

## Licence

MIT. See [LICENSE](LICENSE).
