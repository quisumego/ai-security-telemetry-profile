# CLAUDE.md

Project: AI security telemetry profile (name confirmed at M0).
Owner: Erebus. Personal portfolio project, fully independent of any employer.

## What this project is

A security logging profile for LLM applications and agents. It defines an event schema, assigns every field a tier of required, recommended or optional, and justifies each tier with measurement rather than opinion. The evidence comes from an instrumented lab agent, an attack corpus with machine-checkable oracles, a benign corpus, a set of detectors, and a field ablation harness that determines which fields are load-bearing for which attack classes.

The profile layers on the OpenTelemetry GenAI semantic conventions. It adopts `gen_ai.*` naming where an equivalent exists and adds the security fields the conventions do not cover.

Public outputs: this repository, a demo GIF in the README, and a Medium write-up.

## Read before doing anything

- `ai-logging-standard-project-plan.md` in the workspace root is the authoritative plan.
- `ai-logging-standard-checklist.md` in the workspace root is the single progress record.
- `PROJECT-HANDOVER.md` in the workspace root is the current-state handover and wins where it disagrees with the plan.

These three files are kept outside this repository by design. Never move them in. Never run `git init` in the workspace root.

Follow the plan. If a request conflicts with it, say so before building anything.

## Non-negotiable rules

1. **No employer or client material.** No wording, structures, templates or anything derived from work deliverables. All synthetic documents are written fresh here for the fictional company.
2. **No employer reference** anywhere in this repository or the write-up.
3. **Never reproduce text from any standard.** Paraphrase the intent of DSIT, NCSC, ETSI, ISO and OWASP provisions in original wording and cite identifiers only.
4. **Secrets.** The Claude API key exists only as `ANTHROPIC_API_KEY` in the environment or a local `.env` listed in `.gitignore`. Never in code, config, documentation or a commit.
5. **Nothing invented.** Every figure traces to a captured run. Every external identifier, attribute name and vendor capability is verified against a live source at the time of writing, with a retrieval date recorded. Never cite an ATLAS technique identifier or an OpenTelemetry attribute name from memory.
6. **The owner rules on synthetic content and on any change to the pre-committed rules.** You never mark his review items as approved. Anything he has not confirmed keeps its TODO.

## Engineering rules

- Python 3.10 or later. Layout per the plan, Section 7.
- **The agent behaves, the code decides.** Every detection outcome is computed by tested code from captured logs against oracles written before the runs. There is no manual adjudication step anywhere in the scoring path. If you find yourself proposing one, stop and say so.
- **The ablation makes no model calls.** Fields are nulled in captured logs and the detectors re-run. If the ablation harness needs the API, the design is wrong.
- **Development and evaluation stayed separated.** Detectors were authored against throwaway fixtures only, never against the frozen corpus, as `docs/methodology.md` Section 5 requires. The two holdout scenarios, A5 and A9, stayed closed until M4 scoring and were opened after `freeze-m4`, so that commitment is discharged. The detector set stays frozen at `freeze-m4`.
- **Freeze discipline.** Once tagged, `attacks/scenarios/`, `attacks/oracles.py`, `benign/` output, `lab/corpus/` and everything in `runs/` are read-only. Prompt and detector development happens against throwaway fixtures.
- **Pre-committed rules are not tuned to results.** The tiering rule, the materiality threshold and the holdout choice are fixed in `docs/methodology.md` before the first scored run. If a result makes a rule look wrong, report the result and the rule as they stand, and note the concern separately.
- Every scored run writes a manifest: model, config version, prompt version, seed, corpus tag, token counts, date.
- Cost discipline: the pinned lab model is small, model spend occurs only during attack and benign capture, and total spend is checked against budget at the end of every capture stage.

## Style

UK English, plain English, professional and concise. No em-dashes, use commas, colons or full stops. Never use these six words: robust, seamless, proven, flexible, leverage, various. Scan every text file for em-dashes and those words before finishing a stage.

## Session discipline

- Batch all clarifying questions into one message before starting work. Never mix questions into the build afterwards.
- Surgical edits to existing files, never full regeneration unless explicitly required. Re-read any file before editing it, because the owner edits files between turns.
- Tick the checklist the moment an item completes, and reprint the current stage's section in every reply.
- Commit at every working increment, with messages that state what actually happened.
- Stop at the stage exit criterion. Do not start the next stage in the same session.
