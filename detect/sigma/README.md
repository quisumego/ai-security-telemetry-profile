# Sigma rules

One rule per detector, expressing the same logic in a portable format so the
profile can be read by someone who does not run this repository's Python.

**These are the statement of intent; `detect/detectors.py` is the
implementation that scores.** Where a rule and the Python differ, the Python is
what produced every figure in `results/`, and the difference is a defect to
report rather than a choice.

Two limits worth stating plainly:

- Sigma has no standard way to express a condition spanning several events in
  one session, and several of these detectors are exactly that: retrieval
  followed by a canary in a later turn, or egress after external content
  arrived. Those rules carry a `correlation` note in plain words instead of
  pretending a single-event match is equivalent.
- `A5` and `A9` have no rule. They are holdouts. `A10` has no rule, because its
  attack was never delivered in any captured session.

Field names are the ASTP register's own, from `schema/fields.yaml`.
