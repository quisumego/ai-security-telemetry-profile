# Vendor gap analysis

> **Documentation only.** No Azure or AWS resource was created, no console was
> signed in to, and no model call was made. Every claim about a vendor is cited
> to a numbered page read on 23 September 2026.

The question: **with vendor defaults only, which of the ten attack classes stay
detectable** on Microsoft Foundry, which the plan calls "Azure AI Foundry" [1],
and on Amazon Bedrock? The verdicts are in `vendor_gap/evidence.yaml`, each with
the pages it rests on. `vendor_gap/analysis.py` computes the class answers from
the captures and writes `results/vendor-gap.json` and the blocks between
`generated` markers here, and `tests/test_vendor_gap.py` holds both to it. A
field is recorded absent only where a cited page lists a record's full fields,
or where only the deployment holds the value. The field-by-field verdicts and
the rows that decide each answer are in those two files.

The lab runs on Anthropic's API, not on either vendor, so the question is
hypothetical: what the vendor's own records would carry had the agent's model
calls gone through it, the model layer, or had the agent been hosted there,
the agent layer. Each surface is read once its own switch is set, with the
as-shipped reading beside it. On AWS that switch has the reader choose
modalities [15], and Text is taken because the lab's traffic is text only; read
with Text as a further setting, seven fields and three event types move from
available by default to available with configuration, and no class answer
changes, which a test repeats.

## The answer

<!-- generated:headline -->
- **Azure, model layer on:** A5 `X`, A6 `X`, A7 `X`, A8 `uc`, A9 `X`.
- **AWS, model layer on:** A5 `X`, A6 `X`, A7 `X`, A8 `uc`, A9 `X`.

**No class stays detectable on any single surface of either vendor**, as shipped or switched on, with or without the bodies parsed.
Across the ten single-surface columns: A5, A6, A7, A9 read `X`; A8 reads `Xc`, `uc`.

**Security-only fields a vendor column counts as available: 0 of 7.** On all six surfaces every one reads absent, in the form caller supplied or derivable.
<!-- /generated:headline -->

`X` means the class becomes undetectable, `uc` that the answer turns on
something the pages do not settle, and `c` marks A8's circular column. A8
survives on the model layers only if the vendor's input token count means what
the register's does: Bedrock does not say whether it includes cached tokens
[15], and Azure documents no per-call token field [2][4].

**The question can be answered for five classes only, and for two of them on a
single session.** A1 to A4 have no successful trial and A10 is absent; A5 and A7
rest on one trial each; and A8's detector restates its oracle. A5 and A9 are the
holdouts, and the A9 baseline of 10 of 10 carries its exposure: the working
session that built the detectors knew both holdout outcomes, the project's
private working notes at M4 disclosed A9's retrieval signature, the detectors
were authored from fixtures only, and the result is weakened evidence, not a
clean holdout.

## Sources

Every page was read on the date given, from its own text. "Page updated" is a
Microsoft page's `updated_at`; no AWS page carries a date. Where a page
redirected, both addresses are given.

<!-- generated:sources -->
| # | Source | Page updated | Retrieved |
|---|---|---|---|
| 1 | Microsoft Learn, *Enable diagnostic logging for Microsoft Foundry*, https://learn.microsoft.com/en-us/azure/foundry/how-to/diagnostic-logging | 26 June 2026 | 23 September 2026 |
| 2 | Microsoft Learn, *Monitoring data reference for Azure OpenAI*, https://learn.microsoft.com/en-us/azure/foundry/openai/monitor-openai-reference | 19 May 2026 | 23 September 2026 |
| 3 | Microsoft Learn, *Diagnostic Settings in Azure Monitor*, https://learn.microsoft.com/en-us/azure/azure-monitor/data-collection/diagnostic-settings, requested at https://learn.microsoft.com/en-us/azure/azure-monitor/platform/diagnostic-settings | 22 September 2026 | 23 September 2026 |
| 4 | Microsoft Learn, *Azure resource logs supported services and schemas*, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/resource-logs-schema, requested at https://learn.microsoft.com/en-us/azure/azure-monitor/platform/resource-logs-schema | 22 September 2026 | 23 September 2026 |
| 5 | Microsoft Learn, *Monitor Azure OpenAI in Microsoft Foundry Models (classic)*, https://learn.microsoft.com/en-us/azure/foundry-classic/openai/how-to/monitor-openai (a classic page, used because source 2 links to it, as ruling 18 allows) | 12 May 2026 | 23 September 2026 |
| 6 | Microsoft Learn, *Activity Log in Azure Monitor*, https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/activity-log, requested at https://learn.microsoft.com/en-us/azure/azure-monitor/platform/activity-log | 22 September 2026 | 23 September 2026 |
| 7 | Microsoft Learn, *Azure Activity Log event schema*, https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/activity-log-schema, requested at https://learn.microsoft.com/en-us/azure/azure-monitor/platform/activity-log-schema | 22 September 2026 | 23 September 2026 |
| 8 | Microsoft Learn, *Agent tracing overview*, https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-agent-concept | 28 August 2026 | 23 September 2026 |
| 9 | Microsoft Learn, *Microsoft Foundry Tracing and Data Handling*, https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-data | 26 June 2026 | 23 September 2026 |
| 10 | Microsoft Learn, *Set Up Tracing for AI Agents in Microsoft Foundry*, https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/trace-agent-setup | 7 September 2026 | 23 September 2026 |
| 11 | Microsoft Learn, *Export hosted agent telemetry by using OpenTelemetry*, https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/configure-hosted-agent-telemetry | 13 August 2026 | 23 September 2026 |
| 12 | Microsoft Learn, *Quickstart: Trace your hosted agent*, https://learn.microsoft.com/en-us/azure/foundry/observability/quickstarts/quickstart-tracing-hosted-agent | 5 August 2026 | 23 September 2026 |
| 13 | Microsoft Learn, *Monitoring data reference for Foundry Agent Service (classic)*, https://learn.microsoft.com/en-us/azure/foundry-classic/agents/reference/monitor-service, requested at https://learn.microsoft.com/en-us/azure/ai-foundry/agents/reference/monitor-service (a classic page, used because the current address redirects to it, as ruling 18 allows) | 14 April 2026 | 23 September 2026 |
| 14 | Microsoft Learn, Foundry Tools, *Enable diagnostic logging*, https://learn.microsoft.com/en-us/azure/ai-services/diagnostic-logging (the page source 4 links as the schema for Foundry Tools; it carries no schema) | 5 June 2026 | 23 September 2026 |
| 15 | Amazon Bedrock User Guide, *Monitor model invocation using CloudWatch Logs and Amazon S3*, https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html | no date on the page | 23 September 2026 |
| 16 | Amazon Bedrock User Guide, *Per-request metadata tagging*, https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-request-metadata.html | no date on the page | 23 September 2026 |
| 17 | Amazon Bedrock API Reference, *Converse*, https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html | no date on the page | 23 September 2026 |
| 18 | Amazon Bedrock User Guide, *Monitor the bedrock-runtime endpoint*, https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring.html | no date on the page | 23 September 2026 |
| 19 | Amazon Bedrock User Guide, *Monitor the bedrock-mantle endpoint*, https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-mantle.html | no date on the page | 23 September 2026 |
| 20 | Amazon Bedrock User Guide, *Monitor Amazon Bedrock features*, https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-features.html | no date on the page | 23 September 2026 |
| 21 | Amazon Bedrock User Guide, *Monitor Amazon Bedrock API calls using CloudTrail*, https://docs.aws.amazon.com/bedrock/latest/userguide/logging-using-cloudtrail.html | no date on the page | 23 September 2026 |
| 22 | AWS CloudTrail User Guide, *CloudTrail record contents for management, data, and network activity events*, https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html | no date on the page | 23 September 2026 |
| 23 | Amazon Bedrock User Guide, *Monitor bedrock-runtime inference using CloudWatch metrics*, https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-runtime-metrics.html | no date on the page | 23 September 2026 |
| 24 | Amazon Bedrock User Guide, *Monitor knowledge bases using CloudWatch Logs*, https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-bases-logging.html | no date on the page | 23 September 2026 |
| 25 | Amazon Bedrock AgentCore Developer Guide, *Observe your agent applications on Amazon Bedrock AgentCore Observability*, https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html | no date on the page | 23 September 2026 |
| 26 | Amazon Bedrock AgentCore Developer Guide, *Amazon Bedrock AgentCore generated observability data*, https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-service-provided.html | no date on the page | 23 September 2026 |
| 27 | Amazon Bedrock AgentCore Developer Guide, *AgentCore generated runtime observability data*, https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-runtime-metrics.html | no date on the page | 23 September 2026 |
| 28 | Amazon Bedrock AgentCore Developer Guide, *Add observability to your Amazon Bedrock AgentCore resources*, https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html | no date on the page | 23 September 2026 |
<!-- /generated:sources -->

## 1. The surfaces

<!-- generated:surfaces -->
| Vendor | Layer | Surface | Switch | What it records |
|---|---|---|---|---|
| Azure | as shipped | Activity log and platform metrics | none; both are collected with no action [3] | Activity log entries for management operations performed through Resource Manager, and platform metrics as numeric series split by dimensions such as the model deployment and model name. Agent metrics, including tool calls split by tool name, are series too. [6][7][2][13] |
| Azure | model | Foundry resource logs through a diagnostic setting | create a diagnostic setting on the Foundry resource with the categories the how-to lists: Audit Logs, Request and Response Logs and Azure OpenAI Request Usage [1][3] | Records in the AzureDiagnostics table by category: Audit, AzureOpenAIRequestUsage, ManagedNetworkEvent, RequestResponse and Trace. Each carries the header fields common to all resource logs; anything specific to the service sits in properties, which no page read documents for these categories. [2][4][5][14] |
| Azure | agent | Foundry agent tracing for a hosted agent, in Application Insights | connect an Application Insights resource to the Foundry project [10][9] | A server-side trace for each agent invocation, from the hosting protocol runtime. Spans for model calls, tool calls and retrieval come from the agent's own code, instrumented out of the box only for Microsoft Agent Framework and LangChain. The lab uses the Claude Agent SDK, which is neither. [11][12][10] |
| AWS | as shipped | CloudTrail management events and CloudWatch runtime metrics | none; CloudTrail is on when the account is created and logs management events by default [21][23] | One CloudTrail management event per InvokeModel, InvokeModelWithResponseStream, Converse or ConverseStream call, and runtime metrics published under the AWS/Bedrock namespace, split by model identifier. [21][22][23] |
| AWS | model | Model invocation logging to CloudWatch Logs or Amazon S3 | enable model invocation logging with a destination, selecting the Text modality, which is the lab's only modality [15] | One ModelInvocationLog record per Converse, ConverseStream, InvokeModel or InvokeModelWithResponseStream call on the bedrock-runtime endpoint, with the request and response bodies inline up to 100 KB. Calls through the bedrock-mantle endpoint are not captured. Knowledge bases, Guardrails and Agents are monitored as features apart from the endpoint, and knowledge base logs cover ingestion jobs; none is assessed here. [15][18][19][20][24] |
| AWS | agent | AgentCore Observability for an agent hosted in AgentCore Runtime | enable observability on the agent resource, after the one-time CloudWatch Transaction Search setup for the account [27][28][26] | For each agent invocation, one InvokeAgentRuntime span and one APPLICATION_LOGS record, plus USAGE_LOGS records of resource consumption. Spans for the model calls, tool calls and retrieval inside the agent come only from instrumentation the deployment adds to its own code. Source 26 marks agent spans and logs as needing explicit enablement, while source 28 says the runtime creates a log group by default; both are recorded. [27][26][25][28] |
<!-- /generated:surfaces -->

Both plan-named surfaces are off as shipped: Azure resource logs "Aren't
collected by default" [3], and "Model invocation logging is disabled by
default" [15]; Foundry tracing is off too [9]. With no action, Azure collects
its activity log and platform metrics [3], and AWS its CloudTrail management
events and CloudWatch runtime metrics [21][23].

**Counts over the 37 fields**, and over the seven security-only fields:

<!-- generated:counts -->
| Surface | available by default | available with configuration | absent | unconfirmed | Security-only fields, in the same order |
|---|---|---|---|---|---|
| Activity log and platform metrics | 0 | 0 | 22 | 15 | 0, 0, 7, 0 |
| Foundry resource logs through a diagnostic setting | 1 | 0 | 21 | 15 | 0, 0, 7, 0 |
| Foundry agent tracing for a hosted agent, in Application Insights | 0 | 0 | 31 | 6 | 0, 0, 7, 0 |
| CloudTrail management events and CloudWatch runtime metrics | 3 | 0 | 22 | 12 | 0, 0, 7, 0 |
| Model invocation logging to CloudWatch Logs or Amazon S3 | 12 | 0 | 22 | 3 | 0, 0, 7, 0 |
| AgentCore Observability for an agent hosted in AgentCore Runtime | 4 | 0 | 33 | 0 | 0, 0, 7, 0 |
<!-- /generated:counts -->

Nothing is available with configuration on any surface. Every documented
setting is either a surface's own switch or a value the deployment would
supply. Bedrock lists its
log record's fields in full [15]; Azure documents only the header its resource
logs share [4][5], so most Azure verdicts are unconfirmed rather than absent.

## 2. Class by class, on vendor defaults only

For each column, the class's counted detector is re-run over its successful
trials and its benign denominator with everything the column lacks taken away:
fields nulled, unrecorded event types dropped, and ungrouped records run as
sessions of one. An input the pages do not settle is run both ways, and a class
whose answers differ reads `uc`. No model call is made and nothing under
`runs/` is written. What each detector lost, the combined model and agent
answer, and the view across every detector are in `results/vendor-gap.json`,
and `.venv/bin/python -m vendor_gap.analysis` prints the passes.

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

## 3. The fields a deployment has to add itself

In priority order, as ruled: first the fields whose addition returns a class to
its baseline, then every other field the headline column lacks, by tier and
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

## 4. Limitations

- **Nothing was observed.** Every verdict comes from documentation, so where a
  page is wrong or out of date, so is its verdict.
- **What stays unconfirmed.** Azure documents no properties for its resource log
  categories [2][4][5][14] or for a hosted agent's trace [11][12]. No page says
  whether Bedrock counts cached tokens [15] or shows a logged body's shape
  [15][16]; a tool call sits in the Converse response body [17], at no
  documented path in the log. CloudTrail does not list a Converse call's
  parameters [21][22]; no page says whether the activity log records a model
  call [6][7], or names a key linking either vendor's model and agent layers.
- **ASTP granularity.** A vendor record is modelled as the matching ASTP event,
  with the fields the vendor lacks nulled.
- **This agent only.** Foundry traces Microsoft Agent Framework and LangChain
  out of the box [12], and AgentCore records model and tool calls only from
  instrumentation the deployment adds [25][28].
- **Out of scope.** Bedrock Agents, knowledge bases and Guardrails [20][24],
  AgentCore Gateway and built-in tools [26], and either vendor's retrieval
  service.
- **Vendor controls are not ASTP controls.** The authorisation decision, a
  guardrail's reason and a canary's movement are held only by the lab.

## 5. Traps for anyone repeating the checks

- The product was renamed, and a "(classic)" documentation set sits beside the
  current one; some current pages link or redirect into it [5][13].
- Microsoft pages carry `ms.date` and `updated_at`, and only `updated_at`
  matches "Last updated". No AWS page carries a date.
- Source 4 links Foundry Tools' resource log schema to source 14, a how-to page
  with no schema.
- Bedrock invocation logging covers only `bedrock-runtime` [15][19].
- Search and fetch summaries paraphrase, and community answers are not
  documentation: read the page itself.
- A vendor saying it follows the OpenTelemetry GenAI conventions [8] is not a
  field list.

## Quotations

The constraints that decide a verdict or are ambiguous, exactly as each page
reads.

<!-- generated:quotes -->
- [3] *Aren't collected by default. Create a diagnostic setting to collect resource logs.*
- [3] *Automatically collected without configuration.*
- [1] *Select Audit Logs, Request and Response Logs, Azure OpenAI Request Usage, and AllMetrics.*
- [1] *The "Trace" option in diagnostic logging is only available for Custom question answering.*
- [1] *Run this query to measure request latency by response code*
- [5] *All resource logs in Azure Monitor have the same header fields, followed by service-specific fields.*
- [4] *Any extended properties related to this category of events.*
- [4] *A GUID that's used to group together a set of related events.*
- [6] *Azure Monitor records management operations for your Azure resources through the activity log feature.*
- [7] *Contains the record of all create, update, delete, and action operations performed through Resource Manager.*
- [7] *Set of <Key, Value> pairs (that is, a Dictionary) describing the details of the event.*
- [8] *The following table describes common OpenTelemetry GenAI conventions for multi-agent observability.*
- [9] *Tracing is off by default.*
- [10] *Foundry automatically logs server-side traces for Prompt agents, Host agents, and workflows in the Foundry portal.*
- [11] *Hosted agents generate telemetry from the protocol runtime (the Responses or Invocations server) and from your agent code.*
- [12] *out-of-the-box instrumentation for Microsoft Agent Framework and LangChain*
- [12] *Each invocation generates a complete trace.*
- [12] *Enable content recording by setting the environment variable OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true in your agent configuration.*
- [15] *Model invocation logging is disabled by default.*
- [15] *you can collect the full request data, response data, and metadata associated with supported calls*
- [15] *Each invocation log entry is a JSON object with the following structure.*
- [15] *Every field in the record is populated by Amazon Bedrock automatically, with one exception: requestMetadata is the only field supplied by the caller.*
- [15] *The type of log record. Always ModelInvocationLog.*
- [15] *The request body sent to the model (up to 100 KB).*
- [15] *Select the modalities of the data requests and responses that you want to publish to the logs.*
- [15] *Model invocation logging is only supported for calls made through the bedrock-runtime endpoint.*
- [15] *The number of input tokens in the request.*
- [15] *The AWS STS or IAM ARN of the principal that made the request, including the role name and the session or user name.*
- [16] *Use higher-cardinality values such as session or trace identifiers only when you need to trace individual calls.*
- [16] *Request metadata is supplied per call and is not enforced by Amazon Bedrock.*
- [21] *CloudTrail is enabled on your AWS account when you create the account.*
- [21] *CloudTrail logs management event API operations by default.*
- [21] *Data events are often high-volume activities that CloudTrail doesn’t log by default.*
- [22] *The parameters, if any, that were sent with the request.*
- [22] *The response elements, if any, for actions that make changes (create, update, or delete actions).*
- [24] *Amazon Bedrock supports a monitoring system to help you understand the execution of any data ingestion jobs for your knowledge bases.*
- [25] *You can also instrument your agent code to provide additional span and trace data and custom metrics and logs.*
- [26] *Signals marked with an asterisk require explicit enablement.*
- [27] *The following table defines the operation for which spans are created and the attributes for each captured span.*
- [27] *To enable this span data, you need to enable observability on your agent resource.*
- [27] *request_payload - the request payload of the agent invocation*
- [28] *When you create an AgentCore runtime resource (agent), by default, AgentCore runtime creates a CloudWatch log group for the service-provided logs.*
- [28] *you first need to complete a one-time setup to turn on Amazon CloudWatch Transaction Search*
<!-- /generated:quotes -->
