"""
SEZARNEXT NLP Core — Semantic Validation & Local LLM Layer
==========================================================
İki katmanlı doğrulama:

  1) Sembolik doğrulama (her zaman çalışır, bağımlılık yok)
     - Finansal mantık kuralları (oran aralığı, vade/tutar tutarlılığı)
     - Kanıt zorunluluğu: kanıtsız alan kabul edilmez  → hallucination control
  2) Yerel LLM doğrulaması (opsiyonel, Ollama/llama.cpp üzerinden)
     - Belirsiz veya düşük güvenli alanlar için ikinci görüş
     - Ağ yoksa sessizce devre dışı kalır; sistem çalışmaya devam eder

Tasarım ilkesi: LLM asla sayı ÜRETMEZ, sadece regex çıktısını DOĞRULAR.
Bu, SEZARNEXT'in hallucination rate hedefini (<%1) yapısal olarak garanti eder.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

LOCAL_LLM_URL = os.environ.get("SEZARNEXT_LLM_URL", "http://localhost:11434/api/generate")
LOCAL_LLM_MODEL = os.environ.get("SEZARNEXT_LLM_MODEL", "qwen2.5:7b-instruct")
LLM_ENABLED = os.environ.get("SEZARNEXT_LLM_ENABLED", "0") == "1"

# ---------------------------------------------------------------------------
# 1. Sembolik kural motoru
# ---------------------------------------------------------------------------
RULES: list[tuple[str, str]] = [
    ("profit_rate_range", "Aylık kâr payı oranı 0-20 aralığında olmalıdır."),
    ("maturity_range", "Vade 1-360 ay aralığında olmalıdır."),
    ("amount_order", "Asgari tutar azami tutardan büyük olamaz."),
    ("evidence_required", "Sayısal her alanın kaynak metinde kanıtı bulunmalıdır."),
    ("fee_sanity", "Tahsis ücreti oranı %20'yi aşamaz."),
    ("date_order", "Kampanya başlangıcı bitişten sonra olamaz."),
]


def validate_fields(fields: dict[str, Any], evidence_fields: set[str]) -> list[str]:
    """Sembolik doğrulama. Hata mesajları listesi döndürür (boşsa geçerli)."""
    errors: list[str] = []

    pr = fields.get("profit_rate")
    if pr is not None and not (0 < pr <= 20):
        errors.append(f"[profit_rate_range] Aylık kâr payı makul aralık dışında: {pr}")

    mm = fields.get("maturity_months")
    if mm is not None and not (1 <= mm <= 360):
        errors.append(f"[maturity_range] Vade makul aralık dışında: {mm}")

    lo, hi = fields.get("financing_amount_min"), fields.get("financing_amount_max")
    if lo is not None and hi is not None and lo > hi:
        errors.append(f"[amount_order] Asgari ({lo}) > azami ({hi})")

    af = fields.get("allocation_fee")
    if af is not None and fields.get("allocation_fee_is_rate") and af > 20:
        errors.append(f"[fee_sanity] Tahsis ücreti oranı aşırı: %{af}")

    s, e = fields.get("campaign_start_date"), fields.get("campaign_end_date")
    if s and e and s > e:
        errors.append("[date_order] Kampanya başlangıcı bitişten sonra")

    numeric_fields = {
        "profit_rate", "financing_amount_min", "financing_amount_max",
        "maturity_months", "allocation_fee", "reward_amount", "shopping_points",
        "discount_rate",
    }
    for f in numeric_fields & set(fields.keys()):
        if fields[f] is not None and f not in evidence_fields:
            errors.append(f"[evidence_required] '{f}' alanı kanıtsız — reddedildi")

    return errors


def enforce_evidence(fields: dict[str, Any], evidence_fields: set[str]) -> dict[str, Any]:
    """Kanıtı olmayan sayısal alanları düşürür (hallucination control)."""
    numeric_fields = {
        "profit_rate", "financing_amount_min", "financing_amount_max",
        "maturity_months", "allocation_fee", "reward_amount", "shopping_points",
        "discount_rate", "expertise_fee", "insurance_fee",
    }
    return {
        k: v for k, v in fields.items()
        if not (k in numeric_fields and k not in evidence_fields)
    }


# ---------------------------------------------------------------------------
# 2. Yerel LLM doğrulama katmanı (opsiyonel)
# ---------------------------------------------------------------------------
VALIDATION_PROMPT = """Sen bir katılım bankacılığı veri doğrulama uzmanısın.
Aşağıdaki METİN'den çıkarılan ALANLAR'ı doğrula.

Kurallar:
- Yeni değer ÜRETME. Sadece verilen değerleri onayla veya reddet.
- Bir değer metinde açıkça yoksa "reject" yaz.
- Yanıtı SADECE JSON olarak ver, açıklama ve markdown ekleme.

METİN:
{text}

ALANLAR:
{fields}

Yanıt formatı:
{{"decisions": {{"alan_adı": "accept" | "reject"}}, "note": "kısa gerekçe"}}"""


def llm_available() -> bool:
    if not LLM_ENABLED:
        return False
    try:
        import urllib.request

        urllib.request.urlopen(LOCAL_LLM_URL.replace("/api/generate", "/api/tags"), timeout=2)
        return True
    except Exception:
        return False


def llm_validate(text: str, fields: dict[str, Any], timeout: int = 30) -> dict[str, str]:
    """
    Yerel LLM ile ikinci görüş. Erişilemezse boş sözlük döner ve
    sistem sembolik doğrulamayla devam eder (graceful degradation).
    """
    if not llm_available():
        return {}
    try:
        import urllib.request

        payload = json.dumps(
            {
                "model": LOCAL_LLM_MODEL,
                "prompt": VALIDATION_PROMPT.format(
                    text=text[:4000],
                    fields=json.dumps(fields, ensure_ascii=False, default=str),
                ),
                "stream": False,
                "options": {"temperature": 0.0},
            }
        ).encode()
        req = urllib.request.Request(
            LOCAL_LLM_URL, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
        raw = body.get("response", "")
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        parsed = json.loads(raw)
        return parsed.get("decisions", {})
    except Exception:
        return {}


def validate(text: str, fields: dict[str, Any], evidence_fields: set[str],
             use_llm: bool = False) -> dict[str, Any]:
    """Tam doğrulama boru hattı."""
    cleaned = enforce_evidence(fields, evidence_fields)
    errors = validate_fields(cleaned, evidence_fields)

    llm_decisions: dict[str, str] = {}
    if use_llm:
        llm_decisions = llm_validate(text, cleaned)
        for field, decision in llm_decisions.items():
            if decision == "reject" and field in cleaned:
                cleaned.pop(field)
                errors.append(f"[local_llm] '{field}' yerel LLM tarafından reddedildi")

    return {
        "fields": cleaned,
        "errors": errors,
        "is_valid": len(errors) == 0,
        "llm_used": bool(llm_decisions),
        "llm_decisions": llm_decisions,
    }
