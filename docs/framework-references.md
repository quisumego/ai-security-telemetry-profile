# Framework references, verified

The three frameworks this profile maps to. Every identifier below was verified
against the live published document at M0, on **12 August 2026**. Nothing here
was cited from memory.

**Identifiers and paraphrased intent only.** No text is reproduced from any of
these documents. Where intent is described, the wording is original.

---

## DSIT Code of Practice for the Cyber Security of AI

| Item | Value |
|---|---|
| Publisher | Department for Science, Innovation and Technology |
| Published | 31 January 2025 |
| Structure | 13 principles |
| Relevant principle | **Principle 12, "Monitor your system's behaviour"** |

Principle 12 is the anchor for this profile. Its intent, in paraphrase: system
operators should keep logs of system and user actions so that security
compliance can be demonstrated and incidents can be investigated, should analyse
those logs to find anomalies and unexpected behaviour, and should watch internal
system state and model performance for changes over time.

The Code states the requirement. It does not say which fields carry detection
signal for which attack classes. That gap is what this profile measures.

---

## NCSC Guidelines for Secure AI System Development

| Item | Value |
|---|---|
| Publisher | National Cyber Security Centre, with CISA and international partners |
| Published | 27 November 2023 |
| Structure | Four lifecycle sections |
| Relevant section | **Section 4, "Secure operation and maintenance"** |

Section 4 contains four guidelines. Their titles are:

- Monitor your system's behaviour
- Monitor your system's inputs
- Follow a secure by design approach to updates
- Collect and share lessons learned

The first two are the ones this profile bears on. Paraphrasing their intent: the
first asks operators to measure model and system outputs so that sudden or
gradual changes affecting security can be observed, and intrusions told apart
from natural drift. The second asks that inputs, including inference requests
and prompts, are monitored and logged so that audit, investigation and
remediation are possible after a compromise or misuse, subject to privacy and
data protection requirements.

The second guideline is worth noting for this profile specifically, because it
places input logging under an explicit data protection qualification. That is
the same tension the retention posture in `methodology.md` Section 8 addresses.

---

## ETSI TS 104 223

| Item | Value |
|---|---|
| Full title | Securing Artificial Intelligence (SAI); Baseline Cyber Security Requirements for AI Models and Systems |
| Identifier | ETSI TS 104 223 |
| Version | V1.1.1 |
| Published | April 2025 |
| Work item reference | DTS/SAI-0014 |
| Structure | 13 principles across 5 lifecycle phases, expressed as numbered provisions |
| Relevant clause | **5.4.2, Principle 12, "Monitor the system's behaviour"**, under 5.4 Secure Maintenance |

Clause 5.4.2 carries four provisions, `5.4.2-1` through `5.4.2-4`. Paraphrasing
their intent:

| Provision | Intent, paraphrased | Obligation |
|---|---|---|
| `5.4.2-1` | Operators log system and user actions to support security compliance, incident investigation and vulnerability remediation | shall |
| `5.4.2-2` | Operators analyse those logs to confirm models still behave as intended and to find anomalies, breaches or drift over time | should |
| `5.4.2-3` | Operators and developers monitor internal system state where this helps address threats or supports later security analytics | should |
| `5.4.2-4` | Operators and developers monitor model and system performance over time to catch behaviour changes affecting security | should |

`5.4.2-1` is the only one of the four expressed as a firm obligation, and it is
the provision this profile is most directly an answer to: it requires logging of
system and user actions without specifying what those log records contain.

Note that ETSI TS 104 223 and the DSIT Code of Practice share both the principle
number and very nearly the principle title for monitoring. They are closely
related documents and should be cited together rather than as independent
corroboration.

A follow-on European Standard, ETSI EN 304 223, builds on this Technical
Specification. It is recorded here for completeness and is not mapped, because
the mapping in `SPEC.md` is written against TS 104 223.

---

## How the mapping is used

`SPEC.md` Section 8 states, for each of the three frameworks, which provision the
profile helps satisfy and how. The claim made is narrow and deliberately so:
these documents require that logging and monitoring happen. This profile is
evidence about **which fields** make that logging useful for detection. It does
not certify compliance with any of them, and no part of this repository should
be read as doing so.

---

## Re-checked 1 October 2026

Ruled at M8: every identifier cited in public text is re-checked against its
live source before `SPEC.md` is written, with the new date recorded beside the
original and any difference reported beside the value above, which is left as
recorded at M0.

| Framework | Source read, times UTC | Result |
|---|---|---|
| DSIT Code of Practice | The GOV.UK content API for the publication and for the Code itself, 21:27 | Unchanged. First published and last updated 31 January 2025. Thirteen principles, and Principle 12 carries the title recorded above |
| NCSC Guidelines | `ncsc.gov.uk`, the collection page and its Section 4 page, 21:27 | Version 1.0, published and reviewed 27 November 2023. Section 4 and three of its four guideline titles read as recorded. **One difference:** the live page titles the second guideline "Monitor your system's input", singular, where the list above records "inputs". `SPEC.md` cites the live title |
| ETSI TS 104 223 | ETSI's publication directory and the V1.1.1 PDF, 21:28 | Unchanged. V1.1.1 (2025-04, DTS/SAI-0014) is still the only published version. Clause 5.4.2, under 5.4 Secure Maintenance, carries the four provisions recorded above: `5.4.2-1` a firm obligation and the other three recommendations. ETSI EN 304 223 now has a published V2.1.1, and it is still not mapped |
