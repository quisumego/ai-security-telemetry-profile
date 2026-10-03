# Vendor surfaces

**Stage:** M7, Vendor gap

**Purpose:** The six vendor surfaces assessed, the switch each needs, and how
many of the profile's fields each would carry. Part of the
[vendor gap analysis](../vendor-gap-analysis.md).

---

## 1. The surfaces

Each vendor has three: what it collects as shipped, the model layer the plan
names, and one agent layer.

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

**Both plan-named surfaces are off as shipped.** Azure resource logs "Aren't
collected by default" [3], and "Model invocation logging is disabled by
default" [15]; Foundry tracing is off too [9]. With no action, Azure collects
its activity log and platform metrics [3], and AWS its CloudTrail management
events and CloudWatch runtime metrics [21][23].

## 2. Counts over the fields

Counts over the 37 fields, and over the seven security-only fields:

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
supply. Bedrock lists its log record's fields in full [15]; Azure documents
only the header its resource logs share [4][5], so most Azure verdicts are
unconfirmed rather than absent.

---

**Sources:** numbered as in [Sources](sources.md).
