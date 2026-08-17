"""Per-session state, and the emission points that depend on it.

The tools and the hooks are both built as closures over one `LabSession`, which
is what lets a tool call be logged with the retrieval context that preceded it.
That link is `action.context_document_ids`, the field the whole profile leans on
hardest, and it cannot be reconstructed after the fact from separate retrieval
and action logs.

What counts as being in context: anything a tool pulled into the conversation.
A retrieved chunk, a claim record, a case file, and a fetched page all qualify,
because from the model's point of view they are all material that arrived from
outside and is now available to act on.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lab.config import LabConfig
from lab.corpus_index import CorpusIndex, ScoredChunk
from lab.permissions import Decision, PermissionPolicy
from lab.telemetry import Emitter, contains_canary


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class LabSession:
    """State shared by the tools, the hooks and the harness for one session."""

    config: LabConfig
    index: CorpusIndex
    claims: dict[str, dict[str, Any]]
    emitter: Emitter
    policy: PermissionPolicy
    canaries: tuple[str, ...]
    note_root: Path

    turn_index: int = 0
    context_document_ids: list[str] = field(default_factory=list)
    decisions: dict[str, Decision] = field(default_factory=dict)
    user_prompt: str | None = None
    tool_calls: int = 0

    # Captured from any hook input. The completed per-turn token counts and
    # stop reason are read back from here, because the streamed
    # AssistantMessage carries pre-completion figures. See lab/transcript.py.
    transcript_path: Path | None = None
    turns_enriched: int = 0
    turns_unenriched: int = 0

    # ------------------------------------------------------------- context --
    def add_context_document(self, document_id: str) -> None:
        if document_id not in self.context_document_ids:
            self.context_document_ids.append(document_id)

    def turn_block(self) -> dict[str, Any]:
        """The minimal turn block carried on retrieval and action events.

        Only the index and the timestamp. It exists so a tool call can be tied
        to the model call that produced it, using registered fields rather than
        a correlation identifier the register does not define.
        """
        return {"index": self.turn_index, "timestamp": now_iso()}

    def permission_context(self, owners: list[tuple[str, str]]) -> dict[str, Any]:
        """Build `retrieval.permission_context` from (tenant, scope) pairs.

        Scopes are recorded tenant-qualified, as `tenant:scope`. Cross-tenant
        retrieval is a boundary crossing that a bare scope name cannot express:
        Pearson Hardman material is scoped `internal`, and a Thornfield claims
        handler may read Thornfield `internal` material, so an unqualified
        comparison would call that a match and A9 would be invisible. The
        qualified form makes the tenant part of the comparison, which is what
        the register means by the scope each returned document requires.

        `scope_match` is therefore false when either half fails: the wrong
        tenant, or a scope above the caller's ceiling within its own tenant.
        """
        readable = self.config.scopes_readable_by(self.config.caller_scope)
        return {
            "caller_scope": f"{self.config.tenant_id}:{self.config.caller_scope}",
            "document_scopes": [f"{tenant}:{scope}" for tenant, scope in owners],
            "scope_match": all(
                tenant == self.config.tenant_id and scope in readable
                for tenant, scope in owners
            ),
        }

    # ------------------------------------------------------ emission points --
    def emit_session_start(self) -> None:
        self.emitter.emit(
            "session_start",
            content={
                "prompt_text": None,
                "prompt_hash": None,
                "response_text": None,
                "response_hash": None,
                "system_prompt_version": self.config.system_prompt_version,
                "redaction_applied": False,
            },
        )

    def emit_session_end(self) -> None:
        self.emitter.emit("session_end")

    def emit_turn(
        self,
        *,
        model_id: str,
        model_version: str | None,
        tokens_in: int | None,
        tokens_out: int | None,
        latency: float | None,
        finish_reason: str | None,
        response_text: str,
    ) -> None:
        """One model call. Emitted from the message stream, not from a hook.

        No hook carries token counts. They arrive on `AssistantMessage.usage`,
        which is why the turn group is emitted by the harness rather than by
        `lab/hooks.py`.

        `content.prompt_text` carries the user instruction that drove the
        session. On turns after the first, the incremental input is the tool
        results, which are recorded on their own tool_post events rather than
        repeated here.
        """
        prompt = self.user_prompt or ""
        self.emitter.emit(
            "turn",
            turn={
                "index": self.turn_index,
                "timestamp": now_iso(),
                "model_id": model_id,
                "model_version": model_version,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency": latency,
                "finish_reason": finish_reason,
            },
            content={
                "prompt_text": prompt,
                "prompt_hash": sha256(prompt),
                "response_text": response_text,
                "response_hash": sha256(response_text),
                "system_prompt_version": self.config.system_prompt_version,
                "redaction_applied": False,
            },
            canary_triggered=contains_canary(response_text, self.canaries),
        )
        self.turn_index += 1

    def emit_retrieval_for_chunks(self, query: str, results: list[ScoredChunk]) -> None:
        """One event per returned chunk.

        Per chunk rather than per query, because `retrieval.source_provenance`
        is a single label and a query returns material of mixed provenance. The
        checklist requires provenance on every retrieved chunk, and one event
        per chunk is the only way to record that honestly.
        """
        for result in results:
            doc = result.document
            self.add_context_document(doc.id)
            self.emitter.emit(
                "retrieval",
                turn=self.turn_block(),
                retrieval={
                    "document_ids": [doc.id],
                    "chunk_ids": [result.chunk.id],
                    "scores": [result.score],
                    "query_text": query,
                    "source_provenance": doc.provenance,
                    "permission_context": self.permission_context([(doc.tenant, doc.scope)]),
                },
                canary_triggered=contains_canary(result.chunk.text, self.canaries),
            )

    def emit_retrieval_for_content(
        self,
        *,
        document_id: str,
        chunk_id: str,
        query: str,
        provenance: str,
        tenant: str,
        scope: str,
        text: str,
        score: float = 1.0,
    ) -> None:
        """A retrieval event for content that arrived other than by search.

        A claim record, a case file and a fetched page are all material that
        entered the model's context from outside, so each is logged with its own
        provenance and permission context. Without this, `fetch_url` would be
        the one way untrusted content could reach the model with no provenance
        label attached to it.
        """
        self.add_context_document(document_id)
        self.emitter.emit(
            "retrieval",
            turn=self.turn_block(),
            retrieval={
                "document_ids": [document_id],
                "chunk_ids": [chunk_id],
                "scores": [score],
                "query_text": query,
                "source_provenance": provenance,
                "permission_context": self.permission_context([(tenant, scope)]),
            },
            canary_triggered=contains_canary(text, self.canaries),
        )
