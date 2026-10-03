# Attack class references

**Stage:** M0, Rules and schema

**Purpose:** The external identifiers each of the ten attack classes carries,
each verified against a live source with its date. For anyone checking a
mapping; the scenarios cite these rather than derive their own.

---

## 1. The ten attack classes

Each class carries an OWASP identifier and, where one exists, a MITRE ATLAS
technique.

| # | Class | OWASP | MITRE ATLAS |
|---|---|---|---|
| A1 | Direct prompt injection | LLM01:2025 | `AML.T0051.000` LLM Prompt Injection: Direct |
| A2 | Indirect prompt injection via a retrieved document | LLM01:2025 | `AML.T0051.001` LLM Prompt Injection: Indirect; `AML.T0066` Retrieval Content Crafting |
| A3 | Sensitive information disclosure | LLM02:2025 | `AML.T0057` LLM Data Leakage |
| A4 | Excessive agency, tool misuse | LLM06:2025 | `AML.T0053` AI Agent Tool Invocation |
| A5 | Improper output handling | LLM05:2025 | `AML.T0077` LLM Response Rendering |
| A6 | Retrieval corpus poisoning | LLM04:2025 | `AML.T0070` RAG Poisoning; `AML.T0071` False RAG Entry Injection |
| A7 | System prompt leakage | LLM07:2025 | `AML.T0056` Extract LLM System Prompt; `AML.T0069.002` Discover LLM System Information: System Prompt |
| A8 | Unbounded consumption | LLM10:2025 | `AML.T0034.002` Cost Harvesting: Agentic Resource Consumption; `AML.T0029` Denial of AI Service |
| A9 | Cross-tenant retrieval | LLM08:2025 | **No clean identifier. See Section 2.** |
| A10 | Staged exfiltration chain | LLM01:2025 into LLM06:2025 | `AML.T0051.001` LLM Prompt Injection: Indirect, then `AML.T0086` Exfiltration via AI Agent Tool Invocation |

Two of the ten have no exact ATLAS match, and Section 2 says why.

## 2. Where no clean identifier exists

**A9, cross-tenant retrieval, carries no ATLAS identifier.** ATLAS v2026.07 has
no technique for crossing a tenant boundary in retrieval. The nearest,
`AML.T0085.000` Data from AI Services: RAG Databases, covers collecting data
from a retrieval database but not crossing an access boundary between tenants.
Recording it as an approximate match would misstate ATLAS, so A9 carries its
OWASP mapping only: LLM08:2025 Vector and Embedding Weaknesses, which does cover
cross-tenant leakage in retrieval systems.

**A5, improper output handling, is a close match, not an exact one.**
`AML.T0077` LLM Response Rendering matches the rendering half of the class.
ATLAS frames it as a rendering technique rather than as the downstream
injection consequence OWASP LLM05 describes. `AML.T0067` LLM Trusted Output
Components Manipulation is adjacent and is not claimed.

## 3. The OWASP list

| ID | Title |
|---|---|
| LLM01:2025 | Prompt Injection |
| LLM02:2025 | Sensitive Information Disclosure |
| LLM03:2025 | Supply Chain |
| LLM04:2025 | Data and Model Poisoning |
| LLM05:2025 | Improper Output Handling |
| LLM06:2025 | Excessive Agency |
| LLM07:2025 | System Prompt Leakage |
| LLM08:2025 | Vector and Embedding Weaknesses |
| LLM09:2025 | Misinformation |
| LLM10:2025 | Unbounded Consumption |

**Eight of the ten are the profile's spine.** LLM03 (Supply Chain) and LLM09
(Misinformation) are out of scope: neither is a runtime detection problem a
logging profile addresses.

## 4. Verification at M0

| Source | Version verified | Retrieved |
|---|---|---|
| OWASP Top 10 for LLM Applications | 2025 list, `genai.owasp.org` | 12 August 2026 |
| MITRE ATLAS | Data version `2026.07`, format version 6.0.0, collection modified 27 May 2026 | 12 August 2026 |

The ATLAS identifiers were read from `dist/v6/ATLAS-2026.07.yaml` in the
`mitre-atlas/atlas-data` repository, at release `v2026.07` published 7 August
2026. That file holds 101 techniques and 77 sub-techniques, which matches the
repository changelog for that version.

**Read `dist/v6/`, not `dist/ATLAS.yaml`.** The file at `dist/ATLAS.yaml`
declares itself deprecated and is not the current data.

## 5. Re-checked 1 October 2026

Re-checked at M8 by the method in
[`docs/framework-references.md`](framework-references.md). The tables above
stay as recorded at M0.

| Source | Read, times UTC | Result |
|---|---|---|
| OWASP Top 10 for LLM Applications | `genai.owasp.org/llm-top-10/`, 21:26 | Unchanged. All ten 2025 identifiers carry the titles above, and no later list is published |
| MITRE ATLAS | `mitre-atlas/atlas-data`, `dist/v6/ATLAS-2026.07.yaml` and `dist/v6/ATLAS-2026.09.yaml`, 21:26 | The latest release is `v2026.09`, published 15 September 2026, with 120 techniques and 88 sub-techniques. Every identifier cited above is present in it under the same name. **A9 still has no clean identifier**: three of the techniques new in 2026.09 mention a tenant, and they cover reconnaissance of hosted resources and account creation, not crossing a tenant boundary in retrieval. The mapping above stays pinned to data version 2026.07 |

**Citing an identifier is not reproducing a standard.** This page gives
identifiers and titles only, and no text from OWASP, MITRE, DSIT, NCSC or ETSI
is reproduced anywhere in this repository.

---

**Sources:** OWASP Top 10 for LLM Applications 2025, `genai.owasp.org`; MITRE ATLAS, `mitre-atlas/atlas-data`, `dist/v6/`.
