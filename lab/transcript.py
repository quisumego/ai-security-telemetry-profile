"""Reading completed per-turn figures from the Claude Code transcript.

Why this file exists, recorded because it is not obvious and a later reader
would otherwise assume the SDK was enough.

`AssistantMessage` arrives on the stream **before the message has finished
generating**. Its `usage` and `stop_reason` are the state at that moment, not
the completed figures. Observed on 17 August 2026 with SDK 0.2.139: a message
carrying 335 characters of text reported `output_tokens` of 1, and
`stop_reason` was None on every streamed message in the run. Summing across the
messages of one call does not recover the total either, 29 plus 1 against a
`ResultMessage` total of 167. `ResultMessage.usage["iterations"]` holds a single
entry for a multi-call session, so it is not a per-turn breakdown.

The Claude Code CLI persists each assistant message to its transcript once the
message is complete, with the final usage and stop reason. The transcript path
is handed to every hook as `transcript_path`, so the lab captures it there and
reads the completed record back at the moment a turn is flushed.

This is a dependency on an artefact of the CLI rather than on a documented SDK
surface, so it is defended two ways. A format change shows up as a lookup miss,
never as a wrong number: a miss emits null and is counted. The count of
enriched and missed turns goes into the run manifest, where a capture that
started missing is visible rather than silent.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CompletedTurn:
    """The persisted record of one finished model call."""

    message_id: str
    usage: dict[str, Any]
    stop_reason: str | None

    @property
    def output_tokens(self) -> int | None:
        value = self.usage.get("output_tokens")
        return int(value) if value is not None else None

    @property
    def input_tokens_total(self) -> int | None:
        """Uncached, cache creation and cache read added together.

        The same measure `lab.agent.total_input_tokens` computes from the
        streamed usage, so the two sources stay comparable.
        """
        if not self.usage:
            return None
        return (
            int(self.usage.get("input_tokens", 0) or 0)
            + int(self.usage.get("cache_creation_input_tokens", 0) or 0)
            + int(self.usage.get("cache_read_input_tokens", 0) or 0)
        )


def read_completed_turns(path: Path) -> dict[str, CompletedTurn]:
    """Every completed assistant message in a transcript, keyed by message id.

    A malformed or half-written line is skipped rather than raised on. The
    transcript is being appended to by another process while this runs, so a
    partial final line is expected rather than exceptional.
    """
    turns: dict[str, CompletedTurn] = {}
    if not path or not path.is_file():
        return turns

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return turns

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or record.get("type") != "assistant":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        message_id = message.get("id")
        if not message_id:
            continue
        turns[str(message_id)] = CompletedTurn(
            message_id=str(message_id),
            usage=dict(message.get("usage") or {}),
            stop_reason=message.get("stop_reason"),
        )
    return turns


def await_completed_turn(
    path: Path | None,
    message_id: str | None,
    attempts: int = 6,
    delay: float = 0.25,
) -> CompletedTurn | None:
    """Look a message up, allowing for the CLI not having flushed it yet.

    Bounded: at the default settings this waits at most 1.5 seconds before
    giving up and letting the caller emit nulls.
    """
    if not path or not message_id:
        return None
    for attempt in range(attempts):
        found = read_completed_turns(path).get(message_id)
        if found is not None:
            return found
        if attempt < attempts - 1:
            time.sleep(delay)
    return None
