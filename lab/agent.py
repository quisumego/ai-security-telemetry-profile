"""The lab agent.

Builds the Claude Agent SDK options, runs one session, and emits the events no
hook can produce: session lifecycle, and turns with their token counts.

Three settings carry more weight than the rest.

**`model` is pinned and `fallback_model` is never set.** A fallback firing
part-way through a capture would silently run some sessions on a different model
and break the pinned-model guarantee the whole corpus rests on, with no visible
failure. The value is asserted to be None before the run starts rather than
trusted to stay that way.

**`setting_sources=[]`.** Left unset, the SDK loads all filesystem settings,
which for this repository would mean the owner's own `~/.claude/settings.json`,
any project settings, and this repository's `CLAUDE.md`, all pulled into the
lab agent's context. That would contaminate every capture and make none of them
reproducible on another machine.

**`tools=[]`.** No built-in tool exists in the session. The only capabilities
the agent has are the six in lab/tools/, so the telemetry describes the whole of
what the agent could do.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ThinkingConfigDisabled,
    query,
)

from lab.config import (
    CORPUS_DIR,
    REGISTER_PATH,
    SCHEMA_PATH,
    LabConfig,
    load_canary_values,
    load_claims,
    load_config,
)
from lab.corpus_index import CorpusIndex
from lab.hooks import build_hooks
from lab.permissions import PermissionPolicy
from lab.session import LabSession, now_iso
from lab.telemetry import Emitter, SessionIdentity, register_group_keys
from lab.transcript import await_completed_turn
from lab.tools import QUALIFIED_TOOL_NAMES, SERVER_NAME, build_tool_server


@dataclass
class SessionResult:
    """What one session produced, for the run manifest."""

    session_id: str
    events_path: Path
    events_written: int
    tool_calls: int
    turns: int
    subtype: str | None = None
    is_error: bool = False
    total_cost_usd: float | None = None
    usage: dict[str, Any] | None = None
    model_usage: dict[str, Any] | None = None
    final_text: str = ""
    stderr_lines: list[str] = field(default_factory=list)
    turns_enriched: int = 0
    turns_unenriched: int = 0
    transcript_path: str | None = None

    @property
    def models_seen(self) -> list[str]:
        return sorted((self.model_usage or {}).keys())

    def token_totals(self) -> dict[str, int]:
        """Token counts summed across every model key in model_usage.

        The primary record in the manifest, in preference to
        `total_cost_usd`, which the SDK documents as an estimate with stated
        accuracy caveats.
        """
        totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        }
        for entry in (self.model_usage or {}).values():
            totals["input_tokens"] += int(entry.get("inputTokens", 0) or 0)
            totals["output_tokens"] += int(entry.get("outputTokens", 0) or 0)
            totals["cache_read_input_tokens"] += int(entry.get("cacheReadInputTokens", 0) or 0)
            totals["cache_creation_input_tokens"] += int(
                entry.get("cacheCreationInputTokens", 0) or 0
            )
        return totals


def total_input_tokens(usage: dict[str, Any] | None) -> int | None:
    """Every token that went into the model call, cache included.

    A design decision taken before the first capture and recorded here rather
    than left implicit. The register says `turn.tokens_in` measures input
    volume, and names oversized injected content and unbounded consumption as
    what it is for. Under prompt caching the API's own `input_tokens` counts
    only the uncached remainder: the authentication probe on 17 August 2026
    reported `input_tokens` of 10 against 4,601 cache creation tokens for the
    same call. Recording 10 would make the field blind to exactly the thing it
    exists to detect.

    So the field carries the sum of the uncached, cache creation and cache read
    counts. This is wider than the OpenTelemetry `gen_ai.usage.input_tokens`
    attribute it maps to, and the difference is noted in schema/otel-mapping.md.
    """
    if not usage:
        return None
    return (
        int(usage.get("input_tokens", 0) or 0)
        + int(usage.get("cache_creation_input_tokens", 0) or 0)
        + int(usage.get("cache_read_input_tokens", 0) or 0)
    )


def _completed_figures(
    session: LabSession, message: AssistantMessage
) -> tuple[int | None, int | None, str | None]:
    """Completed tokens in, tokens out and finish reason for one model call.

    The streamed `AssistantMessage` arrives before the message has finished
    generating, so its `output_tokens` and `stop_reason` are pre-completion
    values and cannot be used. lab/transcript.py records the evidence. The
    completed record is read from the CLI transcript instead, and a lookup that
    misses emits null rather than a wrong number, counted on the session so the
    miss reaches the run manifest.
    """
    completed = await_completed_turn(session.transcript_path, message.message_id)
    if completed is None:
        session.turns_unenriched += 1
        return total_input_tokens(message.usage), None, None
    session.turns_enriched += 1
    return (
        completed.input_tokens_total or total_input_tokens(message.usage),
        completed.output_tokens,
        completed.stop_reason,
    )


def build_options(
    config: LabConfig,
    session: LabSession,
    server: Any,
    stderr_sink: list[str],
    thinking: str | None = None,
) -> ClaudeAgentOptions:
    """Build the SDK options for one session.

    `thinking` overrides `config.thinking` for this run only. It exists so the
    setting can be compared against itself under otherwise identical
    conditions, which is the only honest way to decide it. A scored capture
    passes None and takes the configured value, and the manifest records which
    value was in force.
    """
    if config.fallback_model is not None:
        raise ValueError(
            "fallback_model is set. It must stay null: a fallback firing "
            "mid-capture would run some sessions on a different model and "
            "break the pinned-model guarantee without any visible failure."
        )

    setting = thinking if thinking is not None else config.thinking
    thinking_config = (
        ThinkingConfigDisabled(type="disabled") if setting == "disabled" else None
    )

    options = ClaudeAgentOptions(
        model=config.model_id,
        tools=[],
        mcp_servers={SERVER_NAME: server},
        allowed_tools=list(QUALIFIED_TOOL_NAMES),
        setting_sources=[],
        system_prompt=config.system_prompt,
        max_turns=config.max_turns,
        max_budget_usd=config.max_budget_usd,
        hooks=build_hooks(session),
        stderr=stderr_sink.append,
    )
    if thinking_config is not None:
        options.thinking = thinking_config
    return options


def build_session(
    config: LabConfig,
    run_dir: Path,
    session_id: str,
    overlay_dirs: tuple[Path, ...] = (),
) -> LabSession:
    """Assemble the session state, the index, the policy and the emitter.

    `overlay_dirs` adds documents to this session's index without touching
    lab/corpus/, which stays the benign estate. M2 uses it to put scenario
    documents in front of the agent, so a poisoned document never enters the
    corpus the M3 benign sessions read.
    """
    index = CorpusIndex.build(
        CORPUS_DIR,
        chunk_words=config.chunk_words,
        overlap_words=config.chunk_overlap_words,
        overlay_dirs=overlay_dirs,
    )
    claims = {str(claim["reference"]): claim for claim in load_claims()}
    canaries = tuple(load_canary_values())

    note_root = run_dir / "notes"
    note_root.mkdir(parents=True, exist_ok=True)

    identity = SessionIdentity(
        id=session_id,
        start_time=now_iso(),
        user_id=config.user_id,
        tenant_id=config.tenant_id,
        client_app=config.client_app,
        agent_id=config.agent_id,
        config_version=config.config_version,
    )

    with SCHEMA_PATH.open(encoding="utf-8") as fh:
        schema = json.load(fh)

    emitter = Emitter(
        path=run_dir / f"session-{session_id}.jsonl",
        astp_version=config.astp_version,
        identity=identity,
        policy_version=config.policy_version,
        canaries=canaries,
        group_keys=register_group_keys(REGISTER_PATH),
        schema=schema,
    )

    policy = PermissionPolicy(
        email_allow_domains=config.email_allow_domains,
        url_allow_hosts=config.url_allow_hosts,
        case_file_root=config.case_file_root,
        note_root=note_root,
    )

    return LabSession(
        config=config,
        index=index,
        claims=claims,
        emitter=emitter,
        policy=policy,
        canaries=canaries,
        note_root=note_root,
    )


async def run_session(
    prompt: str,
    run_dir: Path,
    config: LabConfig | None = None,
    session_id: str | None = None,
    overlay_dirs: tuple[Path, ...] = (),
    thinking: str | None = None,
) -> SessionResult:
    """Run one session end to end and return what it produced."""
    config = config or load_config()
    session_id = session_id or f"s-{uuid.uuid4().hex[:12]}"
    run_dir.mkdir(parents=True, exist_ok=True)

    session = build_session(config, run_dir, session_id, overlay_dirs=overlay_dirs)
    stderr_sink: list[str] = []
    server = build_tool_server(session)
    options = build_options(config, session, server, stderr_sink, thinking=thinking)

    session.user_prompt = prompt
    session.emit_session_start()

    result_message: ResultMessage | None = None
    final_text = ""

    pending_key: Any = None
    pending_message: AssistantMessage | None = None
    pending_text: list[str] = []
    boundary = time.monotonic()

    def flush_turn() -> None:
        nonlocal pending_key, pending_message, pending_text, boundary, final_text
        if pending_message is None:
            return
        text = "".join(pending_text)
        if text.strip():
            final_text = text
        tokens_in, tokens_out, finish_reason = _completed_figures(session, pending_message)
        session.emit_turn(
            model_id=config.model_id,
            model_version=pending_message.model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency=round(time.monotonic() - boundary, 4),
            finish_reason=finish_reason,
            response_text=text,
        )
        boundary = time.monotonic()
        pending_key = None
        pending_message = None
        pending_text = []

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                # One AssistantMessage can arrive more than once for the same
                # model call, once per content block group. Deduplicating on
                # message_id keeps one turn event per call rather than one per
                # block, which would double count every token figure.
                key = message.message_id or id(message)
                if pending_key is not None and key != pending_key:
                    flush_turn()
                pending_key = key
                pending_message = message
                for block in message.content:
                    if isinstance(block, TextBlock):
                        pending_text.append(block.text)
            elif isinstance(message, ResultMessage):
                flush_turn()
                result_message = message
        flush_turn()
    finally:
        session.emit_session_end()
        session.emitter.close()

    return SessionResult(
        session_id=session_id,
        events_path=session.emitter.path,
        events_written=session.emitter.events_written,
        tool_calls=session.tool_calls,
        turns=session.turn_index,
        subtype=result_message.subtype if result_message else None,
        is_error=bool(result_message.is_error) if result_message else False,
        total_cost_usd=result_message.total_cost_usd if result_message else None,
        usage=result_message.usage if result_message else None,
        model_usage=result_message.model_usage if result_message else None,
        final_text=final_text,
        stderr_lines=stderr_sink,
        turns_enriched=session.turns_enriched,
        turns_unenriched=session.turns_unenriched,
        transcript_path=str(session.transcript_path) if session.transcript_path else None,
    )
