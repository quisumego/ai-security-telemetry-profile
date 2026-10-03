# Microsoft Sentinel mapping

**Stage:** M6, Volume and Sentinel

**Purpose:** How ASTP events would land in Microsoft Sentinel: one table, one
Data Collection Rule and one query per detector, each checked against the
platform's published limits. For anyone deploying the profile on Sentinel.

---

## 1. What was built

**Documented, not deployed.** No Azure resource was created, no request was
sent to Azure and no Azure spend was incurred.

`siem/sentinel.py` generates three artefacts from the field register and
writes them to `siem/sentinel/`. `tests/test_sentinel_mapping.py` holds each
file, and the blocks on this page between `generated` markers, to what the
generator produces now.

| Artefact | File | Design | Constraint it meets |
|---|---|---|---|
| Custom table `AstpEvents_CL`, Analytics plan | `astp-table.json` | The register's names in PascalCase, prefixed with the group | A custom table's name ends `_CL` [1]; alerts run on Analytics tables [11]; a table created through a rule can take any plan [12]; the analytics tier keeps data interactive for 90 days by default [13]; the prefix keeps `session.id` and `session.tenant_id` off the reserved names `id` and `TenantId` [1][10] |
| Data Collection Rule, `Direct`, stream `Custom-AstpEvents` | `astp-dcr.json` | A transformation that flattens the six groups into columns, one record at a time | A rule for the Logs Ingestion API [5][10]; supported functions only [3]; with Sentinel enabled, a transformation into an Analytics table is not charged [14]; a call carries at most 1 MB and a value over 64 KB is truncated [4]; column entries the table cannot store are still billed [2] |
| One rule query per detector | `rules/d-a0N.kql` | Each reads the deployment's permitted destinations and document inventory from watchlists | A scheduled analytics rule [6]; watchlists [7] |

**`TimeGenerated` is ingestion time.** A `session_end` event carries no event
time of its own; the gap is listed in [`SPEC.md` Section 9](../SPEC.md#9-limitations).

**A content posture belongs at the source.** The transformation could apply
one [3], but `control.canary_triggered` is computed from the full text, so
hashing or cutting must happen after it, in the agent.

The generated artefacts against their limits:

<!-- generated:figures -->
42 columns against a limit of 500 [4]. The transformation is 2,683 characters against a limit of 15,360 [4]. The longest rule query is 815 characters against a limit of 10,000 [6].
<!-- /generated:figures -->

## 2. Which rules translate

Six of the seven queries translate, one of them with a caveat; `d-a04`
translates only in part. The Sigma rules in `detect/sigma/` state intent; the
Python in `detect/detectors.py` scored every figure, and the queries follow it.
Four rules group events by session, so a session that straddles a rule's
lookback is seen in part [6].

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

**Never run.** No query has been executed: nothing is deployed, and there is
no workspace to run one in. Treat each query as a specification to test.

## 3. Price

No price is attached to any figure, because the price depends on choices this
project does not make. Ingestion is billed per GB of 10^9 bytes from the column
entries written, with no published per-type formula, and Sentinel's charges
apply alongside [2]. The Sentinel pricing page gives no per-GB figure [8].

To price a deployment:

1. Read a per-GB price from the Azure Retail Prices API [9].
2. Record the meter, region, currency and date with it.
3. Multiply a GB-a-day figure in `results/volume.md` by it.

## 4. What is still open

Five things this mapping could not settle:

- whether any of it works, because none of it has run;
- how an absent stream property is treated;
- the billed size of an ASTP record;
- which task a session runs, which `d-a04` needs;
- an event time for `session_end`.

After 31 March 2027 Sentinel is available only in the Microsoft Defender
portal [6][13].

---

## Sources

Each page was read on the date given. "Page updated" is the `updated_at` value
the page carried when read. Nothing on this page is from memory.

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

**Sources:** the fourteen Microsoft pages above, cited by number; the artefacts in `siem/sentinel/`; `tests/test_sentinel_mapping.py`.
