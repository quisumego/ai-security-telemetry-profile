# Mapping to the OpenTelemetry GenAI semantic conventions

**Pinned snapshot**

| Item | Value |
|---|---|
| Repository | `open-telemetry/semantic-conventions-genai` |
| Pinned commit | `8d3e4a0f3c34a46f6edb9c71e8666e02e6bf3958` |
| Commit date | 10 August 2026 |
| Retrieved and verified | **12 August 2026** |
| Tagged releases at retrieval | none (0 releases, 0 tags) |
| Schema URL | not yet published, recorded as outstanding in the repository README |
| Stability of every GenAI attribute at retrieval | Development |

**Why this file exists.** The conventions are moving. Pinning them to a dated
commit and keeping every convention string in one file means a later change to
the conventions is a single edit here, not a hunt through the codebase.

**Status of the conventions at the pinned snapshot.** The GenAI conventions were
moved out of the main `open-telemetry/semantic-conventions` repository in
v1.42.0 in June 2026 and now live in the dedicated repository named above. The
copies that remain in the main repository are marked deprecated and point to the
new location. At the retrieval date no GenAI span, event, metric or attribute
was marked stable, and the dedicated repository had published no versioned
release. This profile is therefore written against a moving target, and says so.

One attribute in the mapping below, `user.id`, comes from the general
OpenTelemetry attribute registry rather than the GenAI conventions. It was
verified on the same date and was also Development status.

No attribute name in this file or in `schema/fields.yaml` was written from
memory. Each was read from the pinned snapshot on the retrieval date.

---

## How to read the mapping

| Mapping | Meaning |
|---|---|
| **full** | An OpenTelemetry attribute carries the same meaning. Adopt the `gen_ai.*` name. |
| **partial** | A related attribute exists but does not carry the same meaning. The difference is stated. |
| **none** | No equivalent attribute exists in the conventions. |

Seven fields marked **none** are flagged `security_only: true` in the register.
They are the profile's hypothesis: the claim under test is that the fields with
the highest detection value are the ones the conventions do not cover. The
ablation at M5 tests that claim and may refute it.

---

## Session group

| ASTP field | Mapping | OpenTelemetry attribute | Note |
|---|---|---|---|
| `session.id` | full | `gen_ai.conversation.id` | |
| `session.start_time` | partial | none | Carried by span start time, not a named attribute |
| `session.user_id` | full | `user.id` | General registry, not `gen_ai.*` |
| `session.tenant_id` | none | | No tenancy attribute in the conventions |
| `session.client_app` | none | | |
| `session.agent_id` | full | `gen_ai.agent.id` | |
| `session.config_version` | none | | |

## Turn group

| ASTP field | Mapping | OpenTelemetry attribute | Note |
|---|---|---|---|
| `turn.index` | none | | Ordering is implicit in the conventions |
| `turn.timestamp` | partial | none | Carried by span timing, not a named attribute |
| `turn.model_id` | full | `gen_ai.request.model` | |
| `turn.model_version` | full | `gen_ai.response.model` | |
| `turn.tokens_in` | full | `gen_ai.usage.input_tokens` | **Measured wider than the attribute name suggests, see below** |
| `turn.tokens_out` | full | `gen_ai.usage.output_tokens` | |
| `turn.latency` | partial | `gen_ai.response.time_to_first_chunk` | Time to first chunk is not total turn latency |
| `turn.finish_reason` | full | `gen_ai.response.finish_reasons` | |

### What `turn.tokens_in` counts, and why it is wider than the attribute

Recorded at M1, on 17 August 2026, before the first scored capture.

The lab emits `turn.tokens_in` as the sum of the uncached, cache creation and
cache read input counts, not as the provider's own `input_tokens` figure alone.

The reason is prompt caching. The register says this field measures input
volume and names oversized injected content and unbounded consumption as what
it is for. Under caching, the provider's `input_tokens` counts only the
uncached remainder of the request: the M1 authentication probe reported
`input_tokens` of 10 against 4,601 cache creation tokens for the same call.
Recording 10 would leave the field blind to exactly the growth it exists to
detect, and the A8 measurement would be meaningless.

The mapping is still stated as `full`, because the field carries the same
quantity the attribute names, total tokens sent into the model call. Anyone
comparing an ASTP capture against a provider's own billing figures should
expect this field to read higher, and the difference is the cached portion.

## Content group

| ASTP field | Mapping | OpenTelemetry attribute | Note |
|---|---|---|---|
| `content.prompt_text` | full | `gen_ai.input.messages` | Content capture is opt-in in the conventions |
| `content.prompt_hash` | none | | |
| `content.response_text` | full | `gen_ai.output.messages` | Content capture is opt-in in the conventions |
| `content.response_hash` | none | | |
| `content.system_prompt_version` | partial | `gen_ai.system_instructions` | The conventions carry the instruction content, not a version identifier |
| `content.redaction_applied` | none | | |

## Retrieval group

| ASTP field | Mapping | OpenTelemetry attribute | Note |
|---|---|---|---|
| `retrieval.document_ids` | partial | `gen_ai.retrieval.documents` | An unstructured attribute that may carry identifiers; no dedicated identifier attribute |
| `retrieval.chunk_ids` | none | | |
| `retrieval.scores` | none | | |
| `retrieval.query_text` | full | `gen_ai.retrieval.query.text` | |
| **`retrieval.source_provenance`** | **none** | | Security-only. No trust labelling of retrieved material exists in the conventions |
| **`retrieval.permission_context`** | **none** | | Security-only. No access-scope attribute exists in the conventions |

## Action group

| ASTP field | Mapping | OpenTelemetry attribute | Note |
|---|---|---|---|
| `action.tool_name` | full | `gen_ai.tool.name` | |
| `action.tool_arguments` | full | `gen_ai.tool.call.arguments` | |
| `action.result_hash` | partial | `gen_ai.tool.call.result` | The conventions carry the result content, not a hash |
| `action.result_bytes` | none | | |
| **`action.permission_decision`** | **none** | | Security-only. No authorisation outcome attribute exists in the conventions |
| **`action.egress_target`** | **none** | | Security-only. Destinations sit inside free-form tool arguments in the conventions |
| **`action.context_document_ids`** | **none** | | Security-only. The conventions log retrieval and tool calls separately and define nothing that links them |

## Control group

| ASTP field | Mapping | OpenTelemetry attribute | Note |
|---|---|---|---|
| **`control.canary_triggered`** | **none** | | Security-only |
| `control.policy_version` | none | | |
| **`control.block_reason`** | **none** | | Security-only |

No group in the conventions corresponds to the control group.

---

## Summary at the pinned snapshot

| Mapping | Field count |
|---|---|
| full | 13 |
| partial | 6 |
| none | 18 |
| **Total** | **37** |

Of the 18 fields with no equivalent, **7 are flagged security-only** and form
the hypothesis under test.

## Attributes present in the conventions that this profile does not adopt

Recorded so the omission is deliberate rather than accidental. The conventions
also define attributes for sampling parameters, embeddings, evaluation scoring,
memory stores, prompt management and workflow naming. None of them carries a
detection role in the threat model in `SPEC.md`, so none is emitted. If the
ablation shows the profile is missing a signal these would have covered, that
is a finding and it gets reported.
