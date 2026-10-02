# Microsoft Sentinel mapping

> **Documented, not deployed.** No Azure resource was created, no request was
> sent to Azure and no Azure spend was incurred.

Written at M6, 23 September 2026, and condensed on 2 October 2026.
`siem/sentinel.py` generates, from the field register, a custom table, a Data
Collection Rule and one KQL query per detector, and writes them to
`siem/sentinel/`: `astp-table.json`, `astp-dcr.json` and `rules/d-a0N.kql`.
`tests/test_sentinel_mapping.py` holds each file, and the blocks on this page
between `generated` markers, to what the generator produces now, and checks
them against the constraints below.

## Sources

Every claim below about Microsoft Sentinel, Azure Monitor Logs, Data Collection
Rules or their limits carries a number from this table. Each page was read on
the date given. "Page updated" is the `updated_at` value the page carried when
it was read. Nothing below is from memory.

| # | Source | Page updated | Retrieved |
|---|---|---|---|
| 1 | Microsoft Learn, *Add or delete tables and columns in Azure Monitor Logs*, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/create-custom-table | 4 September 2026 | 22 September 2026 |
| 2 | Microsoft Learn, *Azure Monitor Logs cost calculations and options*, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/cost-logs | 21 September 2026 | 22 September 2026 |
| 3 | Microsoft Learn, *Supported KQL features in Azure Monitor transformations*, https://learn.microsoft.com/en-us/azure/azure-monitor/data-collection/data-collection-transformations-kql | 28 July 2026 | 22 September 2026 |
| 4 | Microsoft Learn, *Azure Monitor service limits*, https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/service-limits | 19 January 2026 | 22 September 2026 |
| 5 | Microsoft Learn, *Structure of a data collection rule (DCR) in Azure Monitor*, https://learn.microsoft.com/en-us/azure/azure-monitor/data-collection/data-collection-rule-structure | 3 June 2026 | 22 September 2026 |
| 6 | Microsoft Learn, *Scheduled analytics rules in Microsoft Sentinel*, https://learn.microsoft.com/en-us/azure/sentinel/scheduled-rules-overview | 17 July 2026 | 22 September 2026 |
| 7 | Microsoft Learn, *Use watchlists to correlate and enrich event data in Microsoft Sentinel*, https://learn.microsoft.com/en-us/azure/sentinel/watchlists | 23 June 2026 | 23 September 2026 |
| 8 | Microsoft, *Microsoft Sentinel pricing*, https://azure.microsoft.com/en-gb/pricing/details/microsoft-sentinel/, which redirects to https://www.microsoft.com/en-gb/security/pricing/microsoft-sentinel/ | no date on the page | 22 September 2026 |
| 9 | Microsoft, *Azure Retail Prices API*, https://prices.azure.com/api/retail/prices | live data | 22 September 2026 |
| 10 | Microsoft Learn, *Logs Ingestion API in Azure Monitor*, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/logs-ingestion-api-overview | 23 September 2026 | 23 September 2026 |
| 11 | Microsoft Learn, *Azure Monitor Logs*, table plans section, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-platform-logs | 21 September 2026 | 23 September 2026 |
| 12 | Microsoft Learn, *Configure a table plan in a Log Analytics workspace*, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/logs-table-plans | 21 September 2026 | 23 September 2026 |
| 13 | Microsoft Learn, *Log retention tiers in Microsoft Sentinel*, https://learn.microsoft.com/en-us/azure/sentinel/log-plans | 14 May 2026 | 23 September 2026 |
| 14 | Microsoft Learn, *Transformations in Azure Monitor*, https://learn.microsoft.com/en-us/azure/azure-monitor/data-collection/data-collection-transformations | 22 September 2026 | 23 September 2026 |
## 1. What was built

- **The table**, `AstpEvents_CL`, on the Analytics plan. A custom table's name
  ends `_CL` [1]; alerts run on Analytics tables [11]; a table created through a
  rule can take any plan [12]; and Sentinel's analytics tier keeps data
  interactive for 90 days by default [13]. Columns are the register's names in
  PascalCase with the group as a prefix, which keeps `session.id` and
  `session.tenant_id` off the reserved names `id` and `TenantId` [1][10].
  `TimeGenerated` is ingestion time, because a `session_end` event carries no
  event time of its own; the gap is listed in `SPEC.md` Section 9.
- **The Data Collection Rule**, a `Direct` rule for the Logs Ingestion API with
  the stream `Custom-AstpEvents` [5][10]. Its transformation flattens the six
  groups into columns one record at a time, with supported functions only [3].
  A content posture could be applied there [3], but it belongs at the source,
  where `control.canary_triggered` is computed from the full text. With
  Sentinel enabled, a transformation into an Analytics table is not charged
  [14]. A call carries at most 1 MB, a value over 64 KB is truncated [4], and
  column entries the table cannot store are still billed [2].
- **The rule queries**, one per detector, each a scheduled rule [6] that reads
  the deployment's permitted destinations and document inventory from
  watchlists [7].

<!-- generated:figures -->
42 columns against a limit of 500 [4]. The transformation is 2,683 characters against a limit of 15,360 [4]. The longest rule query is 815 characters against a limit of 10,000 [6].
<!-- /generated:figures -->

## 2. Which rules translate

The Sigma rules in `detect/sigma/` state intent; the Python in
`detect/detectors.py` scored every figure, and the queries follow it. Four
rules group events by session, so a session that straddles a rule's lookback is
seen in part [6].

<!-- generated:rules -->
| Detector | Translates | Why |
|---|---|---|
| `d-a01` | yes | single event; the permitted destinations become two watchlists |
| `d-a02` | yes | session-scoped; the Python that scored has no ordering, so neither has this |
| `d-a03` | yes | session-scoped; the Python that scored has no ordering, so neither has this |
| `d-a04` | partly | no field names the task a session runs, so the rule is scoped by client application, which is an assumption about the deployment |
| `d-a06` | yes | single event; the document inventory becomes a watchlist |
| `d-a07` | yes, with a caveat | session-scoped and reasons from absence, so a session that straddles the lookback window can fire on half a session |
| `d-a08` | yes | session-scoped count; circular, as the Sigma rule states, because the thresholds are the A8 oracle's |
<!-- /generated:rules -->

**Never run.** No query has been executed: nothing is deployed, and there is no
workspace to run one in. Treat each as a specification to test.

## 3. Price

No price is attached to any figure, as ruled, because the price depends on
choices this project does not make. Ingestion is billed per GB of 10^9 bytes
from the column entries written, with no published per-type formula, and
Sentinel's charges apply alongside [2]. The Sentinel pricing page gives no
per-GB figure [8]: take one from the Azure Retail Prices API [9], recording the
meter, region, currency and date, and multiply a GB-a-day figure in
`results/volume.md` by it.

## 4. What this mapping could not settle

None of it has run; how an absent stream property is treated; the billed size
of an ASTP record; which task a session runs, which `d-a04` needs; and an event
time for `session_end`. After 31 March 2027 Sentinel is available only in the
Microsoft Defender portal [6][13].
