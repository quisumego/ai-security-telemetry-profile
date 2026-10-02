# AI Security Telemetry Profile (ASTP)

A security logging profile for LLM applications and agents, published with the
measurement that produced it: build an agent, attack it, then remove each field
from the captured logs and see which detections go dark.

![Terminal recording: attacks.report prints attack success per class from the committed captures, then ablation.matrix prints the headline verdict and the Required fields](docs/demo.gif)

## The result

The claim under test: the fields with the most detection value are the ones the
OpenTelemetry GenAI conventions do not cover, in particular seven security
fields this profile adds. The verdict is **undertested**, a reading settled
after the detector baseline was known and before the ablation ran: only two of
the seven could be tested at all, and both tier Required. Read literally, the
rule committed before any capture says **weakened**, because five of the seven
tier Not required, and the claim is not refuted. [`SPEC.md`](SPEC.md) has the
detail.

## What was built

- A small agent on the Claude Agent SDK, pinned to `claude-haiku-4-5`, with six
  tools over a synthetic document estate for a fictional insurer, logging every
  field of the profile as JSON Lines.
- Ten attack classes, ten trials each, every trial scored by an oracle written
  before the runs, and 100 benign sessions so that every detector has a false
  positive rate beside its detection rate.
- Seven detectors with Sigma rules, and an ablation harness that sets each
  field to null in the captured logs and re-runs every detector, with no model
  call.
- A Microsoft Sentinel mapping, a telemetry volume model, a gap analysis of
  what Microsoft Foundry and Amazon Bedrock log by default, and a cross-check of
  the attacks on a second, local model.
- The profile itself, [`SPEC.md`](SPEC.md).

## What was found

- Of the 37 fields, 3 tier Required: `retrieval.document_ids`,
  `retrieval.permission_context` and `control.canary_triggered`. Removing any
  one of them made at least one attack class undetectable. 0 tier Recommended,
  10 Optional and 24 Not required, and most Not required fields were never read
  by a detector with a successful attack to detect, so that tier is not
  evidence that a field carries no signal.
- A planted value leaving by email was not a usable signal on its own. The
  oracle for direct prompt injection fired on 1 of 100 benign sessions and on
  none of the 10 attack trials. What separated the attack from the benign email
  was the destination, which `action.egress_target` records, and the tiering
  rule cannot credit a field for the false positives it prevents, so that field
  tiers Not required with the evidence beside it.
- Default logging on Microsoft Foundry and Amazon Bedrock carries none of the
  seven security-only fields on any of the 6 surfaces assessed, from their
  documentation: a deployment has to log them itself. That supports the case
  for a profile and does not test the claim.
- On a second, local model the attacks that succeeded changed, 18/91 against
  32/100, and one tier would move. That is one comparison, and the tiers do not
  use it.

## Skills demonstrated

- AI security testing: ten attack classes run against an LLM agent, mapped to
  OWASP and MITRE ATLAS, each with a success oracle in code
  ([`attacks/`](attacks/),
  [`docs/attack-class-references.md`](docs/attack-class-references.md)).
- Security logging design and agent instrumentation: a field register mapped to
  the OpenTelemetry GenAI conventions, emitted from the Claude Agent SDK's hooks
  and the session harness, and validated against a JSON Schema as it is
  written
  ([`schema/`](schema/), [`lab/`](lab/)).
- Detection engineering: seven detectors and their Sigma rules, written against
  synthetic fixtures and never against the captures, and scored for detections
  and false positives ([`detect/`](detect/)).
- Experimental design: the rules, the thresholds and what would weaken or
  refute the claim, committed before any data, with holdout classes and no
  manual judgement in the scoring ([`docs/methodology.md`](docs/methodology.md)).
- Measurement by ablation: what each field is worth to detection, measured by
  removing it and re-running every detector ([`ablation/`](ablation/),
  [`results/necessity-matrix.md`](results/necessity-matrix.md)).
- SIEM engineering: a Microsoft Sentinel custom table, data collection rule and
  KQL rules generated from the schema and checked against Microsoft's
  documented limits, not deployed
  ([`docs/sentinel-mapping.md`](docs/sentinel-mapping.md)).
- Cloud logging assessment: what Azure and AWS record by default for a model and
  for an agent, every claim cited to vendor documentation with its retrieval
  date ([`docs/vendor-gap-analysis.md`](docs/vendor-gap-analysis.md)).
- Governance mapping: the profile mapped to the DSIT Code of Practice, the NCSC
  guidelines and ETSI TS 104 223 by identifier, with no text reproduced
  ([`docs/framework-references.md`](docs/framework-references.md)).
- Telemetry volume and retention: what the profile costs to log, measured from
  the captures, and what hashing or truncating content saves
  ([`results/volume.md`](results/volume.md)).
- Reproducible engineering: a Python test suite that rebuilds every result from
  the captures, and a ledger that ties every published figure to a committed
  file ([`tests/`](tests/), [`spec/figures.yaml`](spec/figures.yaml)).

## How it was done

The rules came first. The tiering rule, the threshold for a material change
and what would weaken or refute the claim were committed before any capture, as
the second commit, `c8b28dd`. Two of the ten attack classes were held out: no
detector was written for them, and they were opened only after the detectors
were frozen. Every outcome is computed by tested code from the captured logs,
with no manual judgement anywhere in the scoring, and the test suite rebuilds
every result from the captures and fails if a committed result or a quoted
figure drifts from it.

The repository's history was rewritten once before publication to take
personal data out, with every commit's dates copied unchanged. Git dates are
set by whoever commits, so what a reader can check is the order: the rules come
before the schema, any detector and any capture.
[`docs/history-rewrite.md`](docs/history-rewrite.md) records how the rewrite
was checked.

The work was done with Claude Code, Anthropic's AI coding assistant, under the
rules in [`CLAUDE.md`](CLAUDE.md): it wrote the code, ran the captures and
drafted the documents. Each stage's design was put to the author as questions
and ruled before work acted on it, as the rulings files and
[`docs/build-log.md`](docs/build-log.md) record, and the author wrote the four
injection documents the attacks use.

## Limitations

One agent, one model and a synthetic corpus, with ten trials per attack class,
and one author who designed the schema, the attacks and the detectors: the
tiers are evidence about this schema and these detectors, not a ranking of
logging fields in general. The Sentinel queries have never been run, and the
vendor findings rest on documentation, with no vendor log observed.
[`SPEC.md` Section 9](SPEC.md#9-limitations) has the full list.

## Reproduce it

```bash
# Python 3.10 or later
git clone https://github.com/quisumego/ai-security-telemetry-profile.git
cd ai-security-telemetry-profile
python -m venv .venv
.venv/bin/pip install -e ".[lab,dev]"
.venv/bin/python -m pytest
```

No command here calls a model: each reads the captures committed under
`runs/`, and the suite fails if a result it rebuilds differs from the committed
file under `results/`. The `lab` extra installs the Claude Agent SDK, which the
agent and part of the suite load; the captures were taken with version 0.2.139.
From the repository root:

```bash
.venv/bin/python -m attacks.report                      # attack success per class
.venv/bin/python -m benign.report                       # the benign sessions and each oracle's false positives
.venv/bin/python -m detect.evaluate                     # the detector baseline, holdouts closed
.venv/bin/python -m detect.evaluate --include-holdouts  # the baseline with the two holdouts opened
.venv/bin/python -m ablation.matrix                     # the necessity matrix, the tiers and the verdict
.venv/bin/python -m cost.model                          # model spend, telemetry volume, retention postures
.venv/bin/python -m siem.sentinel                       # the Sentinel table, data collection rule and queries
.venv/bin/python -m vendor_gap.analysis                 # the vendor gap answers
.venv/bin/python -m crosscheck.report                   # attack success on the second model
.venv/bin/python -m crosscheck.matrix                   # the necessity matrix on the second model
.venv/bin/python -m spec.render                         # fails if SPEC.md's generated tables are stale
```

Both `detect.evaluate` forms print a holdout note written before the holdouts
were opened. The detector file it comes from is frozen, so the note stays: read
the holdout result in [`SPEC.md`](SPEC.md) Section 9, with the caveat it
carries.

## Where to read more

- [`SPEC.md`](SPEC.md): the profile, with every field's evidence, retention
  and volume guidance, the Sentinel and framework mappings, and the
  limitations.
- [`docs/methodology.md`](docs/methodology.md): the rules, committed before any
  capture.
- [`docs/write-up.md`](docs/write-up.md): the write-up, for a general security
  audience.
- [`docs/build-log.md`](docs/build-log.md): what happened at each stage,
  including what went wrong.
- [`results/`](results/) and [`spec/figures.yaml`](spec/figures.yaml): every
  measured result, and the source of every figure the published documents
  quote.
- [`docs/vendor-gap-analysis.md`](docs/vendor-gap-analysis.md),
  [`docs/sentinel-mapping.md`](docs/sentinel-mapping.md) and
  [`docs/history-rewrite.md`](docs/history-rewrite.md).
- The external identifiers, each checked against its live source with a
  retrieval date: [`docs/attack-class-references.md`](docs/attack-class-references.md),
  [`docs/framework-references.md`](docs/framework-references.md) and
  [`schema/otel-mapping.md`](schema/otel-mapping.md).

The files under `attacks/` and `lab/` that the captures read are frozen as they
were captured, so notes inside them describe the project before the detectors
existed.

## Licence

MIT. See [LICENSE](LICENSE).
