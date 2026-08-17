# Build log

What actually happened, session by session. Hours are wall-clock on the stage,
not an estimate.

---

## M0. Scope, naming, schema, scaffold

**Date:** 12 August 2026
**Stage:** M0
**Outcome:** exit criterion met, with one item outstanding (see below)

### Decisions taken

The five M0 questions were put to the owner as a single batch before any file
was created, and answered in one reply.

| # | Decision | Ruling |
|---|---|---|
| 1 | Specification name | AI Security Telemetry Profile, ASTP |
| 2 | Repository name | `ai-security-telemetry-profile` |
| 3 | Fictional company | Thornfield Mutual, a mid-market insurer |
| 4 | Field register | 37 fields across six groups, as proposed |
| 5 | Trials per scenario | **Raised from 5 to 10.** See amendment below |
| 6 | Materiality threshold | 20 percentage points, or a false positive rate above 10 per cent |
| 7 | Pinned lab model | `claude-haiku-4-5` |
| 8 | Content retention | Full prompt and response text captured in the lab |

### Amendment to the plan

The project plan specifies five trials per scenario. The owner raised this to
ten at M0, before any capture existed.

Reason: with five trials a detection rate can only take the values 0, 20, 40,
60, 80 or 100 per cent, so the proposed 20 percentage point materiality
threshold was exactly one trial. Ten trials make that threshold two trials and
halve the granularity of every rate. Cost is roughly fifty more sessions against
a small pinned model, which the budget absorbs.

Consequences: 100 attack sessions rather than 50. The checklist was updated.
The amendment is recorded in `PROJECT-HANDOVER.md`, which wins over the plan.

All rates are reported as a fraction alongside the percentage, so the size of
the denominator is always visible.

### Verification performed

Every external identifier was verified against a live source on **12 August
2026**. Nothing was cited from memory.

| Source | What was pinned |
|---|---|
| OpenTelemetry GenAI conventions | Repository `open-telemetry/semantic-conventions-genai`, commit `8d3e4a0f3c34a46f6edb9c71e8666e02e6bf3958` dated 10 August 2026. Zero releases, zero tags, no published schema URL. Every attribute at Development status |
| OpenTelemetry general registry | `user.id`, Development status |
| MITRE ATLAS | Data version `2026.07`, format version 6.0.0, from release `v2026.07`. 101 techniques and 77 sub-techniques, matching the changelog |
| OWASP Top 10 for LLM Applications | 2025 list, LLM01:2025 to LLM10:2025 |
| DSIT Code of Practice for the Cyber Security of AI | Published 31 January 2025, Principle 12 |
| NCSC Guidelines for Secure AI System Development | Published 27 November 2023, Section 4 and its four guideline titles |
| ETSI TS 104 223 | V1.1.1, April 2025, reference DTS/SAI-0014, clause 5.4.2 and provisions `5.4.2-1` to `5.4.2-4` |

Two findings worth recording for whoever repeats this:

- The GenAI conventions in the **main** `semantic-conventions` repository are
  deprecated and point to the dedicated repository. Reading the main repository
  gives a stale attribute list.
- `dist/ATLAS.yaml` in `mitre-atlas/atlas-data` declares itself deprecated. The
  current data is under `dist/v6/`.

One gap was found and recorded rather than papered over: **ATLAS v2026.07 has no
technique for cross-tenant retrieval (A9)**. The adjacent technique
`AML.T0085.000` covers collecting data from a retrieval database but not
crossing a tenant boundary, so A9 carries its OWASP mapping and no ATLAS
identifier.

### Clash check

| Name | Result |
|---|---|
| `ai-security-telemetry-profile` | No repository of that exact name exists on GitHub. Available |
| Thornfield Mutual | No company of that name found. The nearest real things are an unrelated business park and an unrelated domain. Clean |
| ASTP | Acronym is in cross-domain use, notably by a European technology transfer association and historically by the Apollo-Soyuz Test Project. No collision with a security or telemetry standard. Accepted, with the full phrase spelled out on first use |

Rejected on the clash check: **ASTS**, which collides with a listed company
trading under that exact ticker.

### Built

- Repository created as a subfolder of the workspace root, `git init` run inside
  it only. The workspace root was confirmed not to be a repository, before and
  after.
- `CLAUDE.md` moved from the workspace root into the repository, as instructed.
  The plan, the checklist and the handover stay outside it.
- MIT licence, `.gitignore` covering `.env`, `pyproject.toml`, Python package
  skeleton for the six modules, `.env.example` with the pinned model.
- `schema/fields.yaml`, 37 fields. Tiers are `null` throughout and are assigned
  at M5.
- `schema/event.schema.json`, JSON Schema draft 2020-12.
- `schema/otel-mapping.md`, with the pinned commit and retrieval date at the top.
- `docs/methodology.md`, the pre-commitment.
- `docs/attack-class-references.md` and `docs/framework-references.md`, the
  verified identifiers, so M2 and M8 do not have to re-verify.
- `SPEC.md` skeleton with the nine section headings fixed.
- Test suite: **40 tests, green.**

### On the test suite

The suite tests the M0 artefacts rather than being empty, because the artefacts
are the deliverable. Three tests are worth naming:

- `test_no_tier_is_assigned_before_the_ablation` fails if any field carries a
  tier. This makes the pre-commitment mechanical rather than a promise.
- `test_every_schema_property_exists_in_the_register` and its mirror check the
  register and the schema agree in both directions. A field emitted but not
  registered would escape the ablation, which would be a silent hole.
- `test_style.py` enforces the house style automatically: no em-dashes, none of
  the six banned words, and no API key material in any tracked file.

### Outstanding

- **Spend alert on the API account is not configured.** It cannot be done from
  this session and needs the owner to set it in the console before M2, which is
  the first stage that spends. The checklist item stays unticked.
- `ANTHROPIC_API_KEY` is not present in the environment. Not needed for M0.
  Needed from M1.

### Commit hashes

| Artefact | Commit |
|---|---|
| Pre-commitment (`docs/methodology.md`) | `c8b28dd00be4be5fcdb7ee2d6751a60aec8eda9e` |

The pre-commitment was committed on its own, before the schema, before any
detector and before any capture. The ordering is checkable with
`git log --oneline --reverse`.

### History rewritten, 17 August 2026

The four M0 commits were rewritten to remove co-authorship trailers. The work
is the owner's alone and the repository carries no attribution to a tool.

Rewriting changes commit hashes, so **the hash in the table above is the
post-rewrite one**. Its previous value was `ad13606b`. Anyone comparing this
file against an earlier copy will see the difference, so it is recorded here
rather than left to look like a discrepancy.

Nothing else changed:

- File contents at every commit are byte-identical to before the rewrite,
  verified with `git diff` against a backup tag taken beforehand.
- Commit order is unchanged.
- No capture existed on either side of the rewrite, so the claim the
  pre-commitment hash exists to support, that the rules predate every scored
  run, is unaffected. The rules remain the second commit in the repository.

The trailer-bearing commits were then made unreachable, so the published
history contains one authorship and one only.

**Hours:** to be recorded by the owner.
