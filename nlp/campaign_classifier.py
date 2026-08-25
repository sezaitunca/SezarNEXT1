"""
SEZARNEXT NLP Core — Campaign & Product Classification
======================================================
Ontoloji sinyalleri üzerinden ağırlıklı skorlama ile ürün tipi ve kampanya
tipi tahmini yapar. Softmax benzeri normalizasyonla kalibre edilmiş güven
skoru üretir ve karar gerekçesini (matched terms) döndürür.
"""

from __future__ import annotations

import math

from nlp import participation_ontology as onto
from schemas.campaign_schema import CampaignType, ProductType


def _softmax_top(scores: dict[str, float], temperature: float = 2.5):
    if not scores:
        return None, 0.0, {}
    exp = {k: math.exp(v / temperature) for k, v in scores.items()}
    total = sum(exp.values())
    probs = {k: v / total for k, v in exp.items()}
    label = max(probs, key=probs.get)
    return label, probs[label], probs


def classify_product(text: str) -> dict:
    scores = onto.product_scores(text)
    label, conf, probs = _softmax_top(scores)
    if label is None or max(scores.values(), default=0) < 1.5:
        return {
            "label": ProductType.DIGER.value,
            "confidence": 0.35,
            "scores": scores,
            "distribution": probs,
        }
    return {
        "label": label,
        "confidence": round(min(0.99, conf + 0.05 * min(scores[label], 6) / 6), 3),
        "scores": scores,
        "distribution": {k: round(v, 3) for k, v in probs.items()},
    }


def classify_campaign(text: str) -> dict:
    scores = onto.campaign_scores(text)
    label, conf, probs = _softmax_top(scores)
    if label is None or max(scores.values(), default=0) < 1.5:
        return {
            "label": CampaignType.DIGER.value,
            "confidence": 0.35,
            "scores": scores,
            "distribution": probs,
        }
    return {
        "label": label,
        "confidence": round(min(0.99, conf + 0.05 * min(scores[label], 6) / 6), 3),
        "scores": scores,
        "distribution": {k: round(v, 3) for k, v in probs.items()},
    }


def classify(text: str) -> dict:
    """Tek çağrıda ürün + kampanya sınıflandırması."""
    p = classify_product(text)
    c = classify_campaign(text)
    return {
        "product_type": p["label"],
        "product_confidence": p["confidence"],
        "campaign_type": c["label"],
        "campaign_confidence": c["confidence"],
        "product_scores": p["scores"],
        "campaign_scores": c["scores"],
    }
