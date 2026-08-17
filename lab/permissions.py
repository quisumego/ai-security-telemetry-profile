"""The lab's own authorisation policy.

The Agent SDK's permission system is not used to make these decisions. Tools
listed in `allowed_tools` are auto-approved and never produce a decision record,
and `can_use_tool` is not invoked for calls that are already permitted. The
field register requires `action.permission_decision` on **every** tool call
including the permitted ones, because a tool used outside its intended task
looks identical to legitimate use unless the decision is logged. Logging only
denials hides the case that matters, which is the harmful action that was
allowed.

So the policy is evaluated here, in the PreToolUse hook, for every call.

Three of the four outcomes are used:

  allowed        the policy authorises the call outright
  denied         the policy refuses it, and the hook blocks it
  escalated      the policy cannot authorise it automatically and refers it.
                 In this lab a referral proceeds, because a lab that blocked
                 every outbound call would produce no telemetry worth
                 detecting. The referral is what gets recorded.
  not_evaluated  a tool arrived that the policy has no rule for. This should
                 not happen with six known tools and is a fault indicator.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ALLOWED = "allowed"
DENIED = "denied"
ESCALATED = "escalated"
NOT_EVALUATED = "not_evaluated"

MCP_PREFIX = "mcp__thornfield__"


def bare_tool_name(tool_name: str) -> str:
    """Strip the MCP server prefix the SDK puts on in-process tool names."""
    return tool_name[len(MCP_PREFIX) :] if tool_name.startswith(MCP_PREFIX) else tool_name


@dataclass(frozen=True)
class Decision:
    decision: str
    reason: str | None
    egress_target: str | None


def normalise_email_target(address: str) -> str:
    """A recipient address as a comparable target.

    The local part is kept because it has forensic value, and the domain is
    kept separable so a detector can compare it against an allow list without
    parsing free-form tool arguments.
    """
    return f"mailto:{address.strip().lower()}"


def normalise_url_target(url: str) -> str:
    """A URL with the scheme and host lowercased, everything else untouched.

    The query string is deliberately preserved. A staged exfiltration chain
    encodes its payload into the query, so stripping it would remove the whole
    of what the field exists to capture.
    """
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()
    rest = url.strip()[len(parsed.scheme) + 3 + len(parsed.netloc) :]
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{rest}"


def email_domain(address: str) -> str:
    _, _, domain = address.strip().lower().partition("@")
    return domain


@dataclass
class PermissionPolicy:
    email_allow_domains: list[str]
    url_allow_hosts: list[str]
    case_file_root: Path
    note_root: Path

    def decide(self, tool_name: str, tool_input: dict[str, Any]) -> Decision:
        name = bare_tool_name(tool_name)
        handler = {
            "search_documents": self._read_only,
            "lookup_claim": self._read_only,
            "read_case_file": self._read_case_file,
            "write_case_note": self._write_case_note,
            "send_email": self._send_email,
            "fetch_url": self._fetch_url,
        }.get(name)
        if handler is None:
            return Decision(
                NOT_EVALUATED,
                f"no policy rule exists for tool {name!r}",
                None,
            )
        return handler(tool_input)

    # ------------------------------------------------------------- handlers --
    def _read_only(self, _: dict[str, Any]) -> Decision:
        return Decision(ALLOWED, None, None)

    def _read_case_file(self, tool_input: dict[str, Any]) -> Decision:
        path = str(tool_input.get("path", ""))
        if not self._inside(self.case_file_root, path):
            return Decision(
                DENIED,
                f"path {path!r} resolves outside the case file root",
                None,
            )
        return Decision(ALLOWED, None, None)

    def _write_case_note(self, tool_input: dict[str, Any]) -> Decision:
        path = str(tool_input.get("path", ""))
        if not self._inside(self.note_root, path):
            return Decision(
                DENIED,
                f"path {path!r} resolves outside the case note root",
                None,
            )
        return Decision(ALLOWED, None, None)

    def _send_email(self, tool_input: dict[str, Any]) -> Decision:
        address = str(tool_input.get("to", ""))
        target = normalise_email_target(address)
        domain = email_domain(address)
        if domain and domain in self.email_allow_domains:
            return Decision(ALLOWED, None, target)
        return Decision(
            ESCALATED,
            f"recipient domain {domain!r} is not on the internal allow list",
            target,
        )

    def _fetch_url(self, tool_input: dict[str, Any]) -> Decision:
        url = str(tool_input.get("url", ""))
        target = normalise_url_target(url)
        host = (urlparse(url.strip()).hostname or "").lower()
        if host and host in self.url_allow_hosts:
            return Decision(ALLOWED, None, target)
        return Decision(
            ESCALATED,
            f"host {host!r} is not on the internal allow list",
            target,
        )

    # ---------------------------------------------------------------- paths --
    @staticmethod
    def _inside(root: Path, candidate: str) -> bool:
        """True where candidate resolves inside root.

        Resolution happens before the comparison, so `../` sequences and
        symbolic links cannot walk out of the root by spelling.
        """
        if not candidate:
            return False
        try:
            resolved = (root / candidate).resolve()
            return resolved == root.resolve() or root.resolve() in resolved.parents
        except (OSError, ValueError):
            return False
