# Framework references

**Stage:** M0, Rules and schema

**Purpose:** The three frameworks the profile maps to, each verified against
its live published document, with the relevant provisions' intent paraphrased.
No text is reproduced from any of them.

---

## 1. The three frameworks

Each asks for logging and monitoring; none says which fields a log needs.
That gap is what this profile measures.

| Framework | Publisher | Published | Relevant part |
|---|---|---|---|
| DSIT Code of Practice for the Cyber Security of AI | Department for Science, Innovation and Technology | 31 January 2025 | Principle 12, "Monitor your system's behaviour" |
| NCSC Guidelines for Secure AI System Development | National Cyber Security Centre, with CISA and international partners | 27 November 2023 | Section 4, "Secure operation and maintenance" |
| ETSI TS 104 223, V1.1.1 | ETSI | April 2025 | Clause 5.4.2, Principle 12, "Monitor the system's behaviour" |

Every identifier was verified on **12 August 2026**, and re-checked on 1 October
2026 (Section 6).

## 2. DSIT Code of Practice

| Item | Value |
|---|---|
| Structure | 13 principles |
| Relevant principle | **Principle 12, "Monitor your system's behaviour"** |

**Principle 12 is the anchor for this profile.** Its intent, in paraphrase:
operators should keep logs of system and user actions so that security
compliance can be shown and incidents investigated, analyse those logs for
anomalies and unexpected behaviour, and watch internal system state and model
performance for changes over time. The Code states the requirement; it does
not say which fields carry detection signal for which attack classes.

## 3. NCSC Guidelines

| Item | Value |
|---|---|
| Structure | Four lifecycle sections |
| Relevant section | **Section 4, "Secure operation and maintenance"** |

Section 4 holds four guidelines:

- Monitor your system's behaviour
- Monitor your system's inputs
- Follow a secure by design approach to updates
- Collect and share lessons learned

**The first two bear on this profile.** In paraphrase, the first asks operators
to measure model and system outputs, so that sudden or gradual changes
affecting security can be seen and intrusions told apart from natural drift.
The second asks that inputs, inference requests and prompts among them, are
monitored and logged so that audit, investigation and remediation are possible
after a compromise or misuse, subject to privacy and data protection. That
qualification is the tension the retention posture in
[`docs/methodology.md`](methodology.md) Section 8 addresses.

## 4. ETSI TS 104 223

| Item | Value |
|---|---|
| Full title | Securing Artificial Intelligence (SAI); Baseline Cyber Security Requirements for AI Models and Systems |
| Identifier | ETSI TS 104 223 |
| Version | V1.1.1 |
| Published | April 2025 |
| Work item reference | DTS/SAI-0014 |
| Structure | 13 principles across 5 lifecycle phases, expressed as numbered provisions |
| Relevant clause | **5.4.2, Principle 12, "Monitor the system's behaviour"**, under 5.4 Secure Maintenance |

Clause 5.4.2 carries four provisions. Their intent, in paraphrase:

| Provision | Intent, paraphrased | Obligation |
|---|---|---|
| `5.4.2-1` | Operators log system and user actions to support security compliance, incident investigation and vulnerability remediation | shall |
| `5.4.2-2` | Operators analyse those logs to confirm models still behave as intended and to find anomalies, breaches or drift over time | should |
| `5.4.2-3` | Operators and developers monitor internal system state where this helps address threats or supports later security analytics | should |
| `5.4.2-4` | Operators and developers monitor model and system performance over time to catch behaviour changes affecting security | should |

**`5.4.2-1` is the provision this profile answers most directly.** It is the
only firm obligation of the four, and it requires logging of system and user
actions without saying what the records contain.

**Cite ETSI TS 104 223 and the DSIT Code together, not as independent
corroboration.** They share the principle number and very nearly the title for
monitoring.

**ETSI EN 304 223 is not mapped.** The follow-on European Standard builds on
this Technical Specification; the mapping in `SPEC.md` is written against
TS 104 223.

## 5. How the mapping is used

**The claim is narrow.** These documents require that logging and monitoring
happen; this profile is evidence about which fields make that logging useful
for detection. [`SPEC.md`](../SPEC.md#8-framework-mapping) Section 8 states,
for each framework, the provision the profile helps satisfy. Nothing in this
repository certifies compliance with any of them.

## 6. Re-checked 1 October 2026

Every identifier cited in public text was re-checked against its live source at
M8, with the new date recorded beside the original. Any difference is reported
here, and the values above stay as recorded at M0.

| Framework | Source read, times UTC | Result |
|---|---|---|
| DSIT Code of Practice | The GOV.UK content API for the publication and for the Code itself, 21:27 | Unchanged. First published and last updated 31 January 2025. Thirteen principles, and Principle 12 carries the title recorded above |
| NCSC Guidelines | `ncsc.gov.uk`, the collection page and its Section 4 page, 21:27 | Version 1.0, published and reviewed 27 November 2023. Section 4 and three of its four guideline titles read as recorded. **One difference:** the live page titles the second guideline "Monitor your system's input", singular, where the list above records "inputs". `SPEC.md` cites the live title |
| ETSI TS 104 223 | ETSI's publication directory and the V1.1.1 PDF, 21:28 | Unchanged. V1.1.1 (2025-04, DTS/SAI-0014) is still the only published version. Clause 5.4.2, under 5.4 Secure Maintenance, carries the four provisions recorded above: `5.4.2-1` a firm obligation and the other three recommendations. ETSI EN 304 223 has a published V2.1.1, dated December 2025, and it is still not mapped |

---

**Sources:** the DSIT Code of Practice on GOV.UK; the NCSC Guidelines on `ncsc.gov.uk`; ETSI TS 104 223 V1.1.1 from ETSI's publication directory.
