"""The M8 rulings the specification and its publication depend on, committed first.

Put to the owner on 30 September 2026 as one batch of thirty-five questions with
the design, after the pre-flight and the pre-publication scan had run on the
rewritten history and before anything in this package was written. Every
question carried a recommended option. The owner's reply on 1 October 2026 was
"Do all recommended - I approve it all.", taken as the recommended option on all
thirty-five.

This file is committed on its own, before the renderer, the figure ledger,
`SPEC.md`, `README.md` or the write-up, so `git log` shows the rulings came
first. M5, M6, M7 and M7b used the same ordering.

**What this stage is.** Plan Section 6, M8: `SPEC.md`, `README.md`, a demo GIF
made with vhs with its tape committed, the repository made public, and a Medium
write-up. Exit: the repository public, the post live, and every figure in the
post traceable to a committed result file.

**What is not here.** No result, tier, frozen path or generated block is
edited by hand. The tiers stay as M5 applied them, and M7b's reading is a
comparison only. M8 makes no model call and takes no capture.
"""

from __future__ import annotations

RULED_DATE = "2026-10-01"
OWNER_REPLY = "Do all recommended - I approve it all."

MODEL_CALLS = False
CAPTURES = False

# Ruling 1. The pre-publication scan of 30 September 2026 found the system
# prompt canary quoted in the message of the A7 capture commit. It is left as it
# is: the same value is published by design at its registered placement and in
# the captures under runs/, no oracle reads a commit message, and changing a
# message would need a second history rewrite. Recorded in the M8 build log
# entry.

# Ruling 2. The same scan found the pre-commitment's old hash in the rewrite
# entry of docs/build-log.md, and in the message of the commit that recorded the
# rewrite in the build log. Both are left: they are the rewrite's own record of
# the mapping, which docs/history-rewrite.md resolves. The hash test of ruling 9
# covers the public documents, not the dated build log.

# Ruling 3. This package holds the M8 code: these rulings, the renderer for the
# generated blocks of SPEC.md, and the figure ledger.
LEDGER = "spec/figures.yaml"

# Ruling 4. The field register and its tier evidence in SPEC.md are generated
# blocks between markers, written by `.venv/bin/python -m spec.render --write`
# from schema/fields.yaml and the results files. A test requires a fresh render
# to reproduce the file exactly. The prose around them is written by hand.
SPEC = "SPEC.md"

# Ruling 5. The M7b comparison sits in its own subsection after the register,
# read over the local pass and never applied. The register shows the M5 tiers
# only; action.egress_target's row points to its three readings.
M7B_IN_OWN_SUBSECTION = True

# Ruling 6. External identifiers in public text are re-checked against live
# sources before SPEC.md is written, with the new retrieval date recorded
# beside the original one. Any drift is reported beside the pinned value and
# the register is not edited. OpenTelemetry attribute names are stated as at
# the pinned commit, with the live check noted beside them.
RECHECK_IDENTIFIERS_LIVE = True

# Ruling 7. The headline leads in README.md (a section directly under the GIF),
# in SPEC.md (the status block above Section 1, and again at the opening of
# Section 3) and in the write-up (the subtitle and the first 150 words). Each
# states undertested first and weakened beside it, says the claim was not
# refuted, and says the undertested reading is M5 ruling 8's, ruled before the
# sweep but after the M4 baseline was known.
HEADLINE = "undertested"
SECTION_9_AS_WRITTEN = "weakened"

# Ruling 8. The A9 holdout result is never quoted without its exposure in the
# same paragraph (M5 ruling 10). A test checks every paragraph of the public
# documents: one that names A9 together with d-a03 or a detection word must
# carry all four phrases. Generated blocks that carry an A9 cell carry them too.
# The dated build log and the generated results pages are out of scope.
PUBLIC_DOCUMENTS = ("SPEC.md", "README.md", "docs/write-up.md")
A9_EXPOSURE_PHRASES = (
    "knew both holdout outcomes",
    "disclosed A9's retrieval signature",
    "authored from fixtures only",
    "weakened evidence, not a clean holdout",
)

# Ruling 9. Every figure in the public documents is in the ledger, with its
# source file, its key and, for a derived figure, its formula. A test holds
# each entry to its source and to the documents that quote it, and fails on
# any number in a public document that is neither in the ledger nor an
# identifier of an allowed form. The holdout figures come from
# holdout_generalisation in results/baseline.json; per_class.A9 is never a
# source. Every commit hash a public document cites must resolve to a commit
# in this repository and must not be an old hash.
FORBIDDEN_SOURCE_KEYS = ("results/baseline.json:per_class.A9",)

# Ruling 10. Sources are committed result files only: results/, the tiers in
# schema/fields.yaml, the generated files under siem/sentinel/, and a new
# results/benign.json written by `benign.report --write`, so the A1 oracle's
# benign false positive has a committed source. Dates and hashes come from git.
# The plan's cost estimate and the stage hours stay out of public text.
NEW_RESULTS_FILE = "results/benign.json"

# Ruling 11. The write-up's title is option 3 of the plan's Section 10.
TITLE = "I Removed Every Field From My AI Logs to Find Out Which Ones Matter"
SUBTITLE = (
    "Only two of the seven fields I added for security could be tested at all. "
    "Both were required. The claim came back undertested."
)

# Ruling 12. The plan's Section 10 working assumptions are confirmed: a
# professional profile purpose, a mixed security and GRC readership, 1,500 to
# 2,000 words, Medium first and then LinkedIn.
WORDS = (1_500, 2_000)

# Ruling 13. The draft is committed at docs/write-up.md, so the style, canary
# and figure tests hold it. It carries no table, because Medium's story editor
# documents none. The owner pastes it into Medium and supplies the address.
WRITE_UP = "docs/write-up.md"

# Ruling 14. README.md links the post in one small commit after it is live.
README_LINKS_POST = True

# Rulings 15 to 18. The limitations say each of these:
#   15. The volume projections describe ASTP events as this lab emits them, and
#       no tool result is ever logged, so they are not a model of agent logging
#       in general.
#   16. The vendor gap result supports the case for a profile but does not test
#       the headline claim, and the two findings are kept apart.
#   17. Any comparison between vendors carries the qualifier that most Azure
#       verdicts are unconfirmed rather than absent.
#   18. Reading tiers across models would be a new rule written after the
#       results, so it is future work and never presented as a finding.
LIMITATIONS_H1_TO_H4 = True

# Ruling 19. The pre-commitment after the rewrite is stated as proposed: the
# public repository was created after every capture, its history was rewritten
# once with every recorded date copied unchanged, git dates are set by whoever
# commits, and what a reader can check is the order of commits, with
# docs/history-rewrite.md recording how the rewrite was checked.
PRECOMMITMENT_WORDING = True

# Ruling 20. The original history is not offered for inspection, because it
# carries the personal data the rewrite removed.
OFFER_ORIGINAL_HISTORY = False

# Ruling 21. The limitations also carry: circularity and a single author; the
# undertested and Optional readings ruled after the baseline was known;
# Recommended empty by structure; thirty of thirty-seven fields read by no
# detector; the circular A8 detector; two X cells resting on one session each;
# and the A4 oracle's task-set mismatch.
ADDED_LIMITATIONS = True

# Ruling 22. The demo GIF shows report commands only: attacks.report, and
# ablation.matrix narrowed to its verdict line and its Required-field table.
# Neither detect.evaluate form appears, and no deciding cell that names A9.
GIF_COMMANDS = (
    ".venv/bin/python -m attacks.report",
    ".venv/bin/python -m ablation.matrix",
)

# Ruling 23. Installs: ttyd and ffmpeg from the Kali repository, the owner
# running the one sudo line in a terminal; vhs v0.12.1 as the release tarball
# from github.com/charmbracelet/vhs, checked against the release's
# checksums.txt, with the binary placed in ~/.local/bin and no root; no go; the
# Chromium already installed is the browser vhs drives.
VHS_VERSION = "v0.12.1"
VHS_ASSET = "vhs_0.12.1_Linux_x86_64.tar.gz"
VHS_ASSET_BYTES = 9_474_207
APT_PACKAGES = ("ttyd", "ffmpeg")

# Ruling 24. The tape and the GIF live in docs/, the GIF under 5 MB. Before the
# GIF is committed, every command's full output is checked as text for the
# identity values, and every distinct frame is viewed, with the count reported.
TAPE = "docs/demo.tape"
GIF = "docs/demo.gif"
GIF_MAX_BYTES = 5_000_000

# Ruling 25. tests/test_style.py also scans .tape files and .env.example. The
# canary placement scan also covers SPEC.md, README.md, tapes under docs/, and
# this package.
STYLE_SUFFIXES_ADDED = (".tape", ".example")

# Ruling 26. README.md is rewritten to the outline proposed: the GIF, the
# result, the question, the method, how to reproduce each result, where to read
# further, the history rewrite, what it does not claim, and the licence.

# Ruling 27. The stale files are fixed: README.md rewritten, SPEC.md Section 7
# written, pyproject.toml's comment replaced and its packages listing every
# package, and .env.example rewritten to the facts the rewrite kept. The Agent
# SDK stays unpinned and the version the captures ran on is stated.
# attacks/scenarios/README.md is a frozen path and is left as it is.
SDK_VERSION_CAPTURED = "0.2.139"

# Ruling 28. The canary value in tests/test_permissions.py is replaced by a
# value of the same shape that the test asserts is not in the register, so the
# URL normalisation test still checks that the query keeps its case. The canary
# placement scan is extended to tests/.
CANARY_SCAN_COVERS_TESTS = True

# Ruling 29. The owner changes the visibility himself, in the repository's
# settings on GitHub, after confirming at that moment, and checks that the page
# names quisumego/ai-security-telemetry-profile and not the -original
# repository. Both visibilities are read back afterwards.
VISIBILITY_CHANGED_BY = "owner"
REPOSITORY = "quisumego/ai-security-telemetry-profile"

# Ruling 30. The owner sets the repository's description in its About panel on
# the same visit.
DESCRIPTION_SET_BY = "owner"

# Ruling 31. An annotated tag on the commit that carries the M8 build log
# entry, pushed by name before the visibility change. No GitHub release.
RELEASE_TAG = "publish-m8"
GITHUB_RELEASE = False

# Ruling 32. The paragraph of the build log's rewrite entry that records the
# corpus.digest finding, which went beyond the ruled draft, is confirmed.
REWRITE_DIGEST_PARAGRAPH_CONFIRMED = True

# Ruling 33. M8's hours run from its first commit to its last, with the M4
# method's figure beside them. The rewrite records no hours, as ruled at the
# time. No grand total across stages is given.
HOURS_GRAND_TOTAL = False

# Ruling 34. Stale lines in the handover and the checklist are corrected at the
# close-out, marked as corrections.

# Ruling 35. The session stays open until the owner supplies the post's
# address. Sharing the post on LinkedIn is the owner's.
WAIT_FOR_POST_ADDRESS = True
