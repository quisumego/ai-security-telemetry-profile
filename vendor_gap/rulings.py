"""The M7 rulings the vendor gap analysis depends on, committed before it exists.

Put to the owner on 23 September 2026 as one batch of twenty-two questions with
the design, before anything in this package was built. Questions 1 to 17 were
ruled in the owner's first reply. Questions 18 to 22 came back without a
ruling, so those five were asked again before anything was built, as the M5
batch did with its one unanswered point, and ruled the same day. The owner took
the recommended option on all twenty-two. This file is committed on its own,
before the evidence file, the analysis or any result, so `git log` shows the
rulings came first. The M5 and M6 rulings used the same ordering.

**What this stage is.** An evidence stage. Every claim about a vendor comes from
a page read in the session, carries a source number and a retrieval date, and
is held to that source by a test. Nothing is stated from memory, and no vendor's
behaviour is inferred from the other's.

**What is not here.** The tiers are read from `schema/fields.yaml`, the counted
detector per class from `ablation/rulings.py`, and the materiality threshold
from `ablation/matrix.py`, which cites `docs/methodology.md` Section 4. None is
restated or edited.
"""

from __future__ import annotations

from ablation.rulings import CLASS_DETECTOR  # noqa: F401  ruling 10 reuses M5 ruling 1

RULED_DATE = "2026-09-23"

# No model call and no cloud resource. Nothing in the plan asks for an Azure or
# AWS resource, none is created, no console is signed in to, and the package
# never touches the network: pages are read in the session and recorded here.
MODEL_CALLS = False
CLOUD_RESOURCES = False

# Ruling 1. Layers in scope. The plan-named model layer is the headline, and one
# agent layer per vendor is assessed in its own column. Each layer is answered
# on its own. A combined answer is given only where a documented key links the
# two layers' records; otherwise the combination is unconfirmed.
LAYERS = ("model", "agent")
HEADLINE_LAYER = "model"
COMBINED_NEEDS_DOCUMENTED_LINK = True

# Ruling 2. What "vendor defaults" means. The headline counts a surface once its
# own switch is set (a diagnostic setting created, invocation logging enabled,
# tracing enabled), and the switch is recorded as that surface's configuration
# step. The literal reading, what is collected with no action at all, is always
# printed beside it with its own verdicts and class answer.
READINGS = ("switched_on", "as_shipped")
HEADLINE_READING = "switched_on"

# Ruling 3. The verdict vocabulary. "Absent" only where a cited page gives the
# record's full field list and the value is not in it; a field the pages do not
# mention is "unconfirmed", never absent. A vendor's statement that it follows
# the OpenTelemetry GenAI conventions is not evidence that it emits any one
# attribute, and ASTP's own mapping never stands in for a vendor's field list.
VERDICTS = (
    "available_by_default",
    "available_with_configuration",
    "absent",
    "unconfirmed",
)
ABSENT_NEEDS_FULL_FIELD_LIST = True

# Ruling 4. "Available with configuration" names the setting, where it is set,
# and its source.
CONFIGURATION_STEP_RECORDED = True

# Ruling 5. Consequences of enabling a setting: only what the cited page states
# about that setting, in one line, with no price, consistent with M6 ruling 7.
CONSEQUENCES_FROM_CITED_PAGE_ONLY = True
PRICE = None

# Ruling 6. A value inside a body or in free content. A value at a documented
# path inside a request or response body counts only in a separate, labelled
# "body parsed" answer. A value present only in free content, because the
# application wrote it there, never counts.
FORMS = (
    "own_field",
    "body_documented",
    "content_only",
    "caller_supplied",
    "derivable",
)
COUNTS_IN_HEADLINE = frozenset({"own_field"})
COUNTS_WHEN_BODY_PARSED = frozenset({"own_field", "body_documented"})

# Ruling 7. Values the vendor does not produce itself: a caller-supplied value
# through a vendor slot, or a value the deployment derives from what the vendor
# logs plus its own knowledge. Both are absent under vendor defaults, with the
# slot or the inputs named, never counted, and both are listed under the fields
# a deployment has to add itself.
NOT_PRODUCED_BY_VENDOR = frozenset({"caller_supplied", "derivable"})

# Ruling 8. The six ASTP event types get a verdict per surface, as rows kept
# apart from the 37 fields so the field counts are unaffected.
EVENT_TYPES = ("session_start", "turn", "retrieval", "tool_pre", "tool_post", "session_end")

# Ruling 9. A vendor field carries an ASTP field only when its documented
# meaning matches the register's. A related field whose meaning differs, or is
# not documented, is recorded as partial with the difference stated, and the
# vendor pass runs it both ways.
MEANINGS = ("match", "partial")

# Ruling 10. The counted detector per class is M5 ruling 1, imported above. The
# any-detector result is shown beside it and decides nothing.
ANY_DETECTOR_DECIDES = False

# Ruling 11. Class answers are computed by code, as vendor passes over the
# captures, read only and with no model call. A pass nulls what the column does
# not count as available, drops the event types the surface keeps no record of,
# holds the deployment's own configuration (allow lists, document inventory,
# task tool set) as scored, and re-runs the counted detector. The result is
# compared with the baseline under methodology Section 4 as M5 ruling 2 reads
# it, through `ablation.matrix.cell_code`.
COMPUTED_BY_VENDOR_PASS = True

# Ruling 12. Session grouping. Where a surface carries no key that groups a
# session's records, the detector runs over each record as a session of one, and
# a trial counts as detected if any of its records fires.
UNGROUPED_RECORDS_RUN_ALONE = True

# Ruling 13. The class answer vocabulary is M5's, plus one code. `uc` marks a
# class whose answer differs across the combinations of its counted detector's
# unconfirmed or partial inputs.
UNCONFIRMED_CODE = "uc"
ANSWER_WORDS = {
    ".": "stays detectable",
    "x": "degrades materially",
    "X": "becomes undetectable",
    "nt": "not computable: no successful trial",
    "ab": "absent from the corpus",
    "uc": "unconfirmed: the answer depends on what the pages do not settle",
}

# Ruling 14. The evidence file is the source of truth. The generator writes the
# generated blocks of docs/vendor-gap-analysis.md and results/vendor-gap.json
# from it, and tests hold every verdict to a listed source.
EVIDENCE = "vendor_gap/evidence.yaml"
DOC = "docs/vendor-gap-analysis.md"
RESULTS = "results/vendor-gap.json"

# Ruling 15. Citations: numbered sources with the requested URL beside the final
# one where a page redirected, the page's own date (Microsoft's `updated_at`,
# as M6 recorded it; an AWS page carries none, and that is recorded), the
# retrieval date, short quotations, no copies of vendor pages committed, and a
# section recording the traps found.
PAGE_COPIES_COMMITTED = False

# Ruling 16. Layout as proposed, the canary placement scan extended to
# vendor_gap/, the style scan unchanged because it already covers these paths,
# and a tag on the commit that writes the analysis.
TAG = "gap-m7"

# Ruling 17. The order of "the fields a deployment has to add itself": first the
# fields whose addition changes a class answer, as measured by the vendor
# passes; then by tier, read from the register; ties in register order. The
# caution of handover Section 11 goes beside every Not required field.
ADD_ORDER = ("measured", "tier", "register")

# Ruling 18. Naming. The live page names are used, and the plan's name is stated
# once. The current documentation is assessed, and a "(classic)" page is used
# only where the current documentation links or redirects to it.
PLAN_NAME = "Azure AI Foundry"
CLASSIC_ONLY_WHERE_LINKED = True

# Ruling 19. Tidy-up: the stale holdout wording is fixed in benign/report.py
# only. detect.evaluate is left as it is, because its wording comes from the
# frozen detect/detectors.py and is stored in the generated
# results/baseline.json.
FIX_BENIGN_REPORT_WORDING = True
FIX_EVALUATE_WORDING = False

# Ruling 20. The M2 hours are recorded from commit timestamps, both figures,
# marked as reconstructed at M7, and the M2 standing-rules line is ticked with a
# correction note.
M2_HOURS_RECORDED = True

# Ruling 21. The stale lines listed in the design are corrected at close-out,
# marked as corrections. The repository's CLAUDE.md line and the frozen or
# generated text are listed and not edited.
EDIT_CLAUDE_MD = False

# Ruling 22. Stage hours from the first M7 commit to the last, with the M4
# method's figure beside it, counted from the M6 close at 09:14 on
# 23 September 2026.
M4_METHOD_FROM = "2026-09-23 09:14"
