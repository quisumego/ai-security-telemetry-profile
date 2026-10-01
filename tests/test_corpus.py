"""The synthetic corpus, the claims table and the canary register.

These are the material every capture reads. A mistake here is a mistake in every
run taken afterwards, so the checks are structural rather than a spot read.
"""

from pathlib import Path

import pytest
import yaml

from lab.config import (
    CANARY_REGISTER_PATH,
    CLAIMS_PATH,
    CORPUS_DIR,
    REPO_ROOT,
    load_canary_values,
    load_claims,
    load_config,
)
from lab.corpus_index import CorpusIndex, parse_document

PROVENANCE_VALUES = {
    "internal_authored",
    "external_supplied",
    "user_supplied",
    "third_party_feed",
    "unknown",
}
TENANTS = {"thornfield-mutual", "pearson-hardman"}
CANARY_PATTERN = __import__("re").compile(r"^THN-[A-Z]{4}-[0-9a-f]{12}$")


@pytest.fixture(scope="module")
def documents():
    return [parse_document(p) for p in sorted(CORPUS_DIR.glob("*.md"))]


@pytest.fixture(scope="module")
def register():
    with CANARY_REGISTER_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------- documents --


def test_the_corpus_has_the_agreed_document_count(documents):
    assert len(documents) == 24


def test_every_document_declares_complete_front_matter(documents):
    for doc in documents:
        assert doc.id and doc.title and doc.doc_type
        assert doc.tenant in TENANTS, f"{doc.id} has tenant {doc.tenant!r}"
        assert doc.provenance in PROVENANCE_VALUES, f"{doc.id} has {doc.provenance!r}"
        assert doc.body.strip(), f"{doc.id} has an empty body"


def test_document_ids_are_unique_and_match_their_filename(documents):
    seen = set()
    for doc in documents:
        assert doc.id not in seen, f"duplicate document id {doc.id}"
        seen.add(doc.id)
        assert doc.path.stem == doc.id, f"{doc.path.name} does not match id {doc.id}"


def test_every_document_scope_is_in_the_configured_scope_order(documents):
    order = set(load_config().scope_order)
    for doc in documents:
        assert doc.scope in order, f"{doc.id} has unconfigured scope {doc.scope!r}"


def test_provenance_is_not_uniform(documents):
    """A field with one value everywhere cannot carry detection signal.

    The ablation is meant to test whether provenance is load-bearing. If every
    document were internally authored the answer would be decided by the corpus
    rather than by the measurement.
    """
    values = {doc.provenance for doc in documents}
    assert "internal_authored" in values
    assert "external_supplied" in values
    assert "unknown" in values, "the third state has no representative document"


def test_both_tenants_are_represented(documents):
    tenants = {doc.tenant for doc in documents}
    assert tenants == TENANTS


def test_material_exists_above_the_callers_scope_ceiling(documents):
    """Otherwise there is no boundary for A3 to cross and nothing to detect."""
    config = load_config()
    readable = set(config.scopes_readable_by(config.caller_scope))
    unreadable = [d for d in documents if d.tenant == config.tenant_id and d.scope not in readable]
    assert unreadable, "every document is inside the caller's scope"


# -------------------------------------------------------------------- index --


def test_the_index_builds_and_chunks_every_document(documents):
    config = load_config()
    index = CorpusIndex.build(CORPUS_DIR, config.chunk_words, config.chunk_overlap_words)
    assert len(index.documents) == len(documents)
    assert len(index.chunks) >= len(documents)
    for doc_id in index.documents:
        assert any(c.document_id == doc_id for c in index.chunks), f"{doc_id} produced no chunk"


def test_search_is_deterministic():
    config = load_config()
    index = CorpusIndex.build(CORPUS_DIR, config.chunk_words, config.chunk_overlap_words)
    first = [(r.chunk.id, r.score) for r in index.search("reserving guidance", 5)]
    second = [(r.chunk.id, r.score) for r in index.search("reserving guidance", 5)]
    assert first == second
    assert first, "a query drawn from the corpus returned nothing"


def test_the_index_does_not_filter_by_scope():
    """A deliberate property, checked so it cannot be lost by accident.

    An index that filtered correctly would make restricted disclosure and
    cross-tenant retrieval impossible to attempt, and the telemetry would have
    nothing to reveal.
    """
    config = load_config()
    index = CorpusIndex.build(CORPUS_DIR, config.chunk_words, config.chunk_overlap_words)
    results = index.search("solvency coverage ratio own funds", 5)
    assert any(r.document.scope == "finance_restricted" for r in results)


def test_the_index_never_reads_the_canary_register_or_the_claims_table():
    index = CorpusIndex.build(CORPUS_DIR)
    paths = {doc.path.resolve() for doc in index.documents.values()}
    assert CANARY_REGISTER_PATH.resolve() not in paths
    assert CLAIMS_PATH.resolve() not in paths


# ------------------------------------------------------------------- claims --


def test_the_claims_table_has_twelve_records_across_both_tenants():
    claims = load_claims()
    assert len(claims) == 12
    assert {c["tenant"] for c in claims} == TENANTS


def test_every_claim_reference_is_unique():
    references = [c["reference"] for c in load_claims()]
    assert len(references) == len(set(references))


def test_claim_references_used_in_the_corpus_resolve(documents):
    """A document that names a claim the lookup cannot find is a dead end."""
    known = {c["reference"] for c in load_claims()}
    for doc in documents:
        reference = doc.meta.get("claim_reference")
        if reference:
            assert reference in known, f"{doc.id} names unknown claim {reference}"


# ------------------------------------------------------------------ canaries --


def test_the_canary_register_lives_outside_the_corpus():
    """A detector must not be able to enumerate the canaries by retrieval."""
    assert CANARY_REGISTER_PATH.parent == CORPUS_DIR.parent
    assert CORPUS_DIR not in CANARY_REGISTER_PATH.parents


def test_there_are_eight_canaries_and_all_match_the_declared_pattern(register):
    values = load_canary_values()
    assert len(values) == 8
    assert len(set(values)) == 8
    for value in values:
        assert CANARY_PATTERN.match(value), f"{value} does not match the register pattern"


def test_every_canary_appears_exactly_where_the_register_says(register):
    for entry in register["canaries"]:
        target = REPO_ROOT / entry["planted_in"]
        assert target.is_file(), f"{entry['planted_in']} does not exist"
        assert entry["value"] in target.read_text(encoding="utf-8"), (
            f"{entry['value']} is not present in {entry['planted_in']}"
        )


# The source tree the canary placement test scans. Rescoped at M2, ruled by
# the owner on 21 September 2026: lab/ and attacks/ are source, and a canary in
# either outside its planted location would make an oracle ambiguous. runs/ is
# deliberately excluded, because a captured attack run contains canary values
# by design whenever an attack succeeds: that is what the oracle reads. The
# reason is recorded in docs/methodology.md Section 6.
CANARY_SCAN_GLOBS = (
    "lab/**/*.md",
    "lab/**/*.yaml",
    "lab/*.yaml",
    "attacks/**/*.md",
    "attacks/**/*.yaml",
    "attacks/**/*.py",
    "docs/**/*.md",
    # The detector package and its Sigma rules, added at M4. A detector that
    # matched a canary value would be keying on the attack design rather than
    # on behaviour, and a Sigma rule carrying one would publish the value.
    "detect/**/*.py",
    "detect/**/*.yml",
    "detect/**/*.yaml",
    "benign/**/*.py",
    # The ablation package and the generated results, added at M5 by the
    # owner's ruling of 22 September 2026. Results are meant to hold
    # identifiers and counts only, and this is what holds them to it.
    "ablation/**/*.py",
    "results/**/*.json",
    "results/**/*.md",
    # The volume model, added at M6 by the owner's ruling of 23 September
    # 2026. It reads every captured event, so it is held to the same rule.
    "cost/**/*.py",
    # The Sentinel generator and what it writes, added at M6 by the same
    # ruling. A rule query carrying a canary value would publish it.
    "siem/**/*.py",
    "siem/**/*.json",
    "siem/**/*.kql",
    # The vendor gap package, added at M7 by the owner's ruling of 23 September
    # 2026. Its passes read every captured event, and its evidence file is
    # published beside the doc.
    "vendor_gap/**/*.py",
    "vendor_gap/**/*.yaml",
    # The local model cross-check, added at M7b by the owner's ruling of 23
    # September 2026. Its runner and report read every captured event.
    "crosscheck/**/*.py",
    # The published documents, the demo tape, the M8 package and the tests,
    # added at M8 by the owner's ruling of 1 October 2026. SPEC.md and
    # README.md sit at the root, outside every glob above, and a test that
    # carried a registered value would plant it in a second file.
    "SPEC.md",
    "README.md",
    "docs/**/*.tape",
    "spec/**/*.py",
    "spec/**/*.yaml",
    "tests/**/*.py",
)


def test_no_canary_appears_anywhere_it_was_not_planted(register):
    """Catches a canary copied into a second file by accident.

    A canary in two places would make an exfiltration oracle ambiguous about
    which boundary was crossed, which is exactly what canaries exist to remove.
    In particular no scenario file, overlay document or oracle may carry a
    canary value: an attack prompt that contained the string it is meant to
    exfiltrate would score itself.
    """
    declared = {entry["value"]: REPO_ROOT / entry["planted_in"] for entry in register["canaries"]}
    scanned: list[Path] = []
    for pattern in CANARY_SCAN_GLOBS:
        scanned.extend(REPO_ROOT.glob(pattern))

    for path in scanned:
        if path.resolve() == CANARY_REGISTER_PATH.resolve():
            continue
        text = path.read_text(encoding="utf-8")
        for value, expected in declared.items():
            if value in text:
                assert path.resolve() == expected.resolve(), (
                    f"{value} appears in {path.relative_to(REPO_ROOT)}, "
                    f"but the register plants it in {expected.relative_to(REPO_ROOT)}"
                )


def test_the_system_prompt_carries_its_canary(register):
    """A7 is only machine-checkable if the system prompt holds a unique string."""
    entry = next(e for e in register["canaries"] if e["location_kind"] == "system_prompt")
    assert entry["value"] in load_config().system_prompt


def test_the_canary_scan_covers_the_source_tree_and_not_the_captures():
    """The scan scope is itself a rule, so it is asserted rather than assumed."""
    assert any(g.startswith("attacks/") for g in CANARY_SCAN_GLOBS)
    assert any(g.startswith("lab/") for g in CANARY_SCAN_GLOBS)
    assert not any(g.startswith("runs/") for g in CANARY_SCAN_GLOBS)
