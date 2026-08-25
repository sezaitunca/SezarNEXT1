"""
SEZARNEXT Evidence
==================
Her yapay zekâ cevabının yanında kaynak künyesi üretir:

    Kaynak Banka / Kaynak URL / Kaynak Metin /
    Veri Çekim Tarihi / Extraction Method / Confidence Score

Bu katman explainability + traceability + hallucination control sağlar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from schemas.campaign_schema import SezarNextCampaign


@dataclass
class EvidenceCard:
    bank: str
    product: str
    source_url: str
    claim: str
    quote: str
    last_checked: str
    extraction_method: str
    confidence: float
    synthetic: bool = False

    def render(self) -> str:
        warn = "\n[DEMO VERİSİ — gerçek banka verisi değildir]" if self.synthetic else ""
        return (
            f"Kaynak doğrulandı.\n"
            f"Banka        : {self.bank}\n"
            f"Ürün         : {self.product}\n"
            f"İddia        : {self.claim}\n"
            f"Kanıt        : \"{self.quote}\"\n"
            f"URL          : {self.source_url}\n"
            f"Son kontrol  : {self.last_checked}\n"
            f"Yöntem       : {self.extraction_method}\n"
            f"Confidence   : {self.confidence:.2f}{warn}"
        )


FIELD_LABELS = {
    "profit_rate": "Kâr payı oranı",
    "financing_amount_max": "Azami finansman tutarı",
    "financing_amount_min": "Asgari finansman tutarı",
    "maturity_months": "Vade",
    "allocation_fee": "Tahsis ücreti",
    "reward_amount": "Nakit iade",
    "shopping_points": "Para puan",
    "discount_rate": "İndirim oranı",
    "expertise_fee": "Ekspertiz ücreti",
    "fee_waiver": "Ücret muafiyeti",
}


def build_card(campaign: SezarNextCampaign, field_name: str = "profit_rate") -> EvidenceCard:
    """Belirli bir alan için kanıt kartı üretir."""
    value = getattr(campaign, field_name, None)
    quote = campaign.evidence_text[:220]
    method = campaign.extraction_method.value
    conf = campaign.confidence_score

    for ev in campaign.evidence_items:
        if ev.field_name == field_name:
            quote = ev.raw_snippet
            method = ev.extraction_method.value
            conf = ev.confidence
            break

    label = FIELD_LABELS.get(field_name, field_name)
    claim = f"{label}: {value}"
    if field_name == "profit_rate" and value is not None:
        claim = f"{label}: %{value}".replace(".", ",")

    return EvidenceCard(
        bank=campaign.bank,
        product=campaign.product_name,
        source_url=campaign.source_url,
        claim=claim,
        quote=quote,
        last_checked=campaign.scraped_at.strftime("%d.%m.%Y"),
        extraction_method=method,
        confidence=conf,
        synthetic=campaign.is_synthetic,
    )


def coverage(campaigns: list[SezarNextCampaign]) -> float:
    """Evidence coverage metriği: kanıtı olan sayısal alan oranı."""
    tracked = ["profit_rate", "financing_amount_max", "maturity_months"]
    total = covered = 0
    for c in campaigns:
        ev_fields = {e.field_name for e in c.evidence_items}
        for f in tracked:
            if getattr(c, f, None) is not None:
                total += 1
                if f in ev_fields:
                    covered += 1
    return round(covered / total, 4) if total else 0.0
