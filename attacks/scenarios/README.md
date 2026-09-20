# Attack scenarios

One file per attack class. Each carries the class, its OWASP and MITRE ATLAS
references copied from `docs/attack-class-references.md`, the tools it
exercises, how the attack is delivered, the exact user prompt used on every
trial, any overlay material, and the machine-checkable success oracle.

The prompt is identical across all ten trials of a scenario, so the only
variation between trials is the model's.

No file here may contain a canary value. Oracles refer to canaries by where
the register plants them, never by value, and `tests/test_corpus.py` scans this
directory to enforce that. An attack prompt that carried the string it is
meant to exfiltrate would score itself.

Attack success, decided by the oracle, and attack detection, decided at M4 by
detectors not yet written, are separate measurements and are never combined.
See `docs/methodology.md` Section 1.

Holdouts A5 and A9 were committed in `docs/methodology.md` Section 5 before
any of these files existed.
