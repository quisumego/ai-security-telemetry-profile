"""The figure ledger: every figure the published documents quote, and its source.

Ruled at M8 (spec/rulings.py, rulings 9 and 10). spec/figures.yaml lists each
figure with the committed file it comes from, the key or keys it is read from,
and, for a derived figure, the formula. tests/test_spec.py resolves every entry
against its source, checks that each quoted text is in the documents that quote
it, and sweeps those documents for any number that is neither in the ledger nor
an identifier of an allowed form.

Key paths: dots separate keys, `['a.b']` is a key that itself contains dots,
`[n]` indexes a list, and `[k=v]` picks the item of a list whose key k equals v. Formulas are Python expressions over the named
inputs and the helpers below, with no other builtins.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from lab.config import REPO_ROOT
from spec import rulings

LEDGER = REPO_ROOT / rulings.LEDGER
ALLOWED_SOURCE = re.compile(r"^(results/[\w.-]+\.json|schema/fields\.yaml|siem/sentinel/[\w.-]+\.json)$")
WORDS = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty").split()

_PART = re.compile(r"([^.\[\]]+)|\[(\d+)\]|\['([^']+)'\]|\[([^=\]]+)=([^\]]+)\]")


def load() -> list[dict[str, Any]]:
    return yaml.safe_load(LEDGER.read_text(encoding="utf-8"))["figures"]


def source(path: str) -> Any:
    text = (REPO_ROOT / path).read_text(encoding="utf-8")
    return yaml.safe_load(text) if path.endswith(".yaml") else json.loads(text)


def resolve(doc: Any, keypath: str) -> Any:
    value = doc
    for name, index, quoted_key, key, wanted in _PART.findall(keypath):
        if name:
            value = value[name]
        elif quoted_key:
            value = value[quoted_key]
        elif index:
            value = value[int(index)]
        else:
            matches = [item for item in value if str(item.get(key)) == wanted]
            if len(matches) != 1:
                raise KeyError(f"{keypath}: [{key}={wanted}] matches {len(matches)} items")
            value = matches[0]
    return value


def _count(container: Any, key: str, wanted: Any) -> int:
    items = container.values() if isinstance(container, dict) else container
    return sum(1 for item in items if item.get(key) == wanted)


HELPERS = {
    "len": len, "sum": sum, "round": round, "min": min, "max": max, "abs": abs,
    "sorted": sorted, "set": set, "all": all, "any": any,
    "count": _count,
    "words": lambda n: WORDS[n],
}


def evaluate(entry: dict[str, Any]) -> dict[str, Any]:
    """Every named value of an entry: its inputs, then its computed values."""
    doc = source(entry["source"])
    names: dict[str, Any] = {k: resolve(doc, p) for k, p in (entry.get("inputs") or {}).items()}
    for name, expr in (entry.get("compute") or {}).items():
        names[name] = eval(expr, {"__builtins__": {}, **HELPERS, **names})  # noqa: S307
    return names


def rendered(entry: dict[str, Any]) -> str:
    return entry["render"].format(**evaluate(entry))


def check_holds(entry: dict[str, Any]) -> bool:
    if "check" not in entry:
        return True
    return bool(eval(entry["check"], {"__builtins__": {}, **HELPERS, **evaluate(entry)}))  # noqa: S307


# ---------------------------------------------------------- the number sweep --

GENERATED = re.compile(r"<!-- generated:(\w+) -->.*?<!-- /generated:\1 -->", re.S)
FENCED = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`]+`")
LINK_TARGET = re.compile(r"\]\([^)\s]*\)")
URL = re.compile(r"(?:https?://)?(?:[\w-]+\.)+(?:com|org|net|uk|ai|io|dev)(?:/\S*)?")
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_S = r"\s+"

# Identifiers that carry digits and are not figures. Each is a form, not a value.
IDENTIFIER_FORMS = [
    rf"\b\d{{1,2}}{_S}(?:{MONTHS}){_S}\d{{4}}\b",              # a date
    rf"\b(?:{MONTHS}){_S}\d{{4}}\b",                            # a month
    rf"\b\d{{1,2}}(?={_S}(?:and|or){_S}\d{{1,2}}{_S}(?:{MONTHS}))",  # "22 or 23 September"
    r"\b\d{4}-\d{2}(?:-\d{2})?\b",                          # an ISO date, or a year and month
    r"\b(?:19|20)\d{2}\b",                                    # a year
    r"\bLLM\d{2}:\d{4}\b",                                   # an OWASP identifier
    rf"\bTop{_S}10\b",                                         # the OWASP list's name
    r"\bAML\.T\d{4}(?:\.\d{3})?\b",                          # a MITRE ATLAS technique
    r"\b\d+\.\d+\.\d+(?:-\d+)?\b",                           # a version, or an ETSI provision
    r"\b[Vv]\d+\.\d+\.\d+\b",                                # a version
    rf"\bversion{_S}\d+\.\d+\b",                              # a document version
    r"\b\d{4}\.\d{2}\b",                                     # an ATLAS data version
    r"\bA(?:10|[1-9])\b",                                     # an attack class
    r"\bb[1-4]\b",                                            # a benign task type
    r"\bm\d+b?-[a-z]\d+(?:-t\d+)?\b",                         # a session or trial identifier
    r"\bd-a\d{2}\b",                                          # a detector
    r"\bM\d+b?\b",                                            # a stage
    rf"\bSections?{_S}\d+(?:\.\d+)?(?:{_S}(?:and|to){_S}\d+(?:\.\d+)?)?\b",  # a section
    r"#+ \d+(?:\.\d+)*\.?(?= )",                                # a numbered heading
    rf"\bPrinciple{_S}\d+\b", rf"\b[Cc]lause{_S}\d+(?:\.\d+)*\b",
    rf"\b[Rr]ulings?{_S}\d+(?:{_S}(?:to|and){_S}\d+)?\b",
    rf"\bRFC{_S}\d+\b", r"\bUTF-8\b", r"\bgranite4\.1:3b\b", r"\bclaude-haiku-4-5\b",
    rf"\bTS{_S}104{_S}223\b", rf"\bEN{_S}304{_S}223\b",
]
IDENTIFIER = re.compile("|".join(f"(?:{f})" for f in IDENTIFIER_FORMS))
NUMBER = re.compile(r"(?<![\w.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:\^\d+)?")


def normalised(text: str) -> str:
    """One line, single spaces, blockquote markers gone, so a figure or an
    identifier that wraps across lines reads as written."""
    return re.sub(r"\s+", " ", re.sub(r"\n>[ ]?", "\n", text)).strip()


def prose(path: str) -> str:
    """A published document as the sweep reads it: generated blocks and fenced
    code removed, then normalised."""
    text = (REPO_ROOT / path).read_text(encoding="utf-8")
    for pattern in (GENERATED, FENCED):
        text = pattern.sub(" ", text)
    return normalised(text)


def strip_for_sweep(text: str, quoted: list[str]) -> str:
    """Remove what the sweep does not judge: inline code, links, the ledger's own
    quoted figures, and the identifier forms above."""
    for pattern in (INLINE, LINK_TARGET, URL):
        text = pattern.sub(" ", text)
    for q in sorted(set(quoted), key=len, reverse=True):
        text = text.replace(q, " ")
    return IDENTIFIER.sub(" ", text)


def unaccounted(path: str, quoted: list[str]) -> list[str]:
    text = strip_for_sweep(prose(path), quoted)
    return [f"{path}: {m.group(0)!r} in {text[max(0, m.start() - 60):m.end() + 40]!r}"
            for m in NUMBER.finditer(text)]


# --------------------------------------------------------------- the hashes --

HEX = re.compile(r"(?<![0-9A-Za-z_-])[0-9a-f]{7,40}(?![0-9A-Za-z_-])")
# Hex identifiers a published document cites that are not commits of this
# repository, each with what it is.
NOT_COMMITS = {
    "5ae2e5c0": "the corpus.digest the manifests record",
    "65bb7f2a": "the corpus.digest a fresh clone computes",
}


def cited_hashes(path: str) -> list[str]:
    text = (REPO_ROOT / path).read_text(encoding="utf-8")
    return [h for h in HEX.findall(text) if re.search(r"\d", h) and re.search(r"[a-f]", h)]
