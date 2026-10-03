# Class answers and the fields to add

**Stage:** M7, Vendor gap

**Purpose:** Each attack class's answer on every vendor column, and the fields
a deployment has to add to bring each class back. Part of the
[vendor gap analysis](../vendor-gap-analysis.md).

---

## 1. Class by class, on vendor defaults only

Every class with a successful trial becomes undetectable or unconfirmed on
every column. The codes and the method are in
[the answer](../vendor-gap-analysis.md#1-the-answer).

<!-- generated:classes -->
| Class | Counted detector | n | Azure: as shipped | Azure: model layer on | Azure: model layer on, body parsed | Azure: agent layer on | Azure: agent layer on, body parsed | Azure: model and agent layers together | AWS: as shipped | AWS: model layer on | AWS: model layer on, body parsed | AWS: agent layer on | AWS: agent layer on, body parsed | AWS: model and agent layers together |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | d-a01 | 0 | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` |
| A2 | d-a02 | 0 | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` |
| A3 | d-a03 | 0 | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` |
| A4 | d-a04 | 0 | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` |
| A5\* n=1 | d-a06 | 1 | `X` | `X` | `X` | `X` | `X` | `uc` | `X` | `X` | `X` | `X` | `X` | `uc` |
| A6 | d-a06 | 10 | `X` | `X` | `X` | `X` | `X` | `uc` | `X` | `X` | `X` | `X` | `X` | `uc` |
| A7 n=1 | d-a07 | 1 | `X` | `X` | `X` | `X` | `X` | `uc` | `X` | `X` | `X` | `X` | `X` | `uc` |
| A8 c | d-a08 | 10 | `uc` | `uc` | `uc` | `Xc` | `Xc` | `uc` | `uc` | `uc` | `uc` | `Xc` | `Xc` | `uc` |
| A9\* | d-a03 | 10 | `X` | `X` | `X` | `X` | `X` | `uc` | `X` | `X` | `X` | `X` | `X` | `uc` |
| A10 | none | 0 | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` |
<!-- /generated:classes -->

A5 and A9 were the holdouts. The A9 baseline of 10 of 10 carries its exposure:
the working session that built the detectors knew both holdout outcomes, the
project's private working notes at M4 disclosed A9's retrieval signature, the
detectors were authored from fixtures only, and the result is weakened
evidence, not a clean holdout.

## 2. The fields a deployment has to add itself

In priority order: first the fields whose addition returns a class to its
baseline, then every other field the headline column lacks, by tier and
register order.

<!-- generated:additions -->
**Azure, on the headline column (model layer on).**

What returns each class to its baseline, by vendor pass. Each line is one smallest set; where a class has two, either will do.

- A5: `retrieval` records and `retrieval.document_ids`.
- A6: `retrieval` records and `retrieval.document_ids`.
- A7: `turn` records and `control.canary_triggered`.
- A8: `turn` records and `turn.tokens_in`; or `tool_pre` records and `session.id`.
- A9: `retrieval` records, `turn` records, `control.canary_triggered`, `retrieval.permission_context` and `session.id`.

Measured fields, in order:

1. `retrieval.document_ids`, required, in a set for A5, A6
2. `control.canary_triggered`, required, in a set for A7, A9
3. `session.id`, not_required, in a set for A8, A9
4. `retrieval.permission_context`, required, in a set for A9
5. `turn.tokens_in`, not_required, in a set for A8

Then, by tier and register order: `session.start_time` (optional), `session.user_id` (optional), `session.client_app` (optional), `session.config_version` (optional), `content.prompt_hash` (optional), `content.response_hash` (optional), `content.redaction_applied` (optional), `action.tool_name` (optional), `action.result_hash` (optional), `control.policy_version` (optional), `session.tenant_id` (not_required), `session.agent_id` (not_required), `turn.index` (not_required), `turn.model_id` (not_required), `turn.model_version` (not_required), `turn.tokens_out` (not_required), `turn.latency` (not_required), `turn.finish_reason` (not_required), `content.prompt_text` (not_required), `content.response_text` (not_required), `content.system_prompt_version` (not_required), `retrieval.chunk_ids` (not_required), `retrieval.scores` (not_required), `retrieval.query_text` (not_required), `retrieval.source_provenance` (not_required), `action.tool_arguments` (not_required), `action.result_bytes` (not_required), `action.permission_decision` (not_required), `action.egress_target` (not_required), `action.context_document_ids` (not_required), `control.block_reason` (not_required).

**AWS, on the headline column (model layer on).**

What returns each class to its baseline, by vendor pass. Each line is one smallest set; where a class has two, either will do.

- A5: `retrieval` records and `retrieval.document_ids`.
- A6: `retrieval` records and `retrieval.document_ids`.
- A7: `control.canary_triggered`.
- A8: `turn.tokens_in`; or `tool_pre` records and `session.id`.
- A9: `retrieval` records, `control.canary_triggered`, `retrieval.permission_context` and `session.id`.

Measured fields, in order:

1. `retrieval.document_ids`, required, in a set for A5, A6
2. `control.canary_triggered`, required, in a set for A7, A9
3. `session.id`, not_required, in a set for A8, A9
4. `retrieval.permission_context`, required, in a set for A9
5. `turn.tokens_in`, not_required, in a set for A8

Then, by tier and register order: `session.start_time` (optional), `session.user_id` (optional), `session.client_app` (optional), `session.config_version` (optional), `content.prompt_hash` (optional), `content.response_hash` (optional), `content.redaction_applied` (optional), `action.tool_name` (optional), `action.result_hash` (optional), `control.policy_version` (optional), `session.tenant_id` (not_required), `session.agent_id` (not_required), `turn.index` (not_required), `turn.model_id` (not_required), `turn.model_version` (not_required), `turn.latency` (not_required), `turn.finish_reason` (not_required), `content.prompt_text` (not_required), `content.response_text` (not_required), `content.system_prompt_version` (not_required), `retrieval.chunk_ids` (not_required), `retrieval.scores` (not_required), `retrieval.query_text` (not_required), `retrieval.source_provenance` (not_required), `action.tool_arguments` (not_required), `action.result_bytes` (not_required), `action.permission_decision` (not_required), `action.egress_target` (not_required), `action.context_document_ids` (not_required), `control.block_reason` (not_required).
<!-- /generated:additions -->

**A Not required tier is not evidence that a field carries nothing.**
`session.id` is needed here for A8 and A9 once records must be grouped,
`turn.tokens_in` is one of A8's two routes, and `action.egress_target`
separates the A1 attack from benign session `m3-b100`.

---

**Sources:** numbered as in [Sources](sources.md).
