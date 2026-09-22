"""The ablation sweep: null a field in the captured logs, re-run the detectors.

**No model call is made anywhere in this package.** Fields are nulled in
memory, in copies of the captured events, and the seven detectors frozen at
`freeze-m4` are re-run over the copies. If this ever needed the API, the design
would be wrong.

**Nothing under `runs/` is written.** Every capture is opened for reading,
loaded once, and never mutated. The oracles decide which trials succeeded from
the unmodified captures, so the set of successful trials is fixed before any
field is nulled and only the detectors ever see an ablation.

**Nulling sets a key that is already there and never deletes one.** Handover
Section 6.6: a group that appears in an event carries every one of its
registered keys, null where a value does not apply. An absent key and a null
key must stay distinguishable, or the sweep would measure two things at once,
so a present group missing one of its keys raises rather than being worked
around. An event that does not carry the group is left as it is: no group is
ever added.

**An undeclared read raises.** `detect/session_view.py` already refuses a name
the register does not carry. The sweep also checks, after every detector run,
that the fields read are inside the detector's declared set. The necessity
matrix is built from those declarations, so a detector reading outside its own
would make the matrix wrong without anything else noticing.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from attacks.oracles import load_scenario, score_run
from detect.detectors import DETECTORS, Detector, DetectorConfig
from detect.session_view import registered_fields, session_view
from lab.config import REPO_ROOT

RUNS_DIR = REPO_ROOT / "runs"
CLASSES = tuple(f"A{i}" for i in range(1, 11))
BASELINE = "baseline"


class AblationError(RuntimeError):
    """The sweep met something it cannot measure honestly, and stopped."""


class UndeclaredRead(AblationError):
    """A detector read a registered field it does not declare."""


@dataclass(frozen=True)
class Capture:
    """One captured session, loaded once and never mutated."""

    run_id: str
    events: tuple[dict[str, Any], ...]
    attack_class: str | None = None
    successful: bool = False
    benign_type: str | None = None


@dataclass(frozen=True)
class Ablation:
    """What one pass nulls. The baseline nulls nothing."""

    key: str
    fields: tuple[str, ...]


def _read_capture(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    events_path = REPO_ROOT / manifest["session"]["events_path"]
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return manifest, events


def load_corpus(runs_dir: Path = RUNS_DIR) -> tuple[Capture, ...]:
    """The hundred attack trials and the hundred benign sessions, read only.

    Success is decided here, once, by the frozen oracles over the captures as
    they are on disk. Nothing downstream can change which trials succeeded.
    """
    captures: list[Capture] = []
    for number in range(1, 11):
        scenario_id = f"a{number:02d}"
        scenario = load_scenario(scenario_id)
        for run_dir in sorted(runs_dir.glob(f"m2-{scenario_id}-t[0-9][0-9]")):
            manifest, events = _read_capture(run_dir)
            captures.append(Capture(
                run_id=manifest["run_id"],
                events=tuple(events),
                attack_class=f"A{number}",
                successful=bool(score_run(scenario, run_dir)),
            ))
    for run_dir in sorted(runs_dir.glob("m3-b[0-9][0-9][0-9]")):
        manifest, events = _read_capture(run_dir)
        captures.append(Capture(
            run_id=manifest["run_id"],
            events=tuple(events),
            benign_type=str(manifest["task"]["type"]),
        ))
    return tuple(captures)


def null_fields(events: Sequence[dict[str, Any]], fields: Iterable[str]) -> tuple[dict[str, Any], ...]:
    """Copies of `events` with each named field set to null where it is carried.

    Only the group dict that holds a nulled field is copied; every other part
    of an event is shared with the original, which is never written to.
    """
    targets: dict[str, list[str]] = {}
    for name in fields:
        if name not in registered_fields():
            raise AblationError(f"{name!r} is not a registered field")
        group, _, leaf = name.partition(".")
        targets.setdefault(group, []).append(leaf)
    if not targets:
        return tuple(events)

    out: list[dict[str, Any]] = []
    for event in events:
        copied: dict[str, Any] | None = None
        for group, leaves in targets.items():
            if group not in event:
                continue
            block = event[group]
            if not isinstance(block, dict):
                raise AblationError(
                    f"{event.get('event_type')} event carries group {group!r} as "
                    f"{type(block).__name__}, not an object"
                )
            missing = [leaf for leaf in leaves if leaf not in block]
            if missing:
                raise AblationError(
                    f"{event.get('event_type')} event carries group {group!r} without "
                    f"{missing}: an absent key cannot be told apart from a nulled one"
                )
            if copied is None:
                copied = dict(event)
            copied[group] = {**block, **dict.fromkeys(leaves)}
        out.append(copied if copied is not None else event)
    return tuple(out)


def fires(detector: Detector, events: Sequence[dict[str, Any]], config: DetectorConfig) -> bool:
    """Run one detector over one session, refusing any read it did not declare."""
    view = session_view(list(events))
    fired = detector.run(view, config).fired
    undeclared = view.fields_read - detector.reads
    if undeclared:
        raise UndeclaredRead(f"{detector.id} read {sorted(undeclared)} without declaring it")
    return fired


def ablations(field_names: Sequence[str], field_groups: dict[str, str]) -> tuple[Ablation, ...]:
    """The baseline, every field alone, and every pair within one group.

    Order follows the register, so the output is the same on every run.
    """
    passes = [Ablation(BASELINE, ())]
    passes.extend(Ablation(name, (name,)) for name in field_names)
    for first, second in itertools.combinations(field_names, 2):
        if field_groups[first] == field_groups[second]:
            passes.append(Ablation(f"{first}+{second}", (first, second)))
    return tuple(passes)


def sweep(
    captures: Sequence[Capture],
    config: DetectorConfig,
    passes: Sequence[Ablation],
    detectors: Sequence[Detector] = DETECTORS,
) -> dict[str, dict[str, frozenset[str]]]:
    """For each pass, the run identifiers each detector fires on."""
    result: dict[str, dict[str, frozenset[str]]] = {}
    for ablation in passes:
        fired: dict[str, set[str]] = {d.id: set() for d in detectors}
        for capture in captures:
            events = null_fields(capture.events, ablation.fields)
            for detector in detectors:
                if fires(detector, events, config):
                    fired[detector.id].add(capture.run_id)
        result[ablation.key] = {k: frozenset(v) for k, v in fired.items()}
    return result
