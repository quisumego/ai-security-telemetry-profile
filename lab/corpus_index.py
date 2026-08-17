"""The retrieval index over lab/corpus/.

Deterministic lexical scoring, computed in this process. No embeddings, so the
index makes no model calls, touches no network, and returns the same scores on
every run. That is what lets a capture be replayed and an ablation be re-run at
no cost.

A deliberate design choice, stated here rather than buried: **the index labels,
it does not filter.** A search returns every chunk that matches, whatever its
scope or tenant, and records the scope of each alongside the caller's own scope
so that `retrieval.permission_context.scope_match` can be computed. An index
that filtered correctly would make cross-tenant retrieval and restricted
disclosure impossible to attempt, and there would be nothing for the telemetry
to reveal. Labelling without filtering is also the realistic failure mode in
retrieval systems, which is the shape OWASP LLM08 describes.

The only control between the caller and restricted material is therefore the
model's own behaviour under the system prompt, which is exactly the thing the
attack corpus is built to measure.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
TOKEN = re.compile(r"[a-z0-9]+")

# Small stop list. Kept short deliberately: an aggressive list would throw away
# insurance terms that carry meaning in this corpus.
STOPWORDS = frozenset(
    """
    a an and are as at be been by for from has have in is it its of on or that
    the their there they this to was were where which who will with would
    """.split()
)

BM25_K1 = 1.2
BM25_B = 0.75


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    doc_type: str
    tenant: str
    provenance: str
    scope: str
    path: Path
    body: str
    meta: dict


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    index: int
    text: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    document: Document
    score: float


def tokenise(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if len(t) > 1 and t not in STOPWORDS]


def parse_document(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER.match(text)
    if match is None:
        raise ValueError(f"{path} has no YAML front matter")
    meta = yaml.safe_load(match.group(1)) or {}
    missing = {"id", "title", "doc_type", "tenant", "provenance", "scope"} - set(meta)
    if missing:
        raise ValueError(f"{path} front matter is missing {sorted(missing)}")
    return Document(
        id=str(meta["id"]),
        title=str(meta["title"]),
        doc_type=str(meta["doc_type"]),
        tenant=str(meta["tenant"]),
        provenance=str(meta["provenance"]),
        scope=str(meta["scope"]),
        path=path,
        body=match.group(2).strip(),
        meta=meta,
    )


def chunk_document(doc: Document, chunk_words: int, overlap_words: int) -> list[Chunk]:
    words = doc.body.split()
    if not words:
        return []
    step = max(1, chunk_words - overlap_words)
    chunks: list[Chunk] = []
    for i, start in enumerate(range(0, len(words), step)):
        window = words[start : start + chunk_words]
        if not window:
            break
        text = " ".join(window)
        chunks.append(
            Chunk(
                id=f"{doc.id}#c{i:02d}",
                document_id=doc.id,
                index=i,
                text=text,
                tokens=tuple(tokenise(text)),
            )
        )
        if start + chunk_words >= len(words):
            break
    return chunks


@dataclass
class CorpusIndex:
    """A BM25 index over the chunks of every document in the corpus."""

    documents: dict[str, Document] = field(default_factory=dict)
    chunks: list[Chunk] = field(default_factory=list)
    _doc_freq: Counter = field(default_factory=Counter)
    _avg_len: float = 0.0

    @classmethod
    def build(
        cls,
        corpus_dir: Path,
        chunk_words: int = 180,
        overlap_words: int = 30,
        overlay_dirs: tuple[Path, ...] = (),
    ) -> CorpusIndex:
        """Build the index from the corpus, plus any overlay directories.

        `overlay_dirs` exists so that M2 can add scenario-specific documents to
        a session's index without editing lab/corpus/, which stays the benign
        estate. Nothing uses it at M1.
        """
        index = cls()
        paths: list[Path] = sorted(corpus_dir.glob("*.md"))
        for extra in overlay_dirs:
            paths.extend(sorted(extra.glob("*.md")))

        for path in paths:
            doc = parse_document(path)
            if doc.id in index.documents:
                raise ValueError(f"duplicate document id {doc.id} at {path}")
            index.documents[doc.id] = doc
            index.chunks.extend(chunk_document(doc, chunk_words, overlap_words))

        for chunk in index.chunks:
            for term in set(chunk.tokens):
                index._doc_freq[term] += 1
        lengths = [len(c.tokens) for c in index.chunks]
        index._avg_len = (sum(lengths) / len(lengths)) if lengths else 0.0
        return index

    def score(self, query_terms: list[str], chunk: Chunk) -> float:
        if not chunk.tokens or not query_terms:
            return 0.0
        counts = Counter(chunk.tokens)
        n_chunks = len(self.chunks)
        length = len(chunk.tokens)
        total = 0.0
        for term in set(query_terms):
            freq = counts.get(term, 0)
            if freq == 0:
                continue
            n_containing = self._doc_freq.get(term, 0)
            idf = math.log(1 + (n_chunks - n_containing + 0.5) / (n_containing + 0.5))
            denom = freq + BM25_K1 * (1 - BM25_B + BM25_B * length / (self._avg_len or 1))
            total += idf * (freq * (BM25_K1 + 1)) / denom
        return total

    def search(self, query: str, top_k: int) -> list[ScoredChunk]:
        """Return the highest scoring chunks, whatever their scope or tenant.

        Ties break on chunk id so the ordering is stable across runs.
        """
        terms = tokenise(query)
        scored = []
        for chunk in self.chunks:
            value = self.score(terms, chunk)
            if value <= 0:
                continue
            scored.append(
                ScoredChunk(
                    chunk=chunk,
                    document=self.documents[chunk.document_id],
                    score=round(value, 4),
                )
            )
        scored.sort(key=lambda s: (-s.score, s.chunk.id))
        return scored[:top_k]
