"""
SEZARNEXT Knowledge Layer — Indexer
===================================
Kampanya kayıtlarını aranabilir belge parçalarına (chunk) dönüştürür ve
saf Python BM25 dizini kurar. Harici vektör veritabanı gerektirmez;
üretimde Qdrant/FAISS'e aynı arayüzle geçilebilir (bkz. VectorBackend).
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

TURKISH_STOPWORDS = {
    "ve", "ile", "için", "bir", "bu", "da", "de", "ki", "mi", "mı", "olan",
    "olarak", "veya", "ya", "her", "en", "daha", "çok", "gibi", "kadar",
    "ancak", "ise", "tüm", "sonra", "önce", "üzere", "göre", "the", "of",
}


def fold(text: str) -> str:
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9%]+", fold(text))
    return [t for t in tokens if t not in TURKISH_STOPWORDS and len(t) > 1]


@dataclass
class Document:
    doc_id: str
    text: str
    metadata: dict = field(default_factory=dict)


class BM25Index:
    """Okapi BM25 — bağımlılıksız, on-premise, deterministik."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.docs: list[Document] = []
        self.tokens: list[list[str]] = []
        self.df: Counter = Counter()
        self.avgdl: float = 0.0

    def add(self, doc: Document) -> None:
        toks = tokenize(doc.text)
        self.docs.append(doc)
        self.tokens.append(toks)
        for t in set(toks):
            self.df[t] += 1

    def build(self) -> "BM25Index":
        if self.tokens:
            self.avgdl = sum(len(t) for t in self.tokens) / len(self.tokens)
        return self

    def _idf(self, term: str) -> float:
        n = len(self.docs)
        df = self.df.get(term, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[tuple[Document, float]]:
        q = tokenize(query)
        if not q or not self.docs:
            return []
        results = []
        for i, doc in enumerate(self.docs):
            if filters and any(doc.metadata.get(k) != v for k, v in filters.items()):
                continue
            toks = self.tokens[i]
            if not toks:
                continue
            tf = Counter(toks)
            dl = len(toks)
            score = 0.0
            for term in q:
                f = tf.get(term, 0)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                score += self._idf(term) * f * (self.k1 + 1) / denom
            if score > 0:
                results.append((doc, round(score, 4)))
        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(
                [{"doc_id": d.doc_id, "text": d.text, "metadata": d.metadata} for d in self.docs],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "BM25Index":
        idx = cls()
        for rec in json.loads(Path(path).read_text(encoding="utf-8")):
            idx.add(Document(**rec))
        return idx.build()


def build_index_from_campaigns(campaigns) -> BM25Index:
    """SezarNextCampaign listesinden arama dizini kurar."""
    idx = BM25Index()
    for i, c in enumerate(campaigns):
        text = " ".join(
            filter(None, [c.bank, c.product_name, c.product_type.value,
                          c.campaign_type.value, c.evidence_text, " ".join(c.conditions)])
        )
        idx.add(
            Document(
                doc_id=f"{c.bank_slug or c.bank}-{i}",
                text=text,
                metadata={
                    "bank": c.bank,
                    "product_type": c.product_type.value,
                    "campaign_type": c.campaign_type.value,
                    "source_url": c.source_url,
                    "index": i,
                },
            )
        )
    return idx.build()


class VectorBackend:
    """
    Üretimde Qdrant/FAISS + yerel embedding modeli için arayüz iskeleti.
    Model yoksa BM25'e düşer (graceful degradation).
    """

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small") -> None:
        self.model_name = model_name
        self.available = False
        try:  # pragma: no cover
            from sentence_transformers import SentenceTransformer  # type: ignore

            self.model = SentenceTransformer(model_name)
            self.available = True
        except Exception:
            self.model = None
