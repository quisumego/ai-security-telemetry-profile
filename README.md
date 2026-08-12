# AI Security Telemetry Profile (ASTP)

A security logging profile for LLM applications and agents, published together
with the measurement that produced it.

For every field in the schema the profile states a tier of required,
recommended or optional, and **each tier is justified by a measured result
rather than an opinion**.

> **Status: M0 complete. Work in progress.**
> The schema and the pre-committed rules are written. Nothing has been measured
> yet, so no field carries a tier. This repository is private until M8.

---

## The question

Everyone agrees you should log your LLM applications. Nobody says which fields.

The OpenTelemetry GenAI semantic conventions are the closest thing to a standard
that exists, and they are built for observability, cost attribution and quality
evaluation rather than for detection. The published field lists in the wider
guidance literature are generic: timestamp, user, model, token counts, latency,
a redacted prompt. No one has published which fields carry detection signal for
which attack classes, backed by measurement.

So: build an agent, attack it, then delete each field and see what goes dark.

## How it works

| Stage | What happens |
|---|---|
| Instrument | A small agent over a synthetic corpus emits every field in the register as JSON Lines |
| Attack | Ten attack classes, ten trials each, each with a machine-checkable success oracle written beforehand |
| Baseline | One detector per class, scored against the attack corpus and a benign corpus |
| Ablate | Each field is nulled **in the captured logs** and every detector re-runs. No model calls |
| Tier | Tiers are assigned by applying a pre-committed rule mechanically to the resulting matrix |

The ablation makes no model calls. Fields are nulled in logs that were already
captured and the detectors re-run, which is what keeps the sweep deterministic
and the cost near zero.

## Design principles

- **The agent behaves, the code decides.** Every detection outcome is computed
  by tested code from captured logs, against oracles written before the runs.
  There is no manual adjudication step anywhere in the scoring path.
- **The instrument is not the point.** The agent exists to generate telemetry.
  It is kept small and boring on purpose.
- **Development and evaluation stay separated.** Detectors are authored against
  eight attack scenarios. Two are held out and not opened until scoring.
- **Pre-commitment over post-hoc reasoning.** The tiering rule, the materiality
  threshold and the holdout choice are committed before the first scored run.
  See [`docs/methodology.md`](docs/methodology.md).

## The hypothesis

The profile layers on the OpenTelemetry GenAI conventions, adopting `gen_ai.*`
naming wherever an equivalent attribute exists so the output is adoptable rather
than parallel, and adding the security fields the conventions do not cover.

Of 37 fields, 13 map fully to the conventions, 6 map partially and 18 have no
equivalent. **Seven of those 18 are flagged `security_only`** and are the
hypothesis under test:

| Field | What it records |
|---|---|
| `retrieval.source_provenance` | Whether retrieved content came from a trusted source |
| `retrieval.permission_context` | The access scope of the caller and of what was returned |
| `action.permission_decision` | The authorisation outcome, for permitted calls as well as refused ones |
| `action.egress_target` | Where an outbound call was addressed |
| `action.context_document_ids` | Which retrieved documents were in context when a tool was called |
| `control.canary_triggered` | Whether a planted marker string left the system |
| `control.block_reason` | Why a guardrail fired |

The expected result is that these carry the highest detection value. That
expectation is recorded in the register as a prediction and may be wrong. If the
measurement refutes it, the refutation is published, because a negative result
here is still the only measurement of its kind.

`action.context_document_ids` is the field to watch. It is what turns "the agent
sent an email" into "the agent sent an email while an externally sourced
document was in context". Every existing convention logs retrieval and tool
calls separately and defines nothing that links them.

## Layout

```
schema/     fields.yaml, event.schema.json, otel-mapping.md
lab/        the instrumented agent and its synthetic corpus
attacks/    scenarios, oracles, runner
benign/     the false positive denominator
detect/     Sigma rules and their Python implementations
ablation/   the sweep and the necessity matrix
cost/       volume and cost model, computed from real logs
runs/       captured JSON Lines and run manifests, committed
results/    generated metrics and tables
docs/       methodology, build log, verified references
```

## Running the tests

```bash
pip install -e ".[dev]"
pytest
```

The suite checks that the field register and the event schema agree in both
directions, that no tier has been assigned before the ablation runs, and that
the house style holds.

## Standards and references

Every external identifier in this repository was verified against a live source
with a retrieval date recorded. See
[`docs/attack-class-references.md`](docs/attack-class-references.md) for the
OWASP and MITRE ATLAS mappings,
[`docs/framework-references.md`](docs/framework-references.md) for DSIT, NCSC and
ETSI, and [`schema/otel-mapping.md`](schema/otel-mapping.md) for the pinned
OpenTelemetry snapshot.

No text is reproduced from any standard. Identifiers are cited and intent is
paraphrased in original wording.

## Licence

MIT. See [LICENSE](LICENSE).
