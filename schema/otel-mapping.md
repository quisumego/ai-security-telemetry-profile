# Mapping to the OpenTelemetry GenAI semantic conventions

**Stage:** M0, Rules and schema

**Purpose:** Each of the profile's fields mapped to the OpenTelemetry GenAI
conventions at a pinned commit, with every convention string in one place. For
anyone adopting the `gen_ai.*` names.

---

## 1. The pinned snapshot

The conventions are moving, so the mapping is pinned to a dated commit; a later
change to them is a single edit here.

| Item | Value |
|---|---|
| Repository | `open-telemetry/semantic-conventions-genai` |
| Pinned commit | `8d3e4a0f3c34a46f6edb9c71e8666e02e6bf3958` |
| Commit date | 10 August 2026 |
| Retrieved and verified | **12 August 2026** |
| Tagged releases at retrieval | none (0 releases, 0 tags) |
| Schema URL | not yet published, recorded as outstanding in the repository README |
| Stability of every GenAI attribute at retrieval | Development |

The GenAI conventions moved out of the main
`open-telemetry/semantic-conventions` repository in v1.42.0 in June 2026; the
copies left there are marked deprecated and point to the new location. At the
retrieval date no GenAI span, event, metric or attribute was stable, and the
dedicated repository had no versioned release. `user.id` comes from the general
OpenTelemetry registry, verified the same day, also at Development status. No
attribute name here or in `schema/fields.yaml` was written from memory.

## 2. How to read the mapping

| Mapping | Meaning |
|---|---|
| **full** | An OpenTelemetry attribute carries the same meaning. Adopt the `gen_ai.*` name. |
| **partial** | A related attribute exists but does not carry the same meaning. The difference is stated. |
| **none** | No equivalent attribute exists in the conventions. |

**Seven fields marked none are flagged `security_only: true`** in the register,
in bold below. They are the profile's hypothesis: that the fields with the
highest detection value are the ones the conventions do not cover.
[`SPEC.md`](../SPEC.md#3-the-field-register) Section 3 gives the result.

## 3. The mapping, field by field

In register order, by group: session, turn, content, retrieval, action and
control.

| ASTP field | Mapping | OpenTelemetry attribute | Note |
|---|---|---|---|
| `session.id` | full | `gen_ai.conversation.id` | |
| `session.start_time` | partial | none | Carried by span start time, not a named attribute |
| `session.user_id` | full | `user.id` | General registry, not `gen_ai.*` |
| `session.tenant_id` | none | | No tenancy attribute in the conventions |
| `session.client_app` | none | | |
| `session.agent_id` | full | `gen_ai.agent.id` | |
| `session.config_version` | none | | |
| `turn.index` | none | | Ordering is implicit in the conventions |
| `turn.timestamp` | partial | none | Carried by span timing, not a named attribute |
| `turn.model_id` | full | `gen_ai.request.model` | |
| `turn.model_version` | full | `gen_ai.response.model` | |
| `turn.tokens_in` | full | `gen_ai.usage.input_tokens` | **Measured wider than the attribute name suggests, see Section 4** |
| `turn.tokens_out` | full | `gen_ai.usage.output_tokens` | |
| `turn.latency` | partial | `gen_ai.response.time_to_first_chunk` | Time to first chunk is not total turn latency |
| `turn.finish_reason` | full | `gen_ai.response.finish_reasons` | |
| `content.prompt_text` | full | `gen_ai.input.messages` | Content capture is opt-in in the conventions |
| `content.prompt_hash` | none | | |
| `content.response_text` | full | `gen_ai.output.messages` | Content capture is opt-in in the conventions |
| `content.response_hash` | none | | |
| `content.system_prompt_version` | partial | `gen_ai.system_instructions` | The conventions carry the instruction content, not a version identifier |
| `content.redaction_applied` | none | | |
| `retrieval.document_ids` | partial | `gen_ai.retrieval.documents` | An unstructured attribute that may carry identifiers; no dedicated identifier attribute |
| `retrieval.chunk_ids` | none | | |
| `retrieval.scores` | none | | |
| `retrieval.query_text` | full | `gen_ai.retrieval.query.text` | |
| **`retrieval.source_provenance`** | **none** | | Security-only. No trust labelling of retrieved material exists in the conventions |
| **`retrieval.permission_context`** | **none** | | Security-only. No access-scope attribute exists in the conventions |
| `action.tool_name` | full | `gen_ai.tool.name` | |
| `action.tool_arguments` | full | `gen_ai.tool.call.arguments` | |
| `action.result_hash` | partial | `gen_ai.tool.call.result` | The conventions carry the result content, not a hash |
| `action.result_bytes` | none | | |
| **`action.permission_decision`** | **none** | | Security-only. No authorisation outcome attribute exists in the conventions |
| **`action.egress_target`** | **none** | | Security-only. Destinations sit inside free-form tool arguments in the conventions |
| **`action.context_document_ids`** | **none** | | Security-only. The conventions log retrieval and tool calls separately and define nothing that links them |
| **`control.canary_triggered`** | **none** | | Security-only |
| `control.policy_version` | none | | |
| **`control.block_reason`** | **none** | | Security-only |

No group in the conventions corresponds to the control group.

## 4. What `turn.tokens_in` counts

**`turn.tokens_in` sums the uncached, cache creation and cache read input
counts**, not the provider's own `input_tokens` figure alone. Recorded at M1, on
17 August 2026, before the first scored capture.

Under prompt caching the provider's `input_tokens` counts only the uncached
remainder: the M1 authentication probe reported `input_tokens` of 10 against
4,601 cache creation tokens for the same call. Recording 10 would leave the
field blind to the growth it exists to detect, and the A8 measurement would be
meaningless. The mapping stays `full`, because the field carries the quantity
the attribute names, total tokens sent into the model call. Compared with a
provider's own billing figures, this field reads higher by the cached portion.

## 5. Summary at the pinned snapshot

| Mapping | Field count |
|---|---|
| full | 13 |
| partial | 6 |
| none | 18 |
| **Total** | **37** |

Of the 18 fields with no equivalent, **7 are flagged security-only** and form
the hypothesis under test.

**Attributes the profile does not adopt** are omitted on purpose: sampling
parameters, embeddings, evaluation scoring, memory stores, prompt management
and workflow naming carry no detection role in the threat model in `SPEC.md`,
so none is emitted.

## 6. Re-checked 1 October 2026

The mapping above is stated as at the pinned commit, with a live check beside
it. The register is not edited.

| Item | Value |
|---|---|
| Repository head read | `b31e9e8ea26ac1c086d3313d474e31d7c3f391ae`, 30 September 2026, 33 commits after the pinned commit |
| Releases and tags at the head | none |
| Read at | 21:28 UTC: `model/gen-ai/registry.yaml` at both commits, and `model/user/registry.yaml` on `main` of `open-telemetry/semantic-conventions` |

- Every attribute mapped above is present at the head, at Development
  stability as at the pin, and none is deprecated. No GenAI attribute is
  stable. `user.id` is still Development in the general registry.
- Three of them carry longer notes than at the pin, and none of the additions
  changes a mapping. `gen_ai.usage.input_tokens` adds an example of
  per-modality and cached counts as subsets of the total.
  `gen_ai.response.finish_reasons` adds how its positions align with the
  generations and when to report `error`. `gen_ai.output.messages` adds that
  finish reasons stay aligned with what the provider returned.
- Since the pin the registry has grown from 63 to 79 attributes. The two
  removed, `gen_ai.token.type` and `gen_ai.usage.cache_creation.input_tokens`,
  are not mapped by this profile.
- At the pin, the note on `gen_ai.usage.input_tokens` already says the value
  should include cached tokens, so `turn.tokens_in` carries what the attribute
  defines. Section 4 compares it with a provider's own uncached `input_tokens`
  figure, not with the attribute.

---

**Sources:** `open-telemetry/semantic-conventions-genai` at the pinned commit and at its head on 30 September 2026; `model/user/registry.yaml` in `open-telemetry/semantic-conventions`.
