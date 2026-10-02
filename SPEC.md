# AI Security Telemetry Profile (ASTP)

> **Status: complete, written at M8 on 1 October 2026.** This document is the
> deliverable. Every figure in it comes from a committed result file. The blocks
> between `generated` markers are written by `.venv/bin/python -m spec.render
> --write` from `schema/fields.yaml` and the results, and a test requires a
> fresh render to reproduce them. Every other figure is listed in
> `spec/figures.yaml` with the file and key it comes from, and a test holds each
> one to its source.
>
> **The result in brief.** The profile set out to test one claim: that the
> fields with the most detection value are the ones the OpenTelemetry GenAI
> conventions do not cover, the seven this register flags `security_only`. The
> measurement says **undertested**. Read literally, the falsification rule
> committed before any capture, methodology Section 9, says **weakened**. Both
> words are published, and the claim is not refuted. Undertested is M5 ruling
> 8's reading of Section 9, ruled on 22 September 2026: before the ablation
> sweep ran, but after the M4 baseline had shown which classes had a
> successful attack to detect.
>
> **Stages.** The work ran in stages, and these documents name them: M0, the
> rules and the schema; M1, the lab agent; M2, the attack captures; M3, the
> benign captures; M4, the detectors and their baseline; M5, the ablation and
> the tiers; M6, volume and the Sentinel mapping; M7, the vendor gap; M7b, the
> second-model cross-check; M8, this specification. A ruling cited by number
> from M5 on is in that stage's `rulings.py`, so M5 ruling 8 is in
> `ablation/rulings.py`; earlier rulings are in `docs/build-log.md`. The build
> log and the methodology also cite the plan, the checklist and the handover:
> the author's private working notes, kept outside the repository.

<!-- generated:verdict -->
**Headline: undertested.** Read literally, methodology Section 9 says **weakened**. The claim is not refuted.

- Tiers over the 37 fields: 3 Required, 0 Recommended, 10 Optional, 24 Not required.
- Security-only fields that could be tested at all: 2 of 7, `control.canary_triggered` and `retrieval.permission_context`. Each tiers Required.
- The other 5 tier Not required without ever being tested: `action.context_document_ids`, read by no detector; `action.egress_target`, read only by d-a01, d-a02, whose classes have no successful trial; `action.permission_decision`, read by no detector; `control.block_reason`, read by no detector; `retrieval.source_provenance`, read only by d-a02, whose classes have no successful trial.
- Refuted limb, that the Required fields are predominantly ones the conventions already cover: does not hold. None of the 3 Required fields has a full OpenTelemetry mapping: `retrieval.document_ids` partial; `retrieval.permission_context` none; `control.canary_triggered` none.
- Weakened limb, that several of the seven security-only fields tier Optional or Not required: holds, 5 of 7.
<!-- /generated:verdict -->

The tiers are derived against one model, `claude-haiku-4-5`, on this lab's
synthetic corpus. They are evidence about this schema and these detectors, not a
general ranking of logging fields, and Section 9 says how far they reach.

## 1. Scope and threat model in brief

**What the profile covers.** Security logging for LLM applications and agents
that retrieve documents and call tools: which events to emit, which fields each
event carries, and a tier for each field that says how much detection depends on
it, measured rather than asserted.

**Where it sits.** The profile is layered on the OpenTelemetry GenAI semantic
conventions, as pinned in `schema/otel-mapping.md`, and adopts their `gen_ai.*`
names wherever an equivalent exists. Of its 37 fields, 13 map fully to an
attribute of the conventions, 6 map partially and 18 have no equivalent. Seven
of those eighteen are flagged `security_only`. They are what the profile adds
for detection, and they are the hypothesis the measurement was built to test.

**The threat model.** Ten attack classes, with the OWASP Top 10 for LLM
Applications as the spine and MITRE ATLAS techniques cross-referenced. The
identifiers are those recorded in `docs/attack-class-references.md` on 12 August
2026 and re-checked against their live sources on 1 October 2026.

| Class | What it is | OWASP | MITRE ATLAS |
|---|---|---|---|
| A1 | Direct prompt injection | LLM01:2025 | `AML.T0051.000` |
| A2 | Indirect prompt injection via a retrieved document | LLM01:2025 | `AML.T0051.001`, `AML.T0066` |
| A3 | Sensitive information disclosure | LLM02:2025 | `AML.T0057` |
| A4 | Excessive agency, tool misuse | LLM06:2025 | `AML.T0053` |
| A5 | Improper output handling | LLM05:2025 | `AML.T0077` |
| A6 | Retrieval corpus poisoning | LLM04:2025 | `AML.T0070`, `AML.T0071` |
| A7 | System prompt leakage | LLM07:2025 | `AML.T0056`, `AML.T0069.002` |
| A8 | Unbounded consumption | LLM10:2025 | `AML.T0034.002`, `AML.T0029` |
| A9 | Cross-tenant retrieval | LLM08:2025 | no clean identifier, in ATLAS 2026.07 or 2026.09 |
| A10 | Staged exfiltration chain | LLM01:2025 into LLM06:2025 | `AML.T0051.001`, then `AML.T0086` |

LLM03:2025, Supply Chain, and LLM09:2025, Misinformation, are out of scope:
neither is a runtime detection problem a logging profile addresses.

**How the evidence was produced.** A deliberately small lab agent on the Claude
Agent SDK, pinned to `claude-haiku-4-5`, with six tools over a synthetic
document estate written for a fictional UK insurer, Thornfield Mutual, and a
second tenant. 100 attack trials, ten per class, each scored by a
machine-checkable oracle written before the runs, and 100 benign sessions as the
false positive denominator. Seven detectors, authored against throwaway fixtures
and never against a capture. An ablation sweep that nulled each field in the
captured logs and re-ran the detectors, with no model call. Nothing the lab does
reaches the network: its email tool writes to a file in the run directory, its
URL fetcher serves only committed fixtures, and every destination it is
configured with is under the `.invalid` domain.

**Out of scope.** Training-time attacks, model weights, supply chain and
misinformation; a deployed SIEM, since the Sentinel mapping in Section 7 is
documented, not deployed; and any claim about a vendor's product beyond what its
documentation says.

**What vendor defaults record.** A separate analysis, `docs/vendor-gap-analysis.md`,
read Microsoft Foundry's and Amazon Bedrock's logging documentation and found
none of the seven security-only fields available on any of the 6 vendor
surfaces assessed: each is held only by the deployment, or derived by it. That
supports the case for a profile. It does not test the headline claim, and the
two findings are kept apart. Most of the fields Azure could record are
unconfirmed rather than absent, because Azure documents only the header its
resource logs share, so any comparison between the two vendors carries that
qualifier.

## 2. The event model

One JSON object per line, validated against `schema/event.schema.json` when it
is written, so a malformed event fails the run that produced it. Six event types,
emitted from these points:

| Event type | Emitted by | Groups it carries |
|---|---|---|
| `session_start` | the harness, when a session opens | session, content, control |
| `turn` | the harness, once per model call | session, turn, content, control |
| `retrieval` | the tool that brought content into context: one per search result chunk, and one per claim record, case file or fetched page read | session, turn, retrieval, control |
| `tool_pre` | the pre-tool-use hook, on every call, permitted or not | session, turn, action, control |
| `tool_post` | the post-tool-use hooks, on success and on failure | session, turn, action, control |
| `session_end` | the harness, when a session closes | session, control |

The groups carried are those the committed captures carry for each type. The
schema requires the session group on every event and the turn, retrieval or
action group on the event type of that name.

Three properties the measurement depends on:

- **The emitter reads its group keys from `schema/fields.yaml`**, so the events
  cannot drift from the register. An unregistered key raises.
- **A group that appears in an event carries every one of its registered keys,
  null where a value does not apply.** Nulling a field for the ablation therefore
  sets a key that is already there and never deletes one, so the sweep measures
  one thing.
- **Session and turn events come from the harness**, not from session lifecycle
  hooks, because the Python Agent SDK offered none for callbacks when the lab was
  built. The same events are emitted, from the one place that also holds each
  turn's token counts.

Two gaps were found after the schema was frozen and are recorded, not repaired:
a `session_end` event carries no event time, and no field names the task a
session runs. Section 9 lists both.

## 3. The field register

**Headline: undertested, with weakened, the literal reading of methodology
Section 9, beside it. The claim is not refuted.** Two of the seven
security-only fields could be tested at all, and both tier Required. The other
five tier Not required without ever being tested. Undertested is M5 ruling 8's
reading, ruled before the sweep and after the M4 baseline was known.

Every tier was assigned at M5, on 22 September 2026, by applying the
pre-committed rule of Section 4 mechanically to the necessity matrix:
`ablation.matrix --apply-tiers` wrote them into `schema/fields.yaml`, tagged
`tiers-m5` at `e33c700`, from a sweep run against `e32c7ef`. The sweep nulled 37
fields singly and 103 pairs within a group over the 100 attack trials and the
100 benign sessions. The pairs were reported and decide no tier, as ruled. The
tiers are derived against `claude-haiku-4-5` on this corpus.

### 3.1 Tiers and the evidence for each

<!-- generated:register -->
| Field | OTel | Security only | Tier | Why | Deciding cells | Cells, A1 to A10 |
|---|---|---|---|---|---|---|
| `session.id` | full |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.start_time` | partial |  | **Optional** | no measurable detection effect; a stated justification in its M0 rationale, ruled 2026-09-22 | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.user_id` | full |  | **Optional** | no measurable detection effect; a stated justification in its M0 rationale, ruled 2026-09-22 | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.tenant_id` | none |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.client_app` | none |  | **Optional** | no measurable detection effect; a stated justification in its M0 rationale, ruled 2026-09-22 | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.agent_id` | full |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `session.config_version` | none |  | **Optional** | no measurable detection effect; a stated justification in its M0 rationale, ruled 2026-09-22 | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.index` | none |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.timestamp` | partial |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.model_id` | full |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.model_version` | full |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.tokens_in` | full |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr .c nr ab` |
| `turn.tokens_out` | full |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.latency` | partial |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `turn.finish_reason` | full |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.prompt_text` | full |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.prompt_hash` | none |  | **Optional** | no measurable detection effect; a stated justification in its M0 rationale, ruled 2026-09-22 | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.response_text` | full |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.response_hash` | none |  | **Optional** | no measurable detection effect; a stated justification in its M0 rationale, ruled 2026-09-22 | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.system_prompt_version` | partial |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `content.redaction_applied` | none |  | **Optional** | no measurable detection effect; a stated justification in its M0 rationale, ruled 2026-09-22 | none | `nt nt nt nt nr nr nr nr nr ab` |
| `retrieval.document_ids` | partial |  | **Required** | the field's removal makes at least one class undetectable | A5 X 1/1 to 0/1; A6 X 10/10 to 0/10 | `nt nt nt nt X X nr nr nr ab` |
| `retrieval.chunk_ids` | none |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `retrieval.scores` | none |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `retrieval.query_text` | full |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `retrieval.source_provenance` | none | yes | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `retrieval.permission_context` | none | yes | **Required** | the field's removal makes at least one class undetectable | A9 X 10/10 to 0/10 | `nt nt nt nt nr nr nr nr X ab` |
| `action.tool_name` | full |  | **Optional** | no measurable detection effect; a stated justification in its M0 rationale, ruled 2026-09-22 | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.tool_arguments` | full |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.result_hash` | partial |  | **Optional** | no measurable detection effect; a stated justification in its M0 rationale, ruled 2026-09-22 | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.result_bytes` | none |  | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.permission_decision` | none | yes | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.egress_target` | none | yes | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `action.context_document_ids` | none | yes | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |
| `control.canary_triggered` | none | yes | **Required** | the field's removal makes at least one class undetectable | A7 X 1/1 to 0/1; A9 X 10/10 to 0/10 | `nt nt nt nt nr nr X nr X ab` |
| `control.policy_version` | none |  | **Optional** | no measurable detection effect; a stated justification in its M0 rationale, ruled 2026-09-22 | none | `nt nt nt nt nr nr nr nr nr ab` |
| `control.block_reason` | none | yes | **Not required** | no measurable detection effect and no stated justification | none | `nt nt nt nt nr nr nr nr nr ab` |

Codes, as in `results/necessity-matrix.md`: `X` the class became undetectable with the field nulled, `.` tested with no measurable effect, `nr` not read by the class's counted detector, `nt` no successful trial, `ab` absent, and the suffix `c` the circular A8 column. A5 and A9 were the holdouts, and the A5 and A7 cells each rest on one successful trial. The tiers of `retrieval.permission_context` and `control.canary_triggered` rest on A9 cells, which record how the detector counted for A9, `d-a03`, did when a field was nulled. That A9 result carries its exposure: the working session that built the detectors knew both holdout outcomes, the project's private working notes at M4 disclosed A9's retrieval signature to any session that read them, the detectors were authored from fixtures only, and the result is weakened evidence, not a clean holdout.
<!-- /generated:register -->

### 3.2 Reading the tiers

- **A Not required tier is not evidence that a field carries no signal.** 23 of
  the 24 Not required fields read `nr`, `nt` or `ab` in every column: no
  detector counted for a class with a successful trial ever read them. The one
  measured exception is `turn.tokens_in`, `.c` on the circular A8 column. Read a
  field's row before quoting its tier.
- **`action.egress_target` carries three readings, and its M5 tier stands.** At
  M5 it tiers Not required, because no A1 trial succeeded, so there was no
  detection rate to fall. The benign corpus says more: the A1 oracle fired on 1
  of 100 benign sessions, `m3-b100`, an internal handover email that carried a
  tracked reference to a permitted recipient, and on none of the 10 A1 attack
  trials. The destination is what separates the two, and `d-a01`, which reads it
  with the canary flag, fired on 0/100 benign sessions. The tiering rule credits
  a field for the detections it protects and has no way to credit it for the
  false positives it prevents. Read over the M7b local pass, where A1 succeeded
  in 9 of 10 trials, the rule would tier this field Required. That is a
  comparison, Section 3.4, and is not applied.
- **`session.id` is retained whatever its tier.** The sweep took one capture file
  as one session, so nulling the field could not change what a detector saw. A
  real pipeline receives events from many sessions at once and needs it to put a
  session back together: the session-scoped Sentinel rules group by it, and the
  vendor gap analysis needs it for A8 and A9.
- **`turn.tokens_in` is one of A8's two routes on a vendor surface.** It tiers
  Not required because `d-a08` fired first on the count of tool calls, which
  reads no field.
- **Predicted and computed tiers agree on 9 of 37 fields.** `predicted_tier` was
  written into the register before any run and has not been edited. Where the
  two disagree, the result stands.
- **Optional rests on a stated reason, not a measurement.** The 10 Optional
  fields had no measurable effect and carry an incident response, forensic or
  regulatory reason in their M0 rationale, which the owner accepted field by
  field at M5.

### 3.3 Field definitions

<!-- generated:definitions -->
| Field | Group | Type | OTel mapping | Attribute at the pinned commit | Rationale |
|---|---|---|---|---|---|
| `session.id` | session | string | full | `gen_ai.conversation.id` | Correlates every event in one interaction. Without it, events cannot be grouped and no multi-step attack chain can be reconstructed. |
| `session.start_time` | session | string | partial | none | Anchors the forensic timeline for a session. Incident response value rather than detection value. |
| `session.user_id` | session | string | full | `user.id` | Attribution of activity to a principal. Needed to tell a compromised account from a hostile one, and to establish the expected access scope. |
| `session.tenant_id` | session | string | none | none | Records which tenant the session belongs to. Cross-tenant retrieval is only detectable if the session tenant can be compared with the tenant that owns each retrieved document. |
| `session.client_app` | session | string | none | none | Origin of the request. Useful for scoping an incident to one surface, weak as a detection signal on its own. |
| `session.agent_id` | session | string | full | `gen_ai.agent.id` | Identifies which agent handled the session. In a single-agent lab this is constant, so it is expected to carry no detection signal here. |
| `session.config_version` | session | string | none | none | Reproducibility marker. Already recorded in the run manifest, and constant within a corpus, so no detection signal is expected. |
| `turn.index` | turn | integer | none | none | Ordering within a session. Ordering can usually be recovered from timestamps, so this is expected to be redundant. |
| `turn.timestamp` | turn | string | partial | none | Rate and burst analysis, and the ordering of a staged chain. Needed to distinguish sustained abuse from normal use. |
| `turn.model_id` | turn | string | full | `gen_ai.request.model` | Which model was asked. Constant in this lab because the model is pinned, so no detection signal is expected from the corpus. |
| `turn.model_version` | turn | string | full | `gen_ai.response.model` | Which model answered. Pinned for the whole corpus, therefore zero variance and no detection signal. Predicted to fail the ablation. |
| `turn.tokens_in` | turn | integer | full | `gen_ai.usage.input_tokens` | Input volume. A primary signal for unbounded consumption and for oversized injected content arriving through retrieval. |
| `turn.tokens_out` | turn | integer | full | `gen_ai.usage.output_tokens` | Output volume. Bulk disclosure and runaway generation both show here. |
| `turn.latency` | turn | number | partial | `gen_ai.response.time_to_first_chunk` | Resource exhaustion often shows as latency before it shows as token count. Expected to be correlated with token counts and therefore possibly redundant. |
| `turn.finish_reason` | turn | string | full | `gen_ai.response.finish_reasons` | Distinguishes a completed answer from a truncated or refused one. Separates attack refusal from attack failure. |
| `content.prompt_text` | content | string | full | `gen_ai.input.messages` | The instruction the model received. Direct injection is visible here and nowhere else. |
| `content.prompt_hash` | content | string | none | none | Integrity and correlation without retaining the text. Supports a deployment that declines to store content. No detection signal expected when the text itself is present. |
| `content.response_text` | content | string | full | `gen_ai.output.messages` | What the model said. Sensitive disclosure and system prompt leakage are both observable only in the response. |
| `content.response_hash` | content | string | none | none | Integrity of the response, and detection of identical responses repeated across sessions. Expected to be redundant when response text is present. |
| `content.system_prompt_version` | content | string | partial | `gen_ai.system_instructions` | Identifies which system prompt was in force, so leaked fragments can be matched against a known text rather than judged by eye. |
| `content.redaction_applied` | content | boolean | none | none | Records whether content was redacted before storage. Data protection and evidential value rather than detection value. |
| `retrieval.document_ids` | retrieval | array of string | partial | `gen_ai.retrieval.documents` | Which documents were retrieved. The link between a planted document and a changed answer runs through this field. |
| `retrieval.chunk_ids` | retrieval | array of string | none | none | Sub-document granularity. Locates which passage carried injected content. Expected to be redundant with document identifiers in a corpus of small documents. |
| `retrieval.scores` | retrieval | array of number | none | none | Relevance scores. A poisoned document that suddenly outranks legitimate ones is visible here. Weak on its own. |
| `retrieval.query_text` | retrieval | string | full | `gen_ai.retrieval.query.text` | What was asked of the index. Shows whether retrieval was driven by the user or by injected instructions. |
| `retrieval.source_provenance` | retrieval | string | none | none | Labels each retrieved chunk with where it came from and whether that source is trusted. This is what separates content the organisation wrote from content someone else supplied. Indirect injection is a trust problem before it is a content problem, so without provenance the detector has no basis to treat retrieved instructions as suspicious. |
| `retrieval.permission_context` | retrieval | object | none | none | Records the access scope under which retrieval ran and the scope each returned document requires. A document returned outside the caller's scope is a boundary violation, and it is only visible if both sides of the comparison are logged. |
| `action.tool_name` | action | string | full | `gen_ai.tool.name` | Which capability was exercised. The first question in any tool misuse investigation. |
| `action.tool_arguments` | action | object | full | `gen_ai.tool.call.arguments` | What the tool was asked to do. Canary strings appear in outbound arguments, which is how exfiltration is caught by string match rather than by judgement. |
| `action.result_hash` | action | string | partial | `gen_ai.tool.call.result` | Integrity of what a tool returned, without storing the payload. Supports detection of a tool whose output changed unexpectedly. |
| `action.result_bytes` | action | integer | none | none | Size of the tool result. Bulk reads show as volume before they show as content. |
| `action.permission_decision` | action | string | none | none | Records the authorisation outcome for each tool call, including the calls that were permitted. Excessive agency is an authorisation question: a tool used outside its intended task looks identical to legitimate use unless the decision and its basis are logged. Logging only denials hides the case that matters, which is the harmful action that was allowed. |
| `action.egress_target` | action | string | none | none | The destination of any outbound call, recorded as a normalised target rather than buried in free-form arguments. Exfiltration is defined by where data went, so the destination has to be a field a detector can compare against an allow list. |
| `action.context_document_ids` | action | array of string | none | none | Records which retrieved documents were in the model's context at the moment the tool call was made. This is the field that turns "the agent sent an email" into "the agent sent an email while an externally sourced document was in context". Retrieval and action are logged separately by every existing convention, and the causal link between them is exactly what an indirect injection or a staged exfiltration chain consists of. Expected to be the single most load-bearing field in the profile. |
| `control.canary_triggered` | control | boolean | none | none | Fires when a planted high-entropy string leaves the system. Converts exfiltration from a judgement call into a string match, which is what keeps the scoring path free of manual adjudication. |
| `control.policy_version` | control | string | none | none | Which guardrail policy was in force. Constant across the corpus, so no detection signal is expected. Retained for audit if it fails. |
| `control.block_reason` | control | string | none | none | Why a guardrail fired, when one did. Separates an attack the system stopped from an attack that never worked, which are different security outcomes that look the same in the response text. |
<!-- /generated:definitions -->

### 3.4 Read over the M7b local pass, not applied

The M5 sweep, unchanged, was re-run over the 91 attack trials completed on a
local model, `granite4.1:3b`, served by Ollama, with the agent, prompts, oracles
and detectors unchanged. The model changed which classes succeed, not only how
often: 18/91 attack successes against 32/100 on `claude-haiku-4-5`. A6's
poisoned document never reached the local model, so A6 is unmeasured there, and
A8 completed one trial before the server failed and the pass stopped it.

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

Quoted as committed, from `docs/methodology.md` Sections 3 and 4. That file was
committed on its own on 12 August 2026, as the second commit in this
repository, `c8b28dd`, before the schema, any detector and any capture.

<!-- generated:rule -->
> **3. The tiering rule**
>
> Stated verbatim. Tiers are assigned at M5 by applying this rule mechanically to
> the necessity matrix, with no adjustment.
>
> > **Required:** removing the field makes at least one attack class undetectable.
> >
> > **Recommended:** removing the field materially degrades detection for at least
> > one class, with nothing going dark.
> >
> > **Optional:** no measurable detection effect, but a stated incident response,
> > forensic or regulatory justification for keeping it.
> >
> > **Not required:** no measurable detection effect and no stated justification.
>
> **"Undetectable" means the detection rate for that class falls to zero**, that
> is 0/10 successful trials detected, when the field is nulled. Nothing softer
> counts as undetectable.
>
> **"A stated justification"** for the Optional tier means a written reason
> recorded in `schema/fields.yaml` before the sweep, not one composed afterwards
> to rescue a field that failed. A field with no detection effect and no
> pre-existing justification is tiered **Not required** and is published as such,
> including any field this profile added for security reasons. Publishing the
> failures is what makes the successes worth reading.
>
> **4. The materiality threshold**
>
> Fixed with exact numbers. Not to be changed after the first scored run.
>
> A field's removal **materially degrades** detection for an attack class when
> either of the following holds:
>
> 1. **Detection rate for that class falls by 20 percentage points or more.**
>    With ten trials per scenario this is a fall of at least 2 successful trials
>    out of 10. A fall of a single trial, 10 percentage points, does not count.
>
> 2. **The false positive rate for that detector rises above 10 per cent**, that
>    is more than 10 of approximately 100 benign sessions produce a detection.
>    The benign corpus gives a resolution of about 1 percentage point, so this
>    threshold is well supported by the denominator.
>
> Either condition alone is sufficient. The thresholds are stated as fixed
> numbers rather than as statistical tests because the corpus is small and a
> significance test on ten trials would give a false impression of precision.
> The limitation this creates is stated in Section 7.
>
> **The three states in the necessity matrix**
>
> | State | Meaning |
> |---|---|
> | `X` | The attack class becomes undetectable without this field: detection falls to 0/10 |
> | `x` | Detection degrades materially, as defined above, with nothing going dark |
> | `.` | No measurable effect |
<!-- /generated:rule -->

**How M5 read what the rule leaves open**, ruled on 22 September 2026 and
committed in `ablation/rulings.py` before any sweep code existed. An `X` resting
on one successful trial counts. A material fall is one of at least 20
percentage points with detection still above zero, and the false positive limb
holds when a rate at or below 10 per cent before nulling is above it after.
"Covered" means a full OpenTelemetry mapping, "several" means three or more, and
"predominantly" means more than half. The headline reads undertested when fewer
than four of the seven security-only fields could be tested at all, unless it is
refuted, and the literal Section 9 outcome is always printed beside it.

**The order of commits after the history rewrite.** This repository was created
on 30 September 2026, after every capture. Before it was published, its history
was rewritten once to take the owner's personal data out, with every commit's
recorded author and committer dates copied unchanged. Git dates are set by
whoever makes a commit, here as in any repository, so on their own they show the
order in which work was recorded, not when it was done. What a reader can check
is that order: the pre-committed rules are the second commit, before the
schema, any detector and any capture.

## 5. Retention guidance by tier

From `results/volume.md` Section 5, which reads each field's tier from the
register.

| Tier | Guidance |
|---|---|
| Required | Retain at full fidelity. Removing any one of these made a class undetectable. |
| Recommended | No field holds this tier. |
| Optional | Retain. Each carries a stated incident response, forensic or regulatory reason, and most are hashes and identifiers. |
| Not required | **Not a recommendation to discard.** Decide per field, with its volume beside it, and read the caution in Section 3.2 first. |

Two fields are retained whatever their tier: `action.egress_target` and
`session.id`, for the reasons in Section 3.2.

**Content text.** `docs/methodology.md` Section 8.2 set the posture before any
capture: hash always, truncate as a middle path, and keep full text only by
choice, with a lawful basis, a short retention period and redaction applied
before storage, recorded in `content.redaction_applied`. What a posture saves in
volume was measured. Over the benign sessions, hashing both content text fields
cuts raw bytes per session by 11.2 per cent and value bytes by 22.8 per cent;
truncating each at 1,024 characters cuts them by 0.6 and 1.2 per cent. What a
posture costs in detection could not be measured: no detector counted for a
class with a successful trial reads either text field, so every cell for them
reads `ab`, `nr` or `nt`, and this guidance does not claim a posture loses
nothing. One constraint is firm. `control.canary_triggered`, a Required field,
is computed from the full response text, so it must be set at the source, before
any text is hashed or cut.

## 6. Volume and cost model

From `results/volume.json`, written by `cost.model` from the captures. Two
quantities are kept apart, and no figure combines them.

**Model spend of the captures.** The SDK's own estimates, read from the run
manifests, not money spent: the captures ran on a subscription allowance, no
money was spent, and extra usage was off throughout. $2.8318 over the 100
attack sessions and $1.0860 over the 100 benign sessions. A8 is 75.2 per cent of
the attack corpus's estimated spend on its own.

**Telemetry volume.** What the profile would log, read from the events files. A
benign session averaged 10.31 events and 10,219.79 raw bytes, and an attack
session 13.68 events. A8 is 48.6 per cent of the attack corpus's raw bytes
against 75.2 per cent of its spend, because the pages it fetched entered the
model's context and never the log, which records a result's hash and size, not
the result.

**Which groups take the bytes.** In the benign corpus the session group is the
largest, at 23.2 per cent of raw bytes, because it is carried whole on every
event. The content group is 20.3 per cent. Null members, written so that the
sweep could null a key without deleting it, take 10.1 per cent, and a pipeline
need not write them.

**Projections.** From the benign corpus alone, at an assumed 10 sessions per
user per day, which no capture supports: 0.1022 GB a day of raw bytes at 1,000
users and 1.0220 GB at 10,000 under full text, and 0.0908 and 0.9078 GB under
the hash posture. A GB here is 10^9 bytes. No price is attached:
`docs/sentinel-mapping.md` says where a reader takes one from.

**What these figures describe.** ASTP events as this lab emits them: every null
key written, the session group repeated on every event, the user's instruction
repeated on each turn, and no tool result ever logged. They are not a model of
agent logging in general. Raw bytes are the lab's own serialisation, and value
bytes approximate a column store: neither is a billed size.

## 7. SIEM mapping

**Sigma.** Seven rules in `detect/sigma/`, one per detector, state each
detector's intent in a portable form. `detect/detectors.py` is what scored every
figure, and where the two differ the Python wins. There is no rule for A5 or A9,
the holdouts, and none for A10, whose attack never reached the model in any of
the 10 trials on `claude-haiku-4-5`.

**Microsoft Sentinel, documented and not deployed.** `docs/sentinel-mapping.md`
sets out a custom table, `AstpEvents_CL`, of 42 columns on the Analytics plan; a
`Direct` Data Collection Rule for the Logs Ingestion API whose 2,683-character
transformation flattens the six groups into columns using supported functions
only; and one KQL query per detector. Six of the seven queries translate:
`d-a04` only in part, because no field names the task a session runs, and
`d-a07` with a caveat about sessions that straddle the lookback window.
`TimeGenerated` is ingestion time, because a `session_end` event carries no
event time of its own. Every claim on that page about Sentinel and Azure Monitor
cites a Microsoft source read on 22 or 23 September 2026. `siem/sentinel.py`
generates the table, the rule and the queries from the register, and a test
holds them to it.

**None of the queries has been run.** There is no workspace to run them in.
Treat each as a specification to test, not a tested rule.

## 8. Framework mapping

Identifiers only. Intent is paraphrased in original wording, and no text is
reproduced from any of these documents. Each was read on 12 August 2026 and
re-checked against its live source on 1 October 2026, as
`docs/framework-references.md` records.

The claim is narrow. These documents require that AI systems are logged and
monitored. This profile is evidence about which fields make that logging useful
for detecting the attack classes of Section 1. It does not certify compliance
with any of them, and nothing in this repository should be read as doing so.

| Framework | Identifier | Intent, paraphrased | Where ASTP bears on it |
|---|---|---|---|
| DSIT Code of Practice for the Cyber Security of AI, published 31 January 2025 | Principle 12 | Keep logs of system and user actions so that compliance can be shown and incidents investigated, analyse them for anomalies and unexpected behaviour, and watch system state and model performance over time | Sections 2 and 3 say which actions to log and with which fields, and Section 7 sets out analyses over them |
| NCSC Guidelines for Secure AI System Development, version 1.0, published 27 November 2023 | Section 4, Secure operation and maintenance: the guidelines "Monitor your system's behaviour" and "Monitor your system's input" | Measure outputs so that changes affecting security can be seen and told apart from natural drift; monitor and log inputs, such as prompts, so that misuse can be investigated afterwards, within privacy and data protection limits | The turn, content and action groups carry the inputs and outputs, and Section 5 sets how much content to keep, which is the data protection limit the second guideline names |
| ETSI TS 104 223 V1.1.1 (2025-04) | Clause 5.4.2, provisions `5.4.2-1` to `5.4.2-4` | Log system and user actions, the one firm obligation of the four; analyse the logs, monitor internal state and monitor performance over time, each a recommendation | `5.4.2-1` requires the logs without saying what they contain. Section 3 is an answer to that question, for this threat model |

ETSI TS 104 223 and the DSIT Code share the principle's number and nearly its
title, so they are related documents and should not be read as independent
corroboration. The NCSC's second guideline is cited by its live title; the
record of 12 August 2026 has it in the plural. ETSI EN 304 223, the European
Standard that builds on TS 104 223, is published at V2.1.1, as the re-check of
1 October 2026 found. The mapping above is to TS 104 223 V1.1.1 only, and the
EN is not mapped.

## 9. Limitations

Written to be read sceptically, because a reader will find these whether or not
they are stated. `docs/methodology.md` Section 7 stated the first four before
any capture.

**Circularity.** The same person designed the schema, wrote the attacks and
wrote the detectors, and detectors that key on fields the author chose to emit
will tend to find those fields necessary. Two things reduce this and neither
removes it: the detectors were written against observable attack behaviour,
from fixtures, and two classes were held out. Read the register as evidence
about this schema and these detectors.

**A single author.** No one independent reviewed the scenarios, the oracles or
the detectors. Everything is published so that a reader can check the work,
which is a weaker guarantee than someone having checked it.

**A small denominator.** Ten trials per class and 100 benign sessions. Rates are
coarse, so fixed thresholds were used rather than significance tests, and every
rate is given as a fraction.

**What the corpus could and could not test.**

- The four zeros of the attack corpus are not equivalent. A1, A2 and A3 were
  refusals: the attack was put to the model and declined, and A2's injected
  document reached the model in 6 of 10 trials without succeeding in any. A4 is
  a baseline: its prompt carries no attack, and `d-a04` fired on none of the 30
  read-only benign sessions of the same shape, so its zero is a genuine null.
- **A10 is absent from the corpus, not a zero.** Its injected document never
  reached the model in any of the 10 trials, so no session presented the attack,
  and it has no detector.
- Detection is computed over successful trials only, so for the classes with
  none it is not computable, which is different from zero.
- The A5 and A7 cells rest on one successful trial each. No tier depends on them
  alone.
- Recommended is empty by structure, not by evidence: each counted detector
  either reads one field or needs all of its fields together, so nulling a field
  it reads silences it, and a fall short of zero was out of reach.
- 30 of the 37 fields are read by no detector at all, among them
  `action.context_document_ids`, which the register predicted would be the most
  load-bearing field in the profile.
- The A8 detector is circular. `d-a08` uses the A8 oracle's own thresholds, and
  every successful A8 trial made 15 tool calls against a threshold of 10, so the
  A8 column measures nothing independent of the oracle.
- The A4 oracle fires on 45 of 100 benign sessions, because their tasks
  legitimately use tools outside A4's task set. That measures the gap between two
  task definitions, not a false positive rate.
- The rule credits a field only for detections it protects, never for false
  positives it prevents, which is why `action.egress_target` tiers Not required
  (Section 3.2).

**The holdout.** A5 and A9 were held out, committed before any scenario file
existed and opened only after the detector set was frozen. `d-a03`, written for
A3, caught 10 of 10 successful A9 trials with 0/100 benign false positives, so
the gap between developed-against and held-out detection is zero on this
evidence. That A9 result carries its exposure: the working session that built
the detectors knew both holdout outcomes, the project's private working notes at
M4 disclosed A9's retrieval signature to any session that read them, the
detectors were authored from fixtures only, and the result is weakened evidence,
not a clean holdout. `d-a06`, written for A6, caught A5's one successful trial.

**Rules read after some results were known.** The undertested reading of Section
9 (M5 ruling 8) and the list of fields whose M0 rationale counts as a stated
reason for Optional (M5 ruling 4) were both ruled after the M4 baseline was
known and before the sweep ran. Neither text was edited, and the literal Section
9 outcome, weakened, is printed beside the headline wherever the headline
appears.

**One model, one agent, synthetic data.** Methodology Section 7.3 says the
necessity matrix "is expected to be more stable across models than the raw
success numbers, but that expectation is itself untested until M7b runs". It has
run, and the section is left as committed. Over the local pass the headline the
rule would give is unchanged and one tier would move, `action.egress_target` to
Required. 148 of 370 cells differ, 5 of them in measured states, and which
classes succeed changed with the model. That is one comparison, of two models,
not a family, and it has limits of its own:

- `granite4.1:3b` is one small model, run on a CPU with a context of 65,536
  tokens.
- A6 is unmeasured on it: the poisoned document never reached the model.
- A8 is unmeasured on it: one trial completed, then the server answered an
  error and the run was stopped under memory pressure. `results/m7b-crosscheck.json`
  flags A6 as unmeasured and not A8, so this reading of A8 rests on its trial
  count, one completed and one failed.
- The false positive denominator is the benign corpus captured on
  `claude-haiku-4-5`. No local benign pass exists.
- The route, Ollama's Anthropic-compatible endpoint, is one Anthropic says it
  does not support: Claude Code's documentation on LLM gateways, read on 1
  October 2026, says routing Claude Code to non-Claude models through any
  gateway is not supported.
- The local model invented role mailboxes outside the `.invalid` domain in
  `m7b-a06-t04`, `m7b-a06-t09` and `m7b-a06-t10`. Nothing was sent: the lab's
  email tool writes to a file in the run directory.
- Reading tiers across models, for example Required if Required under any model
  tested, would be a new rule written after the results. It is future work, not a
  finding.

Extended thinking was disabled for the whole scored corpus, ruled before any
scenario was written. Thinking may make a model harder to inject, which affects
the absolute success rates this work does not claim, and is not expected to
change which fields carry detection signal. That expectation is untested.

**The instrument.**

- The two schema gaps of Section 2: no event time on `session_end`, and no field
  naming the task a session runs, which `d-a04` needs outside the lab.
- The Sentinel queries have never run (Section 7).
- `lab/agent.py` records a session that ends on the turn or budget cap as an
  outcome instead of crashing, and is tested against stubs. No scored capture
  ended on a cap, so that path has never run live.
- `versions.claude_cli` in the frozen manifests names the command-line client on
  the machine's path, which the lab never ran. The SDK runs its own bundled
  client, version 2.1.233, which the M7b manifests record. Every scored session
  ran on that one version.
- `corpus.digest` hashes the files on disk under its inputs, git-ignored ones
  included, so it identifies the material a session read only where the working
  tree matches the one the captures ran in. The manifests record `5ae2e5c0`; a
  fresh clone computes `65bb7f2a` from the same committed content.

**What the volume figures describe**, and **what the vendor gap can and cannot
say**, are set out in Sections 6 and 1. The vendor verdicts rest on
documentation read on 23 September 2026, with no vendor log record observed, so
where a page is wrong or out of date, so is its verdict.
