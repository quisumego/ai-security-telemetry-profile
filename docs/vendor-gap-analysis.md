# Vendor gap analysis

**Stage:** M7, Vendor gap

**Purpose:** Which attack classes stay detectable on Microsoft Foundry and
Amazon Bedrock with vendor defaults only, read from their documentation. For
anyone deciding what a deployment has to log itself.

---

## 1. The answer

**Documentation only.** No Azure or AWS resource was created, no console was
signed in to, and no model call was made. Every claim about a vendor is cited
to a numbered page read on 23 September 2026.

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

## 2. The question and the method

**The question is hypothetical.** The lab runs on Anthropic's API, not on
either vendor, so it asks what the vendor's own records would carry had the
agent's model calls gone through it, the model layer, or had the agent been
hosted there, the agent layer. Microsoft Foundry is the product the plan calls
"Azure AI Foundry" [1].

**Each surface is read once its own switch is set**, with the as-shipped
reading beside it. On AWS that switch has the reader choose modalities [15],
and Text is taken because the lab's traffic is text only; read with Text as a
further setting, seven fields and three event types move from available by
default to available with configuration, and no class answer changes, which a
test repeats.

**A field is recorded absent only where a cited page lists a record's full
fields, or where only the deployment holds the value.** Otherwise it is
unconfirmed.

**Class answers are computed, not judged.** For each column, the class's
counted detector is re-run over its successful trials and its benign
denominator with everything the column lacks taken away: fields nulled,
unrecorded event types dropped, and ungrouped records run as sessions of one.
An input the pages do not settle is run both ways, and a class whose answers
differ reads `uc`. No model call is made and nothing under `runs/` is written.

The verdicts are in `vendor_gap/evidence.yaml`, each with the pages it rests
on. `vendor_gap/analysis.py` computes the class answers and writes
`results/vendor-gap.json` and the blocks between `generated` markers on these
pages; `tests/test_vendor_gap.py` holds both to it, and
`.venv/bin/python -m vendor_gap.analysis` prints the passes.

## 3. The detail

| Page | What it holds |
|---|---|
| [Surfaces](vendor-gap-analysis/surfaces.md) | The six surfaces, the switch each needs, and the field counts on each |
| [Class answers](vendor-gap-analysis/classes.md) | Every class on every column, and the fields a deployment has to add |
| [Sources](vendor-gap-analysis/sources.md) | The pages read, with their dates, and the quotations that decide a verdict |

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

No class stays detectable on vendor defaults, and none of the seven
security-only fields is available on any surface: a deployment has to log them
itself.

---

**Sources:** the pages numbered in [Sources](vendor-gap-analysis/sources.md); `vendor_gap/evidence.yaml`; `results/vendor-gap.json`.
