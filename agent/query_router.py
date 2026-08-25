"""
SEZAR Agent — Query Router
==========================
Türkçe doğal dil sorgusundan yapılandırılmış niyet (intent) ve parametre çıkarır.
LLM'siz çalışır: ontoloji + normalizer + regex. Deterministik ve denetlenebilir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from nlp import participation_ontology as onto
from nlp.normalizer import normalize_maturity, normalize_text, parse_number

INTENTS = {
    "COMPARE_FINANCING": [
        "en avantajlı", "en uygun", "hangi banka", "karşılaştır", "kıyasla",
        "en ucuz", "en düşük", "bul", "öner", "tavsiye",
    ],
    "PRODUCT_LOOKUP": [
        "kaç", "ne kadar", "kâr payı oranı nedir", "oranı nedir", "var mı",
        "sunuyor mu", "kampanyası", "limiti nedir",
    ],
    "BANK_INTELLIGENCE": [
        "hakkında", "ürünleri neler", "kampanyaları neler", "hangi ürünler",
    ],
    "EXPLAIN_EVIDENCE": [
        "nereden biliyorsun", "kaynak", "kanıt", "doğru mu", "emin misin",
        "nereden aldın",
    ],
    "PAYMENT_PLAN": [
        "taksit", "aylık ödeme", "ödeme planı", "ne öderim", "geri ödeme",
    ],
}

_SCALE = {"bin": 1_000, "milyon": 1_000_000, "milyar": 1_000_000_000}


@dataclass
class Query:
    raw: str
    intent: str = "COMPARE_FINANCING"
    amount: float | None = None
    months: int | None = None
    product_type: str | None = None
    bank: str | None = None
    priority: str = "net_cost"
    confidence: float = 0.0
    signals: dict = field(default_factory=dict)

    def summary(self) -> dict:
        return {
            "intent": self.intent,
            "amount": self.amount,
            "term_months": self.months,
            "product_type": self.product_type,
            "bank": self.bank,
            "priority": self.priority,
            "confidence": self.confidence,
        }


def detect_intent(text: str) -> tuple[str, float]:
    low = text.lower()
    scores = {}
    for intent, keys in INTENTS.items():
        hit = sum(1 for k in keys if k in low)
        if hit:
            scores[intent] = hit
    if not scores:
        return "COMPARE_FINANCING", 0.55
    best = max(scores, key=scores.get)
    conf = min(0.98, 0.6 + 0.12 * scores[best])
    return best, round(conf, 2)


def extract_amount(text: str) -> float | None:
    low = text.lower()
    m = re.search(
        r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)\s*(bin|milyon|milyar)?\s*"
        r"(?:tl|₺|try|lira)",
        low,
    )
    if not m:
        m = re.search(
            r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)\s*(bin|milyon|milyar)\b", low
        )
    if not m:
        return None
    base = parse_number(m.group(1))
    if base is None:
        return None
    return base * _SCALE.get(m.group(2) or "", 1)


def extract_months(text: str) -> int | None:
    return normalize_maturity(text)


def extract_product(text: str) -> str | None:
    scores = onto.product_scores(text)
    if not scores:
        return None
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2.0 else None


def extract_bank(text: str, known_banks: list[str] | None = None) -> str | None:
    if not known_banks:
        return None
    low = text.lower()
    for b in known_banks:
        core = b.lower().replace("katılım", "").replace("bankası", "").strip()
        if core and len(core) > 2 and core in low:
            return b
    return None


def detect_priority(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ["taksit", "aylık ödeme", "aylık yük", "düşük taksit"]):
        return "cash_flow"
    if any(k in low for k in ["masraf", "peşin", "ücret", "tahsis"]):
        return "upfront"
    if any(k in low for k in ["dengeli", "genel"]):
        return "balanced"
    return "net_cost"


def route(text: str, known_banks: list[str] | None = None) -> Query:
    """Ana yönlendirme fonksiyonu."""
    normalized = normalize_text(text)
    intent, conf = detect_intent(text)
    q = Query(
        raw=text,
        intent=intent,
        amount=extract_amount(normalized) or extract_amount(text),
        months=extract_months(normalized) or extract_months(text),
        product_type=extract_product(text),
        bank=extract_bank(text, known_banks),
        priority=detect_priority(text),
        confidence=conf,
    )
    q.signals = {
        "normalized_query": normalized,
        "product_scores": onto.product_scores(text),
        "ontology_hits": [h["label"] for h in onto.detect_concepts(text)],
    }
    return q
