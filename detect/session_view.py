"""Controlled access to one captured session, so a detector cannot read a
field it did not declare.

The declaration is not documentation. M5 builds the necessity matrix from it,
so a detector that quietly reads `control.canary_triggered` without declaring
it would make the matrix wrong in a way nothing else catches. Every read goes
through `EventView.get`, which records the registered field name, and
`tests/test_detectors.py` asserts the recorded set is inside the declared set
for every detector against every fixture.

Nothing here reaches tool arguments, response text or retrieval text. A
detector sees registered field values and no content, which is also why a
report can print identifiers and counts without any canary value reaching a
terminal, a document or a commit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Iterator

import yaml

from lab.config import REPO_ROOT

# The registered groups, as schema/fields.yaml names them. A field is addressed
# as "<group>.<name>", which is exactly the register's own key.
GROUPS = ("session", "turn", "content", "retrieval", "action", "control")


@lru_cache(maxsize=1)
def registered_fields() -> frozenset[str]:
    """Every field name in schema/fields.yaml.

    Read from the register rather than restated here, so a field added or
    renamed at M1 cannot drift out of step with what a detector may read.
    """
    register = yaml.safe_load((REPO_ROOT / "schema" / "fields.yaml").read_text(encoding="utf-8"))
    return frozenset(f["name"] for f in register["fields"])


class EventView:
    """One event. `get` is the only way in, and it records what was read."""

    def __init__(self, event: dict[str, Any], recorder: set[str]) -> None:
        self._event = event
        self._recorder = recorder

    @property
    def event_type(self) -> str:
        return str(self._event.get("event_type", ""))

    def get(self, field_name: str) -> Any:
        """The value of a registered field, recording the read.

        `field_name` is the register's own key, for example
        `action.egress_target`. Asking for anything the register does not carry
        raises, because a detector reading an unregistered key could not be
        ablated at M5 and would silently escape the necessity matrix. The check
        is against the register itself, not against the group prefix: a
        plausible-looking name like `action.outcome` is not a field and must
        fail loudly rather than return null.
        """
        group, _, leaf = field_name.partition(".")
        if group not in GROUPS or not leaf or field_name not in registered_fields():
            raise KeyError(f"{field_name!r} is not a registered field")
        self._recorder.add(field_name)
        return (self._event.get(group) or {}).get(leaf)


@dataclass
class SessionView:
    """One session's events, plus the set of fields read through it."""

    _events: list[dict[str, Any]]
    fields_read: set[str] = field(default_factory=set)

    def events(self, event_type: str | None = None) -> Iterator[EventView]:
        for event in self._events:
            if event_type is None or event.get("event_type") == event_type:
                yield EventView(event, self.fields_read)

    def count(self, event_type: str) -> int:
        """How many events of a type. Reads no field, so records nothing."""
        return sum(1 for e in self._events if e.get("event_type") == event_type)


def session_view(events: list[dict[str, Any]]) -> SessionView:
    return SessionView(list(events))
