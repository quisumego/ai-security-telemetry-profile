"""The M6 rulings the volume model depends on, committed before the model exists.

Put to the owner on 22 September 2026 as one batch of fifteen questions with the
design, before anything in this package was built, and ruled on 23 September
2026: the recommended option on every one. This file is committed on its own,
before `cost/model.py` or any result, so `git log` shows the rulings came first.
The M2 holdout commitment and the M5 rulings used the same ordering.

**Two quantities, never blended.** Model spend is what the captures cost to run,
read from the manifests. Telemetry volume is what the profile would log, read
from the events files. They have different units, sit in different sections of
the output, and no figure combines them.

**What is not here.** The tiers are read from `schema/fields.yaml` and the
necessity matrix from `results/necessity.json`. Neither is restated or edited.
"""

from __future__ import annotations

RULED_DATE = "2026-09-23"

# Ruling 1. Sessions per user per day, for the projections. No capture supports
# any figure: this is an assumption about the fictional deployment, not a
# measurement. One assisted task per working hour over an eight-hour day gives
# eight, rounded to ten. The projection is linear in this number, so a reader
# rescales it exactly. It is restated beside every projection.
SESSIONS_PER_USER_PER_DAY = 10
SESSIONS_PER_USER_PER_DAY_BASIS = (
    "an assumption, not a measurement: one assisted task per working hour over "
    "an eight-hour day gives eight, rounded to ten; the projection is linear in it"
)
USER_COUNTS = (1_000, 10_000)

# Ruling 2. Both byte measures are reported.
#   raw:   the UTF-8 bytes on disk, as the lab serialised them. Each group is
#          credited with its `"group": {...}` member as written; the envelope is
#          the remainder, so groups and envelope sum to the file size exactly.
#   value: per field, the UTF-8 length of the value's string form. Strings as
#          they are, integers and reals as JSON text, booleans as true or false,
#          arrays and objects as compact JSON. Null counts zero, keys count
#          zero. An approximation of a column store's size, never a billed size.
BYTE_MEASURES = ("raw", "value")

# Ruling 3. The truncate posture keeps the leading characters of each text
# field, counted as Unicode code points. 1,024 is the headline; 256 and 4,096
# are shown per session only, as sensitivity. Disclosed when ruled: the
# exploratory length distribution had been seen before this was chosen.
TRUNCATE_CHARS = 1_024
TRUNCATE_SENSITIVITY = (256, 4_096)

# Ruling 4. The postures reach the two content text fields only, as
# docs/methodology.md Section 8.2 defines them. The hashes are kept under every
# posture. action.tool_arguments is reported beside them as the free text the
# postures do not reach.
POSTURES = ("full", "truncate", "hash")
POSTURE_FIELDS = ("content.prompt_text", "content.response_text")
KEPT_HASHES = ("content.prompt_hash", "content.response_hash")
FREE_TEXT_BESIDE = ("action.tool_arguments",)

# Ruling 5. Projections come from the benign corpus alone, at its captured mix
# (b1 30, b2 25, b3 20, b4 25), which is the generator's design and not a
# measured traffic mix. The attack corpus is reported per class and never
# projected.
PROJECTION_CORPUS = "benign"
ATTACK_CORPUS_PROJECTED = False

# Ruling 6. Model spend is reported as measured, per class for M2 and per task
# type for M3, in tokens and in the SDK's estimated USD. It is not projected.
MODEL_SPEND_PROJECTED = False

# Ruling 7. Volume only. No monetary figure is attached to telemetry. Price is a
# parameter the reader supplies; the Sentinel mapping names where to read it.
PRICE_PER_GB = None

# Ruling 8. Daily ingest only. No retention period is assumed and no stored
# volume is computed.
RETENTION_PERIODS_DAYS: tuple[int, ...] = ()

# Ruling 9. Retention guidance per tier, with the tier read from the register
# at render time. A Not required tier is never a recommendation to discard.
# Two fields are named as carve-outs, each with its reason.
CARVE_OUTS = {
    "session.id": (
        "the sweep takes one capture file as one session, so nulling this field "
        "could not change what a detector saw; a real pipeline receives events "
        "from many sessions interleaved and needs it to put a session back "
        "together, and every session-scoped rule in the Sentinel mapping groups by it"
    ),
    "action.egress_target": (
        "it is what separates the A1 attack from benign session m3-b100, which "
        "carried the same tracked value to a permitted internal recipient; the "
        "tiering rule cannot credit a field for the false positives it prevents"
    ),
}

# Ruling 10. Sentinel column names: PascalCase of the register name with its
# group prefix, so session.tenant_id becomes SessionTenantId. The register name
# is recorded beside every column.
COLUMN_NAMING = "pascal_case_with_group_prefix"

# Ruling 11. Output layout. cost/ holds these rulings and the model; siem/
# generates the Sentinel artefacts; results/volume.json and results/volume.md
# are written by the model; docs/sentinel-mapping.md is filled against its
# placeholder. The canary placement scan is extended to cost/ and siem/, and the
# style scan to .kql files.
RESULTS_JSON = "results/volume.json"
RESULTS_MD = "results/volume.md"

# Ruling 12. Tag the commit that writes the results.
TAG = "volume-m6"

# Ruling 13. Every stale line listed in the design is corrected at close-out and
# marked as a correction, in PROJECT-HANDOVER.md and in the checklist.
# Ruling 14. Stage hours from the first M6 commit to the last, with the M4
# method's figure beside it.
# Ruling 15. The rest of the design approved as proposed, including:
#   the unit is each line of the 200 scored events files, named by each
#   manifest's session.events_path; outboxes, notes and the three pre-freeze
#   runs are excluded;
#   the spread is n, minimum, median, mean, p90 and maximum, with p90 by the
#   nearest-rank method;
#   a GB is 10**9 bytes;
#   projections use the mean per session, with the spread printed beside it.
SPREAD = ("n", "min", "median", "mean", "p90", "max")
BYTES_PER_GB = 10**9
