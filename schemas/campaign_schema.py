"""
SEZARNEXT — Structured Financial Schema
=======================================
Katılım bankacılığı kampanya ve finansman ürünleri için Pydantic v2 modeli.

Bu modül SEZARNEXT NLP Core'un çıktı sözleşmesidir (output contract).
Extract katmanından çıkan her kayıt bu şemayı doğrulamak zorundadır.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Kontrollü sözlükler (Participation Ontology ile senkron)
# ---------------------------------------------------------------------------
class ProductType(str, Enum):
    TASIT_FINANSMANI = "taşıt_finansmanı"
    KONUT_FINANSMANI = "konut_finansmanı"
    IHTIYAC_FINANSMANI = "ihtiyaç_finansmanı"
    ISYERI_FINANSMANI = "işyeri_finansmanı"
    KOBI_FINANSMANI = "kobi_finansmanı"
    KATILMA_HESABI = "katılma_hesabı"
    KREDI_KARTI = "kredi_kartı"
    SUKUK = "kira_sertifikası"
    ALTIN_HESABI = "altın_hesabı"
    SIGORTA = "sigorta"
    DIGER = "diğer"


class CampaignType(str, Enum):
    ORAN_INDIRIMI = "oran_indirimi"
    UCRET_MUAFIYETI = "ücret_muafiyeti"
    NAKIT_IADE = "nakit_iade"
    PARA_PUAN = "para_puan"
    TAKSIT_FIRSATI = "taksit_fırsatı"
    ODULLU_HESAP = "ödüllü_hesap"
    VADE_ERTELEME = "vade_erteleme"
    HEDIYE = "hediye"
    DIGER = "diğer"


class ExtractionMethod(str, Enum):
    REGEX = "regex"
    ONTOLOGY = "ontology"
    HYBRID = "hybrid_neuro_symbolic"
    LLM = "local_llm"
    MANUAL = "manual"


class Currency(str, Enum):
    TRY = "TRY"
    USD = "USD"
    EUR = "EUR"
    XAU = "XAU"


# ---------------------------------------------------------------------------
# SEZARNEXT Evidence — açıklanabilirlik çekirdeği
# ---------------------------------------------------------------------------
class Evidence(BaseModel):
    """Her alanın hangi ham metinden, hangi yöntemle çıkarıldığının kanıtı."""

    field_name: str
    raw_snippet: str = Field(..., description="Kaynak metinden birebir alıntı")
    char_start: int | None = None
    char_end: int | None = None
    extraction_method: ExtractionMethod = ExtractionMethod.REGEX
    confidence: float = Field(0.0, ge=0.0, le=1.0)

    def as_citation(self) -> str:
        return f'"{self.raw_snippet.strip()}" ({self.extraction_method.value}, conf={self.confidence:.2f})'


# ---------------------------------------------------------------------------
# Ana model
# ---------------------------------------------------------------------------
class SezarNextCampaign(BaseModel):
    """SEZARNEXT'in birincil yapılandırılmış kaydı."""

    # --- Kaynak / izlenebilirlik ---
    bank: str
    bank_slug: str | None = None
    source_url: str
    scraped_at: datetime = Field(default_factory=datetime.now)

    # --- Ürün kimliği ---
    product_name: str
    product_type: ProductType = ProductType.DIGER
    campaign_type: CampaignType = CampaignType.DIGER

    # --- Finansal parametreler ---
    profit_rate: float | None = Field(None, ge=0, le=100, description="Aylık kâr payı oranı (%)")
    annual_cost_rate: float | None = Field(None, ge=0, le=500, description="Yıllık maliyet oranı (%)")
    financing_amount_min: float | None = Field(None, ge=0)
    financing_amount_max: float | None = Field(None, ge=0)
    maturity_months: int | None = Field(None, ge=1, le=360)
    installment_count: int | None = Field(None, ge=1, le=360)
    currency: Currency = Currency.TRY

    # --- Ücret ve masraflar ---
    allocation_fee: float | None = Field(None, ge=0, description="Tahsis ücreti (TL veya %)")
    allocation_fee_is_rate: bool = False
    expertise_fee: float | None = Field(None, ge=0, description="Ekspertiz ücreti")
    insurance_fee: float | None = Field(None, ge=0, description="Sigorta bedeli")
    other_fees: float = Field(0.0, ge=0)

    # --- Kampanya kazançları ---
    reward_amount: float | None = Field(None, ge=0, description="Nakit iade / ödül (TL)")
    discount_rate: float | None = Field(None, ge=0, le=100)
    shopping_points: float | None = Field(None, ge=0, description="Para puan (TL karşılığı)")
    fee_waiver: bool = False

    # --- Zaman ve koşullar ---
    campaign_start_date: date | None = None
    campaign_end_date: date | None = None
    conditions: list[str] = Field(default_factory=list)

    # --- Açıklanabilirlik ---
    evidence_text: str = ""
    evidence_items: list[Evidence] = Field(default_factory=list)
    extraction_method: ExtractionMethod = ExtractionMethod.HYBRID
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)

    # --- Meta ---
    is_synthetic: bool = Field(
        False, description="True ise veri demo amaçlı üretilmiştir, gerçek banka verisi değildir."
    )

    # ------------------------------------------------------------------
    # Doğrulayıcılar
    # ------------------------------------------------------------------
    @field_validator("bank", "product_name")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("boş metin alanı")
        return v

    @model_validator(mode="after")
    def _check_ranges(self) -> "SezarNextCampaign":
        lo, hi = self.financing_amount_min, self.financing_amount_max
        if lo is not None and hi is not None and lo > hi:
            self.financing_amount_min, self.financing_amount_max = hi, lo
        if self.installment_count is None and self.maturity_months is not None:
            self.installment_count = self.maturity_months
        s, e = self.campaign_start_date, self.campaign_end_date
        if s and e and s > e:
            self.campaign_start_date, self.campaign_end_date = e, s
        return self

    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------
    def is_eligible(self, amount: float, months: int, product_type: str | None = None) -> bool:
        """Talep edilen tutar/vade için ürün uygun mu?"""
        if product_type and self.product_type.value != product_type:
            return False
        if self.financing_amount_max is not None and amount > self.financing_amount_max:
            return False
        if self.financing_amount_min is not None and amount < self.financing_amount_min:
            return False
        if self.maturity_months is not None and months > self.maturity_months:
            return False
        return self.profit_rate is not None

    def is_active(self, on: date | None = None) -> bool:
        on = on or date.today()
        if self.campaign_start_date and on < self.campaign_start_date:
            return False
        if self.campaign_end_date and on > self.campaign_end_date:
            return False
        return True

    def citation(self) -> dict[str, Any]:
        """SEZARNEXT Evidence bloğu için kaynak künyesi."""
        return {
            "bank": self.bank,
            "product": self.product_name,
            "source_url": self.source_url,
            "evidence": self.evidence_text,
            "last_checked": self.scraped_at.strftime("%d.%m.%Y"),
            "extraction_method": self.extraction_method.value,
            "confidence": round(self.confidence_score, 3),
            "synthetic": self.is_synthetic,
        }


class ExtractionResult(BaseModel):
    """NLP Inspector'ın gösterdiği tam boru hattı çıktısı."""

    original_text: str
    normalized_text: str
    detected_entities: dict[str, Any] = Field(default_factory=dict)
    ontology_hits: list[str] = Field(default_factory=list)
    campaign: SezarNextCampaign | None = None
    validation_errors: list[str] = Field(default_factory=list)
    is_valid: bool = True
