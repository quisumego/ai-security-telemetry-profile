# AI Security Telemetry Profile (ASTP)

> **Status: skeleton. Written at M8.**
>
> This document is the deliverable. It is not written yet, because most of it
> reports measurements that do not exist. The section headings below are fixed
> now so that the shape of the argument is settled before the results arrive,
> and so no section is quietly dropped because it turned out inconvenient.
>
> Nothing in this file may state a figure that does not trace to a committed
> result file.

## 1. Scope and threat model in brief

*To be written at M8.* What the profile covers, what it does not, and the threat
model the ten attack classes represent. Out of scope is stated as plainly as in
scope.

## 2. The event model

*To be written at M8.* The six field groups, where events are emitted from, and
the JSON Lines shape. Draws on `schema/event.schema.json`.

## 3. The field register

*To be written at M8.* Every field with name, group, type, tier, OpenTelemetry
mapping, security rationale, and **the ablation evidence for its tier**. Each
tier must be traceable to a specific cell in the necessity matrix. A field whose
tier cannot be traced to a cell does not get a tier.

Source: `schema/fields.yaml` after tiers are assigned at M5.

## 4. The tiering rule

*Filled at M8, verbatim from `docs/methodology.md`, with the date it was
committed and the commit hash.* The rule is quoted as committed, not restated.

## 5. Retention guidance by tier

*To be written at M8.* Expands the posture in `docs/methodology.md` Section 8
into per-tier guidance, with the measured detection cost of hashing or
truncating rather than retaining full content.

## 6. Volume and cost model

*To be written at M6 and M8.* Bytes per event by field group, measured from
captured logs rather than estimated, and daily ingest projected at one thousand
and ten thousand users.

## 7. SIEM mapping

*To be written at M6.* Sigma rules and a Microsoft Sentinel custom table schema
with a Data Collection Rule shape. Documented, not deployed.

## 8. Framework mapping

*To be written at M8.* DSIT Code of Practice Principle 12, the NCSC secure
operation and maintenance guidelines, and ETSI TS 104 223 clause 5.4.2.
Identifiers cited, intent paraphrased in original wording, no text reproduced.

Verified identifiers and retrieval dates are already recorded in
`docs/framework-references.md`.

## 9. Limitations

*To be written at M8, drawing on `docs/methodology.md` Section 7.* Circularity,
a small denominator, one model, one agent, a synthetic corpus, and a single
author. Written to survive a sceptical read, because a reader will find these
whether or not they are stated.
