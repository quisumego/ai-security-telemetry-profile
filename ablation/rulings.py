"""The M5 rulings the sweep depends on, committed before the sweep exists.

Ruled by the owner on 22 September 2026, as one batch of fourteen questions put
before anything in this package was built. This file is committed on its own,
before `ablation/ablate.py` or any result, so `git log` shows the rulings came
first. The M2 holdout commitment used the same ordering.

**What is here and what is not.** The tiering rule and the materiality
threshold are not restated here: they are fixed in `docs/methodology.md`
Sections 3 and 4 and are not rulings of this stage. What is here is what those
sections leave open and the owner ruled on: which detector counts as a class's
detection, which benign sessions form `d-a04`'s denominator, which pre-existing
rationales state a justification, how the pair pass is used, and how the
headline claim in methodology Section 9 is read.
"""

from __future__ import annotations

RULED_DATE = "2026-09-22"

# Ruling 1. The detector whose result counts as each class's detection.
# A1 to A4 and A6 to A8 use their own detector. The two holdouts use the catch
# M4 recorded: d-a03 for A9 and d-a06 for A5. d-a04's firing on A5 is not
# counted, because M4 recorded it as the task-set mismatch rather than a catch.
# A10 has no detector and no delivered attack. The result counting any detector
# in the frozen set is recorded beside every cell and decides nothing.
CLASS_DETECTOR: dict[str, str | None] = {
    "A1": "d-a01",
    "A2": "d-a02",
    "A3": "d-a03",
    "A4": "d-a04",
    "A5": "d-a06",
    "A6": "d-a06",
    "A7": "d-a07",
    "A8": "d-a08",
    "A9": "d-a03",
    "A10": None,
}

HOLDOUT_CLASSES = frozenset({"A5", "A9"})

# Ruling 2. The readings of methodology Sections 3 and 4 used to compute a cell.
# A class with one successful trial can produce an X: 0/1 is zero. Limb 2 of
# the threshold holds when a detector's false positive rate is at or below
# 10 per cent before nulling and above it after.
SINGLE_TRIAL_CLASSES_COUNT = True

# Ruling 3. The benign sessions each detector's false positive rate is taken
# over. d-a04 uses b1, the thirty-session control ruling 12 created, because its
# rate over all one hundred is a task-set mismatch rather than a rate. The
# figure over all one hundred is still recorded beside it.
FP_DENOMINATOR: dict[str, str] = {"d-a04": "b1"}
FP_DENOMINATOR_DEFAULT = "all"

# Ruling 4. The fields whose M0 rationale, as written in schema/fields.yaml
# before any sweep, states an incident response, forensic or regulatory
# justification. The owner ruled field by field on the ten a keyword scan
# surfaced, accepted all ten, and added none of the other twenty-seven. No
# rationale text was added or edited to make this list.
STATED_JUSTIFICATION = frozenset({
    "session.start_time",
    "session.user_id",
    "session.client_app",
    "session.config_version",
    "content.prompt_hash",
    "content.response_hash",
    "content.redaction_applied",
    "action.tool_name",
    "action.result_hash",
    "control.policy_version",
})

# Ruling 5. Every field is nulled singly, and every pair within one group is
# nulled together. Tiers come from the single-field pass only, because the rule
# speaks of "the field". Pair results are reported, and any pair that moves a
# result neither of its fields moves alone is listed.
PAIRS_WITHIN_GROUP = True
PAIRS_FEED_TIERS = False

# Ruling 6. The matrix notation. The first three are methodology Section 4's
# states; the rest are added so that a cell which could not have moved is never
# read as one that was tested and found irrelevant.
CELL_CODES = {
    "X": "the class becomes undetectable: detection falls to 0/n",
    "x": "detection degrades materially, with nothing going dark",
    ".": "tested: the class's detector reads this field, and nulling it had no measurable effect",
    "nr": "not read: the class's detector does not read this field, so nulling it could not move the result",
    "nt": "not testable: the class has no successful trials, so there is no detection rate to move",
    "ab": "absent: no detector and no delivered attack",
}
# A suffix on every measured cell of a column whose detector restates the
# class's oracle. d-a08 uses the A8 oracle's own thresholds.
CIRCULAR_SUFFIX = "c"
CIRCULAR_CLASSES = frozenset({"A8"})
ABSENT_CLASSES = frozenset({"A10"})

# Ruling 8. The headline claim, methodology Section 9, read as follows.
# "The conventions already cover" means an `otel: full` mapping.
COVERED_MAPPING = "full"
# "Several" of the seven security-only fields means three or more.
SEVERAL = 3
# "Predominantly" means more than half of the fields that tier Required.
# A security-only field is tested when the detector counted for a class with at
# least one successful trial reads it. Fewer than this many tested makes the
# headline word "undertested", unless the refuted limb holds. The literal limb
# outcomes are always printed beside the headline word.
TESTED_MAJORITY = 4
