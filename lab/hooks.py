"""Hook callbacks, the tool-call emission point.

Verified against live documentation and against the installed SDK on 17 August
2026. The Python SDK's `HookEvent` type admits these callback hooks:

    PreToolUse, PostToolUse, PostToolUseFailure, UserPromptSubmit, Stop,
    SubagentStart, SubagentStop, PreCompact, Notification, PermissionRequest

**`SessionStart` and `SessionEnd` are not among them.** The documentation states
that they can be registered as SDK callback hooks in TypeScript but are omitted
from the Python SDK's `HookEvent` type, and in Python are reachable only as
shell command hooks in a settings file. The lab runs with `setting_sources=[]`
so that no personal or project configuration reaches the instrument, which rules
that route out as well.

So the session lifecycle events are emitted by the harness in lab/agent.py
rather than by a hook. The same applies to turn events: no hook carries token
counts, which arrive on `AssistantMessage.usage` in the message stream. This is
a departure from the wording of the project plan and is recorded as such in
docs/build-log.md.

What the hooks do carry is every tool call, including the calls the policy
refuses, which is where `action.permission_decision` comes from.
"""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import HookContext, HookMatcher

from lab.permissions import DENIED
from lab.session import LabSession, sha256
from lab.telemetry import contains_canary


def _result_text(tool_response: Any) -> str:
    """Flatten a tool response to text for hashing and sizing."""
    if tool_response is None:
        return ""
    if isinstance(tool_response, str):
        return tool_response
    return json.dumps(tool_response, ensure_ascii=False, default=str)


def build_hooks(session: LabSession) -> dict[str, list[HookMatcher]]:
    """Build the hook table for one session."""

    async def on_user_prompt_submit(
        input_data: Any, tool_use_id: str | None, context: HookContext
    ) -> dict[str, Any]:
        """Records the instruction that drove the session.

        The harness knows the prompt it passed in, but taking it from the hook
        means the log records what the agent actually received.
        """
        session.user_prompt = str(input_data.get("prompt", ""))
        return {}

    async def on_pre_tool_use(
        input_data: Any, tool_use_id: str | None, context: HookContext
    ) -> dict[str, Any]:
        tool_name = str(input_data.get("tool_name", ""))
        tool_input = dict(input_data.get("tool_input") or {})

        decision = session.policy.decide(tool_name, tool_input)
        if tool_use_id:
            session.decisions[tool_use_id] = decision
        session.tool_calls += 1

        # context_document_ids is a snapshot taken *before* this call runs, so
        # it records what was in the model's context at the moment the call was
        # made. Material this call is about to bring in belongs to the tool_post
        # event, not to this one.
        session.emitter.emit(
            "tool_pre",
            turn=session.turn_block(),
            action={
                "tool_name": tool_name,
                "tool_arguments": tool_input,
                "result_hash": None,
                "result_bytes": None,
                "permission_decision": decision.decision,
                "egress_target": decision.egress_target,
                "context_document_ids": list(session.context_document_ids),
            },
            canary_triggered=contains_canary(tool_input, session.canaries),
            block_reason=decision.reason,
        )

        if decision.decision == DENIED:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": decision.reason or "refused by policy",
                }
            }
        return {}

    async def on_post_tool_use(
        input_data: Any, tool_use_id: str | None, context: HookContext
    ) -> dict[str, Any]:
        tool_name = str(input_data.get("tool_name", ""))
        tool_input = dict(input_data.get("tool_input") or {})
        response = input_data.get("tool_response")
        body = _result_text(response)

        decision = session.decisions.get(tool_use_id or "")
        session.emitter.emit(
            "tool_post",
            turn=session.turn_block(),
            action={
                "tool_name": tool_name,
                "tool_arguments": tool_input,
                "result_hash": sha256(body),
                "result_bytes": len(body.encode("utf-8")),
                "permission_decision": decision.decision if decision else "not_evaluated",
                "egress_target": decision.egress_target if decision else None,
                # Taken after the call, so anything this tool pulled into
                # context is included. The difference between this list and the
                # one on the matching tool_pre event is what the call added.
                "context_document_ids": list(session.context_document_ids),
            },
            canary_triggered=contains_canary(body, session.canaries)
            or contains_canary(tool_input, session.canaries),
            block_reason=decision.reason if decision else None,
        )
        return {}

    async def on_post_tool_use_failure(
        input_data: Any, tool_use_id: str | None, context: HookContext
    ) -> dict[str, Any]:
        """A tool that raised, or that the policy blocked at PreToolUse.

        Logged as a tool_post with no result, so a refused call is visible in
        the same place as a completed one rather than only as a gap.
        """
        tool_name = str(input_data.get("tool_name", ""))
        tool_input = dict(input_data.get("tool_input") or {})
        error = str(input_data.get("error", ""))
        decision = session.decisions.get(tool_use_id or "")

        session.emitter.emit(
            "tool_post",
            turn=session.turn_block(),
            action={
                "tool_name": tool_name,
                "tool_arguments": tool_input,
                "result_hash": None,
                "result_bytes": 0,
                "permission_decision": decision.decision if decision else "not_evaluated",
                "egress_target": decision.egress_target if decision else None,
                "context_document_ids": list(session.context_document_ids),
            },
            canary_triggered=contains_canary(tool_input, session.canaries),
            block_reason=(decision.reason if decision else None) or error or None,
        )
        return {}

    return {
        "UserPromptSubmit": [HookMatcher(hooks=[on_user_prompt_submit])],
        "PreToolUse": [HookMatcher(hooks=[on_pre_tool_use])],
        "PostToolUse": [HookMatcher(hooks=[on_post_tool_use])],
        "PostToolUseFailure": [HookMatcher(hooks=[on_post_tool_use_failure])],
    }
