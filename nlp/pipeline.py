"""
SEZARNEXT NLP Core — Pipeline
=============================
Ham metin → temizleme → normalizasyon → ontoloji → varlık çıkarımı →
sınıflandırma → doğrulama → Pydantic kayıt.

NLP Inspector ekranı bu boru hattının her adımını görselleştirir.
"""

from __future__ import annotations

from datetime import datetime

from nlp import campaign_classifier, participation_ontology as onto
from nlp.cleaner import clean
from nlp.entity_extractor import extract_entities
from nlp.normalizer import normalize_text
from nlp.semantic_validator import validate
from schemas.campaign_schema import (
    CampaignType,
    ExtractionMethod,
    ExtractionResult,
    ProductType,
    SezarNextCampaign,
)


def _safe_enum(enum_cls, value, default):
    try:
        return enum_cls(value)
    except ValueError:
        return default


def run_pipeline(
    raw_text: str,
    bank: str,
    source_url: str,
    product_name: str | None = None,
    scraped_at: datetime | None = None,
    use_llm: bool = False,
    is_synthetic: bool = False,
) -> ExtractionResult:
    """Tek bir metin parçasını tam boru hattından geçirir."""
    original = raw_text or ""
    cleaned = clean(original)
    normalized = normalize_text(cleaned)

    ext = extract_entities(cleaned)
    fields = dict(ext["fields"])
    evidence_items = ext["evidence"]
    evidence_fields = {e.field_name for e in evidence_items}

    cls = campaign_classifier.classify(cleaned)

    val = validate(cleaned, fields, evidence_fields, use_llm=use_llm)
    fields = val["fields"]

    # Güven skoru: çıkarım + sınıflandırma birleşimi
    conf = round(
        0.6 * ext["confidence"]
        + 0.2 * cls["product_confidence"]
        + 0.2 * cls["campaign_confidence"],
        3,
    )
    if not val["is_valid"]:
        conf = round(conf * 0.75, 3)

    method = ExtractionMethod.HYBRID
    if val["llm_used"]:
        method = ExtractionMethod.LLM

    campaign = None
    try:
        campaign = SezarNextCampaign(
            bank=bank,
            source_url=source_url,
            scraped_at=scraped_at or datetime.now(),
            product_name=product_name or (cleaned[:70] if cleaned else "Bilinmeyen ürün"),
            product_type=_safe_enum(ProductType, cls["product_type"], ProductType.DIGER),
            campaign_type=_safe_enum(CampaignType, cls["campaign_type"], CampaignType.DIGER),
            evidence_text=cleaned[:400],
            evidence_items=evidence_items,
            extraction_method=method,
            confidence_score=conf,
            is_synthetic=is_synthetic,
            **{k: v for k, v in fields.items() if k in SezarNextCampaign.model_fields},
        )
    except Exception as exc:  # şema doğrulaması başarısız
        val["errors"].append(f"[schema] {exc}")

    return ExtractionResult(
        original_text=original,
        normalized_text=normalized,
        detected_entities={k: str(v) for k, v in fields.items()},
        ontology_hits=[h["label"] for h in ext["ontology_hits"]],
        campaign=campaign,
        validation_errors=val["errors"],
        is_valid=val["is_valid"] and campaign is not None,
    )


def inspect(raw_text: str) -> dict:
    """NLP Inspector için adım adım çıktı (dashboard'da gösterilir)."""
    cleaned = clean(raw_text)
    normalized = normalize_text(cleaned)
    ext = extract_entities(cleaned)
    cls = campaign_classifier.classify(cleaned)
    evidence_fields = {e.field_name for e in ext["evidence"]}
    val = validate(cleaned, ext["fields"], evidence_fields)
    return {
        "1_original_text": raw_text,
        "2_cleaned_text": cleaned,
        "3_normalized_text": normalized,
        "4_ontology_hits": ext["ontology_hits"],
        "5_detected_entities": ext["fields"],
        "6_classification": cls,
        "7_validation": {"is_valid": val["is_valid"], "errors": val["errors"]},
        "8_evidence": [e.model_dump() for e in ext["evidence"]],
        "confidence": ext["confidence"],
    }
