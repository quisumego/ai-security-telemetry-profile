# AI Security Telemetry Profile (ASTP)

A security logging profile for LLM applications and agents, tiered by
measurement: attack an agent, remove each field from its logs, and see which
detections go dark.

![Terminal recording: attacks.report prints attack success per class from the saved captures, then ablation.matrix prints the headline verdict and the Required fields](docs/demo.gif)

## The result

I tested one claim: that the log fields that matter most for catching attacks
on an AI agent are the seven security fields this profile adds, which the
OpenTelemetry GenAI conventions do not cover. The answer is **undertested**:
only two of the seven could be tested at all, and both came out Required. Read
literally, the rule I set before any data says **weakened**, because
five of the seven tier Not required. The claim is not refuted. I settled on
undertested once the detector baseline was known, so both words are published.

## What I did

- **A lab agent** on the Claude Agent SDK, pinned to `claude-haiku-4-5`, with
  six tools over made-up insurance documents, logging every field as JSON
  Lines.
- **Attacks and normal sessions:** ten attack types, from prompt injection to
  data exfiltration, ten trials each, and 100 benign sessions for false
  positives.
- **Seven detectors** with Sigma rules, then **field removal**: each field
  nulled in the saved logs and every detector re-run, with no model call.
- **A vendor check** of Microsoft Foundry and Amazon Bedrock logging, and **a
  re-run on a local model**.
- **Mappings** to Microsoft Sentinel, OWASP, MITRE ATLAS and the DSIT, NCSC and
  ETSI guidance.

The rules for judging the results were locked before the first attack, two
attack types were held back until the detectors were frozen, and tested code
scored every outcome. [SPEC.md Section 4](SPEC.md#4-the-tiering-rule) shows how
to check that the rules came first.

**Who did what.** I did this work with Claude Code, Anthropic's AI coding
assistant: it wrote the code, ran the captures and drafted the documents. Each
stage's design came to me as questions, which I ruled on before work acted on
them, as the [build log](docs/build-log.md) records. I wrote the four injection
documents the attacks plant.

## What it achieved

- **The profile, [`SPEC.md`](SPEC.md):** 37 fields, each tiered with its
  evidence: 3 tier Required, 0 tier Recommended, 10 Optional and 24 Not
  required.
- **Required:** `retrieval.document_ids`, `retrieval.permission_context` and
  `control.canary_triggered`. Removing any one made at least one attack type
  undetectable.
- **A planted marker leaving by email is not a signal on its own.** The direct
  prompt injection check fired on 1 of 100 benign sessions and on none of the
  10 attack trials. The destination, `action.egress_target`, told them apart,
  which the tiering rule could not credit.
- **Vendor logs leave the gap:** by their documentation, Microsoft Foundry and
  Amazon Bedrock log none of the seven security fields on any of the 6 surfaces
  assessed.
- **The model matters:** on a small local model the attacks that succeeded
  changed, 18/91 against 32/100. One comparison, not used in the tiers.

**Limits.** One agent, one model, synthetic data, ten trials per attack type,
and one author behind the schema, the attacks and the detectors, so the tiers
describe this setup. The Sentinel queries have never run, and the vendor
findings rest on documentation. [SPEC.md Section 9](SPEC.md#9-limitations)
lists the rest.

## What I learnt

- **A canary is not a signal on its own; the canary with its destination is.**
  Ordinary traffic showed it, not an attack.
- **The model refused what it recognised as an attack** and complied with what
  looked like good work, such as following a retrieved procedure.
- **A measurement only reaches what it can test.** A Not required tier can mean
  never tested, and undertested is a result worth publishing.
- **Fix the rules before the data**, and label anything decided after.
- **An AI coding assistant needs checks of its own.** Tests tied every figure
  to its source, yet reading the claims still caught drafts that said too
  much.

## Tools I used

- **Building and testing:** Python, pytest, PyYAML and jsonschema.
- **Models and runtimes:** the Claude Agent SDK with `claude-haiku-4-5`; Ollama
  with `granite4.1:3b`; Claude Code.
- **Logging and threat frameworks:** OpenTelemetry GenAI conventions, JSON
  Schema, JSON Lines; OWASP Top 10 for LLM Applications, MITRE ATLAS; DSIT,
  NCSC and ETSI TS 104 223.
- **SIEM and detection formats:** Sigma rules, stating intent while the Python
  detectors scored; a Microsoft Sentinel table, Data Collection Rule and KQL
  queries, written but never deployed or run; Azure and AWS logging, assessed
  from documentation without signing in to either cloud.
- **The demo:** vhs, ttyd and ffmpeg.

## Skills I learnt

- **Threat modelling an AI agent:** ruling on ten attack designs mapped to
  OWASP and MITRE ATLAS ([`attacks/`](attacks/)).
- **Writing indirect prompt injection:** the four injection documents, written
  myself ([`attacks/overlays/`](attacks/overlays/)).
- **Designing an experiment that can fail:** deciding the rules and holdouts
  before any data ([`docs/methodology.md`](docs/methodology.md)).
- **Security logging design:** reviewing a field register built on
  OpenTelemetry ([`schema/`](schema/)).
- **Detection engineering:** deciding that every detector reports false
  positives as well as detections ([`detect/`](detect/)).
- **Measurement by ablation:** ruling how each field is valued by what breaks
  without it ([`results/necessity-matrix.md`](results/necessity-matrix.md)).
- **SIEM and cloud logging:** ruling on a Sentinel mapping and a vendor log
  review ([`docs/sentinel-mapping.md`](docs/sentinel-mapping.md),
  [`docs/vendor-gap-analysis.md`](docs/vendor-gap-analysis.md)).
- **Directing an AI coding assistant** under written rulings, with every figure
  checked by a test ([`spec/`](spec/)).

## Run it yourself

No command here calls a model: each reads the captures saved under `runs/`.

```bash
# Python 3.10 or later
git clone https://github.com/quisumego/ai-security-telemetry-profile.git
cd ai-security-telemetry-profile
python -m venv .venv
.venv/bin/pip install -e ".[lab,dev]"
.venv/bin/python -m attacks.report    # attack success per attack type
.venv/bin/python -m benign.report     # the benign sessions and each check's false alarms
.venv/bin/python -m ablation.matrix   # the field-removal results, the tiers and the verdict
```

## Read more

- [`SPEC.md`](SPEC.md): the profile, every field's evidence, and the full
  limitations.
- [`docs/methodology.md`](docs/methodology.md): the rules, written before the
  first attack ran.
- [`docs/write-up.md`](docs/write-up.md): the write-up, for a general security
  audience.
- [`docs/build-log.md`](docs/build-log.md): what happened at each step,
  including what went wrong.
- [`results/`](results/) and [`spec/figures.yaml`](spec/figures.yaml): every
  result, and the source of every figure quoted here.

Files under `attacks/` and `lab/` are kept exactly as the captures read them,
so notes inside them predate the detectors.

## Licence

MIT. See [LICENSE](LICENSE).
