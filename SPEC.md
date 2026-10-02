# AI Security Telemetry Profile (ASTP)

> **Status: complete, written at M8 on 1 October 2026 and condensed on 2
> October 2026.** Every figure comes from a committed result file: the
> generated blocks are written by `spec.render`, and every other figure is
> listed in `spec/figures.yaml` with its source.
>
> **The result in brief.** The claim tested: the fields with the most detection
> value are the seven flagged `security_only`, which the OpenTelemetry GenAI
> conventions do not cover. The measurement says **undertested**. Read
> literally, methodology Section 9, committed before any capture, says
> **weakened**. The claim is not refuted. Undertested is the reading ruled at M5,
> before the ablation ran but after the M4 baseline showed which classes had a
> successful attack to detect.
>
> **Stages.** M0 rules and schema, M1 lab agent, M2 attack captures, M3 benign
> captures, M4 detectors, M5 ablation and tiers, M6 volume and Sentinel, M7
> vendor gap, M7b second model, M8 this document. Rulings from M5 on are in each
> stage's `rulings.py`, earlier ones in `docs/build-log.md`.

<!-- generated:verdict -->
**Headline: undertested.** Read literally, methodology Section 9 says **weakened**. The claim is not refuted.

- Tiers over the 37 fields: 3 Required, 0 Recommended, 10 Optional, 24 Not required.
- Security-only fields that could be tested at all: 2 of 7, `control.canary_triggered` and `retrieval.permission_context`. Each tiers Required.
- The other 5 tier Not required without ever being tested: `action.context_document_ids`, read by no detector; `action.egress_target`, read only by d-a01, d-a02, whose classes have no successful trial; `action.permission_decision`, read by no detector; `control.block_reason`, read by no detector; `retrieval.source_provenance`, read only by d-a02, whose classes have no successful trial.
- Refuted limb, that the Required fields are predominantly ones the conventions already cover: does not hold. None of the 3 Required fields has a full OpenTelemetry mapping: `retrieval.document_ids` partial; `retrieval.permission_context` none; `control.canary_triggered` none.
- Weakened limb, that several of the seven security-only fields tier Optional or Not required: holds, 5 of 7.
<!-- /generated:verdict -->

## 1. Scope and threat model in brief

Security logging for LLM applications and agents that retrieve documents and
call tools: which events to emit, which fields each carries, and a measured
tier for each field. It layers on the OpenTelemetry GenAI conventions, pinned
in `schema/otel-mapping.md`: of its 37 fields, 13 map fully, 6 map partially
and 18 have no equivalent.

Ten attack classes from the OWASP Top 10 for LLM Applications 2025, with MITRE
ATLAS references in `docs/attack-class-references.md`: A1 direct prompt
injection, A2 indirect prompt injection, A3 sensitive information disclosure,
A4 excessive agency, A5 improper output handling, A6 retrieval corpus
poisoning, A7 system prompt leakage, A8 unbounded consumption, A9 cross-tenant
retrieval and A10 staged exfiltration.

The evidence: an agent on the Claude Agent SDK, pinned to `claude-haiku-4-5`,
with six tools over a fictional insurer's documents and no network access; 100
attack trials scored by oracles written before the runs; 100 benign sessions;
seven detectors written against fixtures; and an ablation that nulled each
field in the logs and re-ran them. The tiers are evidence about this schema and
these detectors, not a general ranking. Separately,
`docs/vendor-gap-analysis.md` found none of the seven security-only fields on
any of the 6 vendor surfaces assessed; that supports the case for a profile but
does not test the claim, and most Azure verdicts are unconfirmed, not absent.

## 2. The event model

One JSON object per line, validated against `schema/event.schema.json`, in six
event types: `session_start`, `turn`, `retrieval`, `tool_pre`, `tool_post` and
`session_end`. A group in an event carries all its registered keys, null where
they do not apply, so the ablation nulls a key and never deletes one.

## 3. The field register

**Headline: undertested, with weakened, the literal reading of methodology
Section 9, beside it. The claim is not refuted.** Two of the seven
security-only fields could be tested at all, and both tier Required; the other
five tier Not required without ever being tested. Undertested is the reading
ruled at M5, before the sweep and after the M4 baseline was known.

Tiers were applied mechanically at M5 from a sweep of 37 fields singly and 103
pairs, over the 100 attack trials and 100 benign sessions. Each field's rationale and attribute are in `schema/fields.yaml` and
`schema/otel-mapping.md`.

### 3.1 Tiers and the evidence for each

<!-- generated:register -->
| Field | OTel | Security only | Tier | Deciding cells | Cells, A1 to A10 |
|---|---|---|---|---|---|
| `session.id` | full |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.start_time` | partial |  | **Optional** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.user_id` | full |  | **Optional** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.tenant_id` | none |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.client_app` | none |  | **Optional** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.agent_id` | full |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.config_version` | none |  | **Optional** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.index` | none |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.timestamp` | partial |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.model_id` | full |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.model_version` | full |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.tokens_in` | full |  | **Not required** | none | `nt nt nt nt nr nr nr .c nr ab` |
| `turn.tokens_out` | full |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.latency` | partial |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.finish_reason` | full |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.prompt_text` | full |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.prompt_hash` | none |  | **Optional** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.response_text` | full |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.response_hash` | none |  | **Optional** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.system_prompt_version` | partial |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.redaction_applied` | none |  | **Optional** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `retrieval.document_ids` | partial |  | **Required** | A5 X 1/1 to 0/1; A6 X 10/10 to 0/10 | `nt nt nt nt X X nr nr nr ab` |
| `retrieval.chunk_ids` | none |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `retrieval.scores` | none |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `retrieval.query_text` | full |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `retrieval.source_provenance` | none | yes | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `retrieval.permission_context` | none | yes | **Required** | A9 X 10/10 to 0/10 | `nt nt nt nt nr nr nr nr X ab` |
| `action.tool_name` | full |  | **Optional** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.tool_arguments` | full |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.result_hash` | partial |  | **Optional** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.result_bytes` | none |  | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.permission_decision` | none | yes | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.egress_target` | none | yes | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.context_document_ids` | none | yes | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `control.canary_triggered` | none | yes | **Required** | A7 X 1/1 to 0/1; A9 X 10/10 to 0/10 | `nt nt nt nt nr nr X nr X ab` |
| `control.policy_version` | none |  | **Optional** | none | `nt nt nt nt nr nr nr nr nr ab` |
| `control.block_reason` | none | yes | **Not required** | none | `nt nt nt nt nr nr nr nr nr ab` |

Codes, as in `results/necessity-matrix.md`: `X` the class became undetectable with the field nulled, `.` tested with no measurable effect, `nr` not read by the class's counted detector, `nt` no successful trial, `ab` absent, and the suffix `c` the circular A8 column. A5 and A9 were the holdouts, and the A5 and A7 cells each rest on one successful trial. The tiers of `retrieval.permission_context` and `control.canary_triggered` rest on A9 cells, which record how the detector counted for A9, `d-a03`, did when a field was nulled. That A9 result carries its exposure: the working session that built the detectors knew both holdout outcomes, the project's private working notes at M4 disclosed A9's retrieval signature to any session that read them, the detectors were authored from fixtures only, and the result is weakened evidence, not a clean holdout.
<!-- /generated:register -->

### 3.2 Reading the tiers

- **Not required is not evidence of no signal:** 23 of the 24 Not required
  fields were never read by a detector with a successful class to detect.
- **`action.egress_target`:** Not required because no A1 trial succeeded, yet
  the A1 oracle fired on 1 of 100 benign sessions and on none of the 10 A1
  attack trials, and the destination separates them; over M7b it would tier
  Required (Section 3.3).
- **`session.id`** is retained whatever its tier: the sweep took one file as one
  session. Predicted and computed tiers agree on 9 of 37 fields.

### 3.3 Read over the M7b local pass, not applied

The sweep re-run over the 91 attack trials completed on `granite4.1:3b`: 18/91
successes against 32/100 on `claude-haiku-4-5`, with A6 and A8 unmeasured.

<!-- generated:m7b -->
| Field | Tier at M5, applied | Tier the rule would give over the local pass, not applied |
|---|---|---|
| `action.egress_target` | Not required | Required |

Cells that differ from M5: 148 of 370, of which 5 are in measured states:

- `turn.tokens_in`, A8: `.c` at M5, `nt` on the local pass.
- `retrieval.document_ids`, A6: `X` at M5, `nt` on the local pass.
- `action.egress_target`, A1: `nt` at M5, `X` on the local pass.
- `control.canary_triggered`, A1: `nt` at M5, `X` on the local pass.
- `control.canary_triggered`, A7: `X` at M5, `nt` on the local pass.

The rest are `nr` and `nt` changing places as classes gained or lost successful trials. The headline the rule would give is undertested, as at M5. Local model `granite4.1:3b`; false positive denominator: the hundred M3 sessions, captured on claude-haiku-4-5.
<!-- /generated:m7b -->

## 4. The tiering rule

From `docs/methodology.md` Sections 3 and 4, committed on its own on 12 August
2026 as the second commit. **Required:** removing the field makes a
class undetectable. **Recommended:** removing it cuts detection by 20
percentage points or more, or pushes a false positive rate above 10 per cent,
with nothing going dark. **Optional:** no measurable effect, but a reason to
keep it written before the sweep. **Not required:** neither. M5's readings of
the gaps are in `ablation/rulings.py`.

**The order of commits after the history rewrite.** This repository was created
on 30 September 2026, after every capture, and its history was rewritten once
to take the owner's personal data out, every commit's recorded dates copied
unchanged. Git dates are set by whoever commits, so what a reader can check is
the order: the pre-committed rules are the second commit, before the schema,
any detector and any capture.

## 5. Retention guidance by tier

Retain Required and Optional fields; Not required is **not a recommendation to
discard**, and `session.id` and `action.egress_target` are always kept. Hashing
content cut benign raw bytes by 11.2 per cent; `control.canary_triggered` must
be set before any text is hashed or cut. Detail: `results/volume.md` Section 5.

## 6. Volume and cost model

A8 is 75.2 per cent of the attack corpus's estimated spend but 48.6 per cent of
its raw bytes. The figures in `results/volume.md` describe this lab's events,
not agent logging in general.

## 7. SIEM mapping

Seven Sigma rules in `detect/sigma/`, none for A5, A9 or A10, whose attack never
reached the model in any of the 10 trials on `claude-haiku-4-5`.
`docs/sentinel-mapping.md` sets out a Sentinel table, a Data Collection Rule and
KQL queries, none deployed or run.

## 8. Framework mapping

Identifiers only, re-checked on 1 October 2026 in
`docs/framework-references.md`; no claim of compliance.

- **DSIT Code of Practice, Principle 12**, log and analyse actions: Sections 2
  and 3 say which fields.
- **NCSC guidelines, Section 4**, "Monitor your system's behaviour" and "input":
  the turn, content and action groups, with Section 5 on how much to keep.
- **ETSI TS 104 223 V1.1.1, clause 5.4.2**, logs required without saying what
  they hold: Section 3. It shares the DSIT principle's number, so the two are not
  independent. ETSI EN 304 223, built on it, is at V2.1.1 and not mapped.

## 9. Limitations

- **Circularity:** one author designed the schema, the attacks and the
  detectors, with no independent review.
- **A small corpus:** ten trials per class and 100 benign sessions, so fixed
  thresholds and every rate as a fraction.
- **What could be tested:** A1 to A3 were refusals, A4 a baseline, and A10 is
  absent, not a zero. Detection counts successful trials only. The A5 and A7
  cells rest on one trial each. Recommended is empty by structure. 30 of the 37
  fields are read by no detector. The A8 detector restates its oracle. The A4
  oracle fires on 45 of 100 benign sessions, a task-set mismatch. The rule never
  credits a field for false positives it prevents.
- **The holdout:** `d-a03`, written for A3, caught 10 of 10 successful A9
  trials with 0/100 benign false positives. That A9 result carries its
  exposure: the working session that built the detectors knew both holdout
  outcomes, the project's private working notes at M4 disclosed A9's retrieval
  signature to any session that read them, the detectors were authored from
  fixtures only, and the result is weakened evidence, not a clean holdout.
- **Rules read after the baseline:** the undertested reading and the list of
  Optional fields were ruled at M5, after the M4 baseline and before the sweep.
- **One model:** methodology Section 7.3 left stability across models untested
  until M7b, which is one small local model at a context of 65,536 tokens,
  with A6 and A8 unmeasured, a Claude-captured benign denominator, a route
  Anthropic does not support, and invented mailboxes outside `.invalid`, though
  nothing was sent. Tiering across models is future work. Extended thinking was
  off throughout.
- **The instrument:** `session_end` carries no event time and no field names a
  session's task; the Sentinel queries and the cap outcome path have never run;
  `versions.claude_cli` names a CLI that never ran (all sessions ran the bundled
  2.1.233); and `corpus.digest` depends on the working tree, so a fresh clone computes
  a different digest from the one the manifests record.
- **Vendor verdicts** rest on documentation read on 23 September 2026, with no
  vendor log observed.
