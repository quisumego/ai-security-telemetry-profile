"""The telemetry emitter.

One event per line of JSON Lines, every line validating against
`schema/event.schema.json` before it is written. Validation happens at capture
time rather than at scoring time, so a malformed event fails the run that
produced it instead of being discovered weeks later in `runs/`.

Two rules the rest of the lab depends on:

1. **The key set comes from the register, not from this file.** Group keys are
   read from `schema/fields.yaml` at construction. If a field is added to the
   register and not emitted, or emitted and not registered, that is a test
   failure rather than a silent hole in the ablation.

2. **A group that appears in an event carries every one of its registered keys,
   with null where a value does not apply.** Nulling a field during the M5
   ablation then means setting a key that is already there, never deleting one.
   An absent key and a null key would otherwise be indistinguishable, and the
   sweep would be measuring two different things at once.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml
from jsonschema import Draft202012Validator

GROUPS = ("session", "turn", "content", "retrieval", "action", "control")


def register_group_keys(register_path: Path) -> dict[str, list[str]]:
    """Group name to the leaf names registered under it, read from fields.yaml."""
    with register_path.open(encoding="utf-8") as fh:
        register = yaml.safe_load(fh)
    keys: dict[str, list[str]] = {group: [] for group in GROUPS}
    for entry in register["fields"]:
        group, _, leaf = str(entry["name"]).partition(".")
        keys[group].append(leaf)
    return keys


@dataclass(frozen=True)
class SessionIdentity:
    """The session group. Carried on every event, so each line stands alone."""

    id: str
    start_time: str
    user_id: str
    tenant_id: str
    client_app: str
    agent_id: str
    config_version: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "start_time": self.start_time,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "client_app": self.client_app,
            "agent_id": self.agent_id,
            "config_version": self.config_version,
        }


def canary_hits(text: str | None, canaries: Sequence[str]) -> list[str]:
    """Which planted canary values appear in this text."""
    if not text:
        return []
    return [value for value in canaries if value in text]


def contains_canary(payload: Any, canaries: Sequence[str]) -> bool:
    """True where any canary appears anywhere in a payload.

    The payload is serialised first, so a canary buried in a nested tool
    argument is found as readily as one in a flat string.
    """
    if payload is None:
        return False
    if isinstance(payload, str):
        blob = payload
    else:
        blob = json.dumps(payload, default=str)
    return any(value in blob for value in canaries)


class Emitter:
    """Writes validated ASTP events to a JSON Lines file."""

    def __init__(
        self,
        path: Path,
        astp_version: str,
        identity: SessionIdentity,
        policy_version: str,
        canaries: Sequence[str],
        group_keys: dict[str, list[str]],
        schema: dict | None = None,
    ) -> None:
        self.path = path
        self.astp_version = astp_version
        self.identity = identity
        self.policy_version = policy_version
        self.canaries = tuple(canaries)
        self.group_keys = group_keys
        self._validator = Draft202012Validator(schema) if schema else None
        self._count = 0
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("w", encoding="utf-8")

    # ---------------------------------------------------------------- write --
    @property
    def events_written(self) -> int:
        return self._count

    def _full(self, group: str, values: dict[str, Any] | None) -> dict[str, Any]:
        """Fill a group out to every registered key, null where absent."""
        values = values or {}
        unknown = set(values) - set(self.group_keys[group])
        if unknown:
            raise KeyError(f"{group} carries unregistered keys {sorted(unknown)}")
        return {key: values.get(key) for key in self.group_keys[group]}

    def emit(
        self,
        event_type: str,
        *,
        turn: dict[str, Any] | None = None,
        content: dict[str, Any] | None = None,
        retrieval: dict[str, Any] | None = None,
        action: dict[str, Any] | None = None,
        canary_triggered: bool = False,
        block_reason: str | None = None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "astp_version": self.astp_version,
            "event_type": event_type,
            "session": self.identity.as_dict(),
        }
        if turn is not None:
            event["turn"] = self._full("turn", turn)
        if content is not None:
            event["content"] = self._full("content", content)
        if retrieval is not None:
            event["retrieval"] = self._full("retrieval", retrieval)
        if action is not None:
            event["action"] = self._full("action", action)
        event["control"] = self._full(
            "control",
            {
                "canary_triggered": canary_triggered,
                "policy_version": self.policy_version,
                "block_reason": block_reason,
            },
        )

        if self._validator is not None:
            errors = sorted(self._validator.iter_errors(event), key=lambda e: e.path)
            if errors:
                raise ValueError(
                    f"event of type {event_type!r} failed schema validation: "
                    + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
                )

        self._fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._fh.flush()
        self._count += 1
        return event

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()

    def __enter__(self) -> Emitter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def read_events(path: Path) -> Iterable[dict[str, Any]]:
    """Read a captured JSON Lines file back."""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)
