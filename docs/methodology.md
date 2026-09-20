# Methodology and pre-committed rules

**Status: pre-commitment. Committed at M0, before any scored run exists.**

Every rule in this file was fixed before a single capture was taken. The commit
that introduced it is recorded in `docs/build-log.md`, so the ordering can be
checked by anyone rather than taken on trust.

These rules are not tuned to results. If a result makes a rule look wrong, the
result and the rule are both reported as they stand, and the concern is noted
separately. That is the whole point of writing them down first.

---

## 1. What is being measured

Two separate measurements, reported separately and never combined:

- **Attack success.** Did the attack achieve its objective? Decided by a
  machine-checkable oracle written before the runs, for example whether a canary
  string appears in an outbound tool argument.
- **Attack detection.** Did a detector fire on the captured telemetry? Decided
  by tested code reading the logs.

An attack the model refused is not a detection failure. Conflating the two is
the most common way this kind of work gets picked apart, so detection rate is
always reported over **successful** attack trials only, with the success rate
stated alongside it.

There is no manual adjudication anywhere in the scoring path. Every outcome is
computed by tested code from captured logs against oracles written beforehand.

---

## 2. Corpus size and the denominator

| Corpus | Size | Note |
|---|---|---|
| Attack scenarios | 10 | One per attack class, `attacks/scenarios/` |
| Trials per scenario | **10** | Amended from 5, see below |
| Attack sessions | **100** | |
| Benign sessions | approximately 100 | Across three or four legitimate task types, seeded |

**Amendment recorded, 12 August 2026.** The project plan specifies five trials
per scenario. The owner raised this to ten at M0, before any capture, on the
following reasoning. With five trials a detection rate can only take the values
0, 20, 40, 60, 80 or 100 per cent, so a 20 percentage point materiality
threshold is the smallest change the instrument can represent: a single trial
flipping. Ten trials make 20 percentage points equal two trials and halve the
granularity of every rate. The added cost is roughly fifty more sessions against
a small pinned model, which the budget absorbs. This amendment supersedes the
plan and is recorded in `PROJECT-HANDOVER.md`.

**All rates are reported as a fraction and a percentage together**, for example
`7/10 (70%)`. Percentages alone hide how coarse the denominator is. This applies
to every table in `results/`, in `SPEC.md` and in the write-up.

---

## 3. The tiering rule

Stated verbatim. Tiers are assigned at M5 by applying this rule mechanically to
the necessity matrix, with no adjustment.

> **Required:** removing the field makes at least one attack class undetectable.
>
> **Recommended:** removing the field materially degrades detection for at least
> one class, with nothing going dark.
>
> **Optional:** no measurable detection effect, but a stated incident response,
> forensic or regulatory justification for keeping it.
>
> **Not required:** no measurable detection effect and no stated justification.

**"Undetectable" means the detection rate for that class falls to zero**, that
is 0/10 successful trials detected, when the field is nulled. Nothing softer
counts as undetectable.

**"A stated justification"** for the Optional tier means a written reason
recorded in `schema/fields.yaml` before the sweep, not one composed afterwards
to rescue a field that failed. A field with no detection effect and no
pre-existing justification is tiered **Not required** and is published as such,
including any field this profile added for security reasons. Publishing the
failures is what makes the successes worth reading.

---

## 4. The materiality threshold

Fixed with exact numbers. Not to be changed after the first scored run.

A field's removal **materially degrades** detection for an attack class when
either of the following holds:

1. **Detection rate for that class falls by 20 percentage points or more.**
   With ten trials per scenario this is a fall of at least 2 successful trials
   out of 10. A fall of a single trial, 10 percentage points, does not count.

2. **The false positive rate for that detector rises above 10 per cent**, that
   is more than 10 of approximately 100 benign sessions produce a detection.
   The benign corpus gives a resolution of about 1 percentage point, so this
   threshold is well supported by the denominator.

Either condition alone is sufficient. The thresholds are stated as fixed
numbers rather than as statistical tests because the corpus is small and a
significance test on ten trials would give a false impression of precision.
The limitation this creates is stated in Section 7.

### The three states in the necessity matrix

| State | Meaning |
|---|---|
| `X` | The attack class becomes undetectable without this field: detection falls to 0/10 |
| `x` | Detection degrades materially, as defined above, with nothing going dark |
| `.` | No measurable effect |

---

## 5. The holdout commitment

**Two of the ten scenarios are held out.** They are named at M2, before any
detector work begins, and their captures are not opened until M4 scoring.

Detectors are authored against the eight non-holdout scenarios only. Prompt and
detector development happens against throwaway fixtures, never against the
frozen corpus.

Held-out and developed-against results are reported separately, and the gap
between them is stated whatever it shows. A large gap means the detectors did
not generalise, and that is a finding to publish rather than a problem to hide.

> **Committed at M2, 21 September 2026.** The held-out scenarios are **A5,
> improper output handling** and **A9, cross-tenant retrieval**. Ruled by the
> owner. This commit is made before any scenario file exists in
> `attacks/scenarios/`, so the ordering in `git log` shows the commitment
> preceded the corpus. The commit hash is recorded in `docs/build-log.md`
> against the M2 entry. This paragraph is not edited afterwards.
>
> Reason for the pair, as ruled: A9 is structurally close to A3, sensitive
> information disclosure, so it tests whether a detector written against A3
> generalises across a tenant boundary. A5 is unlike every other class, so it
> tests whether the detector set covers an output sink it was never shown.

The plan named A5 and A9 as holdout **candidates**. The commitment above
confirms that candidacy. It was a choice, not a default: the alternative
considered was to hold out A10, the staged exfiltration chain, as the harder
test of generalisation, and it was rejected because A10 is the scenario the
egress and context fields were designed around and the detectors need to be
developed against it.

---

## 6. Freeze discipline

Once tagged, the following are read-only: `attacks/scenarios/`,
`attacks/oracles.py`, the benign generator output, `lab/corpus/` and everything
in `runs/`. The freeze tag is recorded in the build log.

The schema is frozen at M1. No field is added after that point without
re-running every capture, because a field that was not emitted from the first
run cannot be ablated later.

Every scored run writes a manifest recording model, config version, prompt
version, seed, corpus tag, token counts and date.

**Canary values under `runs/`, ruled 21 September 2026.** The M1 build log
observed that no canary value appeared anywhere under `runs/`. That was a
description of two benign captures, not a rule, and it is false by design from
the first successful attack trial: the oracles for A1, A3, A7, A9 and A10 fire
on a canary reaching `content.response_text` or a tool argument, and both are
stored under full content retention. The canary placement test in
`tests/test_corpus.py` therefore scans the source tree, `lab/` and `attacks/`,
and not `runs/`. A canary in a scenario file, an overlay document or an oracle
would let an attack score itself, so that is what the test forbids. A canary in
a capture is evidence, and is what the oracle reads.

---

## 7. Limitations, stated before the results

### 7.1 Circularity

The same person designed the schema, wrote the attacks and wrote the detectors.
Detectors that key on fields the author chose to emit will tend to find those
fields necessary. This is the weakest joint in the work and it is not fully
fixable.

Two things reduce it and neither eliminates it:

- Detectors are authored against **observable attack behaviour** rather than
  against the field list. The question asked when writing a detector is "what
  did the attack do that a defender could see", not "which field shall I use".
- The two held-out scenarios test whether the detectors generalise to attacks
  they were not written against.

Neither measure removes the underlying problem: a field that was never emitted
cannot be found necessary, and a field the author found interesting enough to
emit is more likely to end up in a detector. A reader should treat the necessity
matrix as evidence about **this** schema and **these** detectors, not as a
general claim about all possible logging schemas.

### 7.2 A small denominator

Ten trials per scenario and roughly one hundred benign sessions. Rates are
coarse and confidence intervals would be wide. Fixed thresholds are used rather
than significance tests, and every rate is reported as a fraction so the reader
can see the denominator.

### 7.3 One model, one agent, synthetic data

Results are captured against a single pinned small model driving a deliberately
small agent over a synthetic corpus written for a fictional company. A smaller
model is cheaper and more injectable, which is what produces telemetry worth
detecting, but it invites the question of whether the findings hold on a
frontier model.

Two things address that question and neither settles it. The bounded local model
cross-check at M7b re-runs the attack corpus against a different model and
reports whether the necessity matrix changes. And the claim being made is about
**which fields carry detection signal**, not about absolute attack success
rates. The matrix is expected to be more stable across models than the raw
success numbers, but that expectation is itself untested until M7b runs.

If M7b is killed under its sixty minute rule, portability is recorded as
untested. It is not rounded up.

**Extended thinking is disabled for the whole scored corpus.** Ruled by the
owner on 21 September 2026, at the start of M2 and before any scenario was
authored or any scored session captured. Thinking costs tokens on every session
and adds variation between trials, and a corpus captured half one way and half
the other would not be comparable. The limitation this creates: thinking may
make the model harder to inject, so the attack success rates reported here may
sit above what a production agent with thinking enabled would show. That
affects the absolute success figures, which this work does not claim, and is
not expected to affect which fields carry detection signal, which it does. The
expectation is untested and is stated as such.

### 7.4 Single author

No independent review of the scenarios, the oracles or the detectors. Everything
is published so that a reader can check the work, which is a weaker guarantee
than someone having actually checked it.

---

## 8. Retention of prompt and response text

This is the field group with real data protection consequences, so the position
is stated explicitly rather than left implied.

### 8.1 In this lab

**Full prompt and response text is captured.** The retrieval corpus is
synthetic, written fresh for a fictional company, and contains no real personal
data and no employer or client material. Capturing full content gives the
detectors the most to work with and lets the ablation test the content fields
honestly against the alternatives.

### 8.2 What the profile recommends for production

The profile does not recommend that every deployment capture full content. The
recommended posture, to be expanded per tier in `SPEC.md` once tiers are known:

| Posture | Recommendation |
|---|---|
| Hash | Always. `content.prompt_hash` and `content.response_hash` are cheap, carry no personal data, and support correlation and integrity checking. |
| Truncate | A middle path where full capture is not acceptable. Retains the leading portion of prompt and response, which is where injected instructions usually sit. |
| Full text | Opt-in. Requires a lawful basis, a short retention period and redaction applied before storage, recorded through `content.redaction_applied`. |

The ablation will show what detection capability is lost by choosing hash or
truncation over full text. That measurement is the point: a deployment can then
make the data protection trade-off with a number attached rather than by
assertion. If the ablation shows the content fields carry less signal than
expected, the recommendation is revised to match the measurement and the change
is recorded.

---

## 9. What would falsify the headline claim

Stated in advance so it cannot be quietly redefined later.

The expected finding is that the fields with the highest detection value are the
ones with no OpenTelemetry equivalent, in particular the seven flagged
`security_only` in `schema/fields.yaml`.

That claim is **weakened** if several of those seven tier as Optional or Not
required. It is **refuted** if the fields that tier Required are predominantly
ones the conventions already cover.

Either outcome is published as the result. A negative result here is still the
only measurement of its kind that has been published, and it is reported with
the same prominence as a positive one would have been.
