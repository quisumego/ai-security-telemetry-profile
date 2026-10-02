"""SPEC.md, README.md and the write-up, held to the results and to the M8 rulings.

Ruled at M8 (spec/rulings.py). SPEC.md's generated blocks must be what a fresh
render writes. Every figure the three published documents quote must be in the
figure ledger, resolve against its committed source, and appear where the
ledger says. No document a reader opens cites a commit ID, except the two the
methodology points to in the build log. The A9 holdout result never appears without its exposure, and
the headline leads where ruling 7 says it does.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from lab.config import REPO_ROOT
from spec import ledger, render, rulings

DOCS = rulings.PUBLIC_DOCUMENTS
ENTRIES = ledger.load()


def _text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


# ------------------------------------------------------------ SPEC.md render --
def test_spec_md_is_what_a_fresh_render_writes():
    assert render.render_doc(_text(rulings.SPEC)) == _text(rulings.SPEC)


def test_spec_md_keeps_the_nine_sections_fixed_at_m0():
    headings = re.findall(r"^## (\d)\. ", _text(rulings.SPEC), re.M)
    assert headings == [str(n) for n in range(1, 10)]


# ------------------------------------------------------------- the ledger --
def test_ledger_ids_are_unique():
    ids = [e["id"] for e in ENTRIES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("entry", ENTRIES, ids=[e["id"] for e in ENTRIES])
def test_every_entry_reads_a_committed_result_file(entry):
    assert ledger.ALLOWED_SOURCE.match(entry["source"]), entry["source"]
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", entry["source"]],
                             cwd=REPO_ROOT, capture_output=True)
    assert tracked.returncode == 0, f"{entry['source']} is not committed"
    for path in (entry.get("inputs") or {}).values():
        assert not any(f"{entry['source']}:{path}".startswith(k) for k in rulings.FORBIDDEN_SOURCE_KEYS), path


@pytest.mark.parametrize("entry", ENTRIES, ids=[e["id"] for e in ENTRIES])
def test_every_entry_renders_its_quoted_text_from_its_source(entry):
    assert ledger.rendered(entry) == entry["quoted"]
    assert ledger.check_holds(entry), f"{entry['id']}: its check does not hold"


@pytest.mark.parametrize("entry", ENTRIES, ids=[e["id"] for e in ENTRIES])
def test_every_quoted_figure_is_where_the_ledger_says(entry):
    assert entry["in"] and set(entry["in"]) <= set(DOCS)
    for doc in entry["in"]:
        assert entry["quoted"] in ledger.prose(doc), f"{entry['quoted']!r} is not in {doc}"


@pytest.mark.parametrize("doc", DOCS)
def test_every_number_in_a_published_document_is_in_the_ledger(doc):
    quoted = [e["quoted"] for e in ENTRIES if doc in e["in"]]
    assert ledger.unaccounted(doc, quoted) == []


def test_the_sweep_would_catch_a_figure_typed_by_hand():
    text = ledger.strip_for_sweep("The attack corpus scored 33/100.", [])
    assert ledger.NUMBER.findall(text) == ["33", "100"]


# ------------------------------------------------------------- the hashes --
# Ruled on 3 October 2026: no document a reader opens cites a commit ID, except
# the two the frozen methodology points to, named at the end of the build log.
READER_DOCS = tuple(sorted(set(DOCS) | {p.relative_to(REPO_ROOT).as_posix()
                                        for p in (REPO_ROOT / "docs").glob("*.md")}))
POINTED_TO_BY_THE_METHODOLOGY = {"docs/build-log.md": ("c8b28dd", "c353533")}


@pytest.mark.parametrize("doc", READER_DOCS)
def test_no_document_a_reader_opens_cites_a_commit_id(doc):
    allowed = POINTED_TO_BY_THE_METHODOLOGY.get(doc, ())
    assert [h for h in ledger.cited_hashes(doc) if h not in allowed] == []


def test_the_commits_the_methodology_points_to_are_commits_here():
    for h in POINTED_TO_BY_THE_METHODOLOGY["docs/build-log.md"]:
        assert h in ledger.cited_hashes("docs/build-log.md"), h
        found = subprocess.run(["git", "cat-file", "-e", f"{h}^{{commit}}"], cwd=REPO_ROOT, capture_output=True)
        assert found.returncode == 0, f"{h} is not a commit of this repository"


# ------------------------------------------------------------ the A9 rule --
A9 = re.compile(r"\bA9\b")
A9_RESULT = re.compile(r"\bd-a03\b|\bcaught\b|\bcatch(?:es)?\b|generalis|transfer|held-out")


def _paragraphs(text: str) -> list[str]:
    """Blank-line separated blocks, a table joined to the paragraph under it."""
    blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
    out, i = [], 0
    while i < len(blocks):
        block = blocks[i]
        if block.lstrip().startswith("|") and i + 1 < len(blocks):
            block, i = block + "\n" + blocks[i + 1], i + 1
        out.append(ledger.normalised(block))
        i += 1
    return out


@pytest.mark.parametrize("doc", DOCS)
def test_the_a9_holdout_result_never_appears_without_its_exposure(doc):
    for paragraph in _paragraphs(_text(doc)):
        if A9.search(paragraph) and A9_RESULT.search(paragraph):
            missing = [p for p in rulings.A9_EXPOSURE_PHRASES if p not in paragraph]
            assert not missing, f"{doc}: {paragraph[:80]!r} quotes the A9 result without {missing}"


def test_the_a9_rule_has_something_to_hold_in_spec_md():
    hits = [p for p in _paragraphs(_text(rulings.SPEC)) if A9.search(p) and A9_RESULT.search(p)]
    assert len(hits) >= 2


# ------------------------------------------------------- where the headline leads --
def _lead_ok(text: str) -> None:
    assert "undertested" in text and "weakened" in text
    assert text.index("undertested") < text.index("weakened")
    assert "refuted" in text


def test_spec_md_leads_with_the_headline_above_section_1_and_at_section_3():
    text = ledger.normalised(_text(rulings.SPEC))
    _lead_ok(text[: text.index("## 1. ")])
    section_3 = text[text.index("## 3. "): text.index("### 3.1")]
    _lead_ok(section_3)
    assert "baseline was known" in section_3


def test_readme_leads_with_the_result():
    text = _text("README.md")
    first = re.findall(r"^## (.+)$", text, re.M)[0]
    assert first == "The result"
    section = ledger.normalised(text.split("## The result", 1)[1].split("\n## ", 1)[0])
    _lead_ok(section)
    assert "baseline was known" in section


def test_the_write_up_leads_with_the_headline():
    text = _text(rulings.WRITE_UP)
    title, subtitle = text.splitlines()[0], text.splitlines()[2]
    assert title == f"# {rulings.TITLE}"
    assert subtitle == f"*{rulings.SUBTITLE}*"
    words = re.findall(r"\S+", ledger.normalised(text.split("\n", 3)[3]))
    _lead_ok(" ".join(words[:200]))
    assert "undertested" in " ".join(words[:150]) and "weakened" in " ".join(words[:150])
    assert "baseline was known" in text


def test_the_write_up_fits_medium_and_the_ruled_length():
    text = _text(rulings.WRITE_UP)
    assert not [line for line in text.splitlines() if line.lstrip().startswith("|")]
    low, high = rulings.WORDS
    assert low <= len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'.:_/-]*", text)) <= high
