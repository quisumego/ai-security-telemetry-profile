"""Load lab/config.yaml.

Every value that could change a capture lives in the YAML rather than in code,
so the run manifest can record the configuration that produced a session and a
reader can tie the two together.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "lab" / "config.yaml"
CANARY_REGISTER_PATH = REPO_ROOT / "lab" / "canary_register.yaml"
CLAIMS_PATH = REPO_ROOT / "lab" / "claims.yaml"
CORPUS_DIR = REPO_ROOT / "lab" / "corpus"
SCHEMA_PATH = REPO_ROOT / "schema" / "event.schema.json"
REGISTER_PATH = REPO_ROOT / "schema" / "fields.yaml"


@dataclass(frozen=True)
class LabConfig:
    """The lab agent's configuration, read once and passed around."""

    raw: dict[str, Any]
    path: Path

    # ------------------------------------------------------------- versions --
    @property
    def config_version(self) -> str:
        return str(self.raw["config_version"])

    @property
    def astp_version(self) -> str:
        return str(self.raw["astp_version"])

    @property
    def policy_version(self) -> str:
        return str(self.raw["policy"]["version"])

    @property
    def system_prompt_version(self) -> str:
        return str(self.raw["system_prompt_version"])

    # ---------------------------------------------------------------- model --
    @property
    def model_id(self) -> str:
        return str(self.raw["model"]["id"])

    @property
    def fallback_model(self) -> str | None:
        """Must be None. A fallback firing mid-capture would run some sessions
        on a different model and break the pinned-model guarantee."""
        return self.raw["model"]["fallback_model"]

    @property
    def thinking(self) -> str:
        return str(self.raw["model"]["thinking"])

    @property
    def max_turns(self) -> int:
        return int(self.raw["model"]["max_turns"])

    @property
    def max_budget_usd(self) -> float:
        return float(self.raw["model"]["max_budget_usd"])

    # -------------------------------------------------------------- session --
    @property
    def user_id(self) -> str:
        return str(self.raw["session"]["user_id"])

    @property
    def tenant_id(self) -> str:
        return str(self.raw["session"]["tenant_id"])

    @property
    def client_app(self) -> str:
        return str(self.raw["session"]["client_app"])

    @property
    def agent_id(self) -> str:
        return str(self.raw["session"]["agent_id"])

    @property
    def caller_scope(self) -> str:
        return str(self.raw["session"]["caller_scope"])

    # --------------------------------------------------------------- policy --
    @property
    def scope_order(self) -> list[str]:
        return list(self.raw["policy"]["scope_order"])

    @property
    def email_allow_domains(self) -> list[str]:
        return list(self.raw["policy"]["egress"]["email_allow_domains"])

    @property
    def url_allow_hosts(self) -> list[str]:
        return list(self.raw["policy"]["egress"]["url_allow_hosts"])

    @property
    def case_file_root(self) -> Path:
        return REPO_ROOT / str(self.raw["policy"]["case_file_root"])

    # ------------------------------------------------------------ retrieval --
    @property
    def default_top_k(self) -> int:
        return int(self.raw["retrieval"]["default_top_k"])

    @property
    def max_top_k(self) -> int:
        return int(self.raw["retrieval"]["max_top_k"])

    @property
    def chunk_words(self) -> int:
        return int(self.raw["retrieval"]["chunk_words"])

    @property
    def chunk_overlap_words(self) -> int:
        return int(self.raw["retrieval"]["chunk_overlap_words"])

    # -------------------------------------------------------- system prompt --
    @property
    def system_prompt(self) -> str:
        return str(self.raw["system_prompt"])

    def scopes_readable_by(self, caller_scope: str) -> list[str]:
        """A caller may read its own scope and everything below it.

        Scope order runs least open to most open, so the caller's own position
        in the list is the ceiling.
        """
        order = self.scope_order
        if caller_scope not in order:
            return []
        return order[: order.index(caller_scope) + 1]


def load_config(path: Path = CONFIG_PATH) -> LabConfig:
    with path.open(encoding="utf-8") as fh:
        return LabConfig(raw=yaml.safe_load(fh), path=path)


def load_canary_values(path: Path = CANARY_REGISTER_PATH) -> list[str]:
    """The planted canary values, read from the register outside the corpus."""
    with path.open(encoding="utf-8") as fh:
        register = yaml.safe_load(fh)
    return [str(entry["value"]) for entry in register["canaries"]]


def load_claims(path: Path = CLAIMS_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return list(yaml.safe_load(fh)["claims"])
