"""
SEZARNEXT NLP Core — Participation Ontology
===========================================
Katılım bankacılığına özgü terminolojiyi kavram düzeyinde modelleyen
sembolik katman. Hybrid Neuro-Symbolic mimaride "symbolic" tarafın çekirdeği.

Üç işlevi vardır:
  1) Eş anlamlı / kurumsal varyant terimleri tek bir kanonik kavrama indirger.
  2) Konvansiyonel bankacılık terimini katılım karşılığına eşler (faiz -> kâr payı).
  3) Ürün ve kampanya sınıflandırıcısına ağırlıklı sinyal üretir.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# 1. Kanonik kavram sözlüğü
# ---------------------------------------------------------------------------
ONTOLOGY: dict[str, dict] = {
    "kar_payi": {
        "label": "Kâr Payı Oranı",
        "terms": ["kâr payı", "kar payı", "kâr payı oranı", "kar oranı", "kârlılık oranı"],
        "conventional": "faiz",
        "unit": "percent_monthly",
    },
    "murabaha": {
        "label": "Murabaha (Kâr Marjlı Satış)",
        "terms": ["murabaha", "murabaha yöntemi", "kâr marjlı satış", "vadeli satış"],
        "unit": None,
    },
    "musaraka": {
        "label": "Müşareke (Ortaklık)",
        "terms": ["müşareke", "musaraka", "kâr zarar ortaklığı", "ortaklık esaslı"],
        "unit": None,
    },
    "mudaraba": {
        "label": "Mudarebe (Emek-Sermaye Ortaklığı)",
        "terms": ["mudarebe", "mudaraba", "emek sermaye ortaklığı"],
        "unit": None,
    },
    "icara": {
        "label": "İcara (Finansal Kiralama)",
        "terms": ["icara", "icâra", "finansal kiralama", "leasing", "kiralama esaslı"],
        "unit": None,
    },
    "katilma_hesabi": {
        "label": "Katılma Hesabı",
        "terms": ["katılma hesabı", "katılım hesabı", "kâr payı hesabı", "katılma fonu"],
        "conventional": "vadeli mevduat",
        "unit": None,
    },
    "ozel_cari": {
        "label": "Özel Cari Hesap",
        "terms": ["özel cari hesap", "cari hesap", "vadesiz katılım hesabı"],
        "conventional": "vadesiz mevduat",
        "unit": None,
    },
    "kira_sertifikasi": {
        "label": "Kira Sertifikası (Sukuk)",
        "terms": ["kira sertifikası", "sukuk", "kira sertifikaları", "icare sukuku"],
        "conventional": "tahvil",
        "unit": None,
    },
    "tahsis_ucreti": {
        "label": "Tahsis Ücreti",
        "terms": ["tahsis ücreti", "tahsis komisyonu", "dosya masrafı", "kullandırım ücreti",
                  "tahsis bedeli", "dosya ücreti"],
        "unit": "amount_or_percent",
    },
    "ekspertiz": {
        "label": "Ekspertiz Ücreti",
        "terms": ["ekspertiz", "ekspertiz ücreti", "değerleme ücreti", "değerleme bedeli"],
        "unit": "amount",
    },
    "sigorta": {
        "label": "Sigorta Bedeli",
        "terms": ["sigorta", "hayat sigortası", "kasko", "dask", "tekafül", "katılım sigortası"],
        "unit": "amount",
    },
    "vade": {
        "label": "Vade",
        "terms": ["vade", "vadeli", "ay vadeli", "taksit sayısı", "geri ödeme süresi"],
        "unit": "months",
    },
    "finansman_tutari": {
        "label": "Finansman Tutarı",
        "terms": ["finansman tutarı", "finansman limiti", "kullandırım tutarı",
                  "finansman desteği", "azami tutar", "limit"],
        "unit": "amount",
    },
    "para_puan": {
        "label": "Para Puan",
        "terms": ["para puan", "parapuan", "puan", "bonus puan", "world puan", "chip para"],
        "unit": "amount",
    },
    "nakit_iade": {
        "label": "Nakit İade",
        "terms": ["nakit iade", "cashback", "geri ödeme kampanyası", "iade", "para iadesi"],
        "unit": "amount",
    },
    "ucret_muafiyeti": {
        "label": "Ücret Muafiyeti",
        "terms": ["ücret alınmaz", "masrafsız", "ücretsiz", "muafiyet", "sıfır masraf",
                  "tahsis ücreti yok", "dosya masrafı yok", "komisyon alınmaz"],
        "unit": "boolean",
    },
    "erken_odeme": {
        "label": "Erken Ödeme İndirimi",
        "terms": ["erken ödeme", "erken kapama", "peşin kapatma indirimi"],
        "unit": None,
    },
    "vade_erteleme": {
        "label": "Vade / Taksit Erteleme",
        "terms": ["taksit erteleme", "ödemesiz dönem", "vade erteleme", "ilk taksit",
                  "taksiti sonra öde"],
        "unit": None,
    },
}

# Konvansiyonel -> katılım terim eşleşmesi (metin ön işleme)
CONVENTIONAL_TO_PARTICIPATION: dict[str, str] = {
    "faiz oranı": "kâr payı oranı",
    "faiz": "kâr payı",
    "kredi": "finansman",
    "kredi tutarı": "finansman tutarı",
    "mevduat": "katılma hesabı",
    "tahvil": "kira sertifikası",
    "anapara": "finansman anaparası",
}

# ---------------------------------------------------------------------------
# 2. Ürün tipi sinyalleri
# ---------------------------------------------------------------------------
PRODUCT_SIGNALS: dict[str, list[tuple[str, float]]] = {
    "taşıt_finansmanı": [
        ("taşıt", 3.0), ("araç", 2.5), ("otomobil", 2.5), ("sıfır araç", 3.0),
        ("ikinci el araç", 3.0), ("motosiklet", 2.0), ("araba", 2.0), ("kasko", 0.8),
    ],
    "konut_finansmanı": [
        ("konut", 3.0), ("ev finansmanı", 3.0), ("mortgage", 2.5), ("ipotek", 2.0),
        ("ekspertiz", 0.8), ("dask", 1.0), ("tapu", 1.0),
    ],
    "ihtiyaç_finansmanı": [
        ("ihtiyaç finansmanı", 3.0), ("ihtiyaç", 2.0), ("bireysel finansman", 2.5),
        ("nakit ihtiyaç", 2.0), ("tüketici finansmanı", 2.0),
    ],
    "işyeri_finansmanı": [
        ("işyeri", 3.0), ("ticari gayrimenkul", 2.5), ("dükkan", 2.0),
    ],
    "kobi_finansmanı": [
        ("kobi", 3.0), ("işletme finansmanı", 2.5), ("ticari finansman", 2.0),
        ("esnaf", 2.0), ("çek", 1.0),
    ],
    "katılma_hesabı": [
        ("katılma hesabı", 3.0), ("katılım hesabı", 3.0), ("birikim", 1.5),
        ("vadeli hesap", 2.0), ("kâr payı hesabı", 2.5),
    ],
    "kredi_kartı": [
        ("kredi kartı", 3.0), ("kart", 1.5), ("para puan", 2.0), ("taksitli alışveriş", 2.0),
        ("nakit iade", 1.5), ("aidat", 1.5), ("temassız", 1.0),
    ],
    "kira_sertifikası": [
        ("kira sertifikası", 3.0), ("sukuk", 3.0), ("halka arz", 1.5),
    ],
    "altın_hesabı": [
        ("altın hesabı", 3.0), ("gram altın", 2.5), ("altın birikim", 2.5),
    ],
    "sigorta": [
        ("tekafül", 3.0), ("katılım sigortası", 3.0), ("poliçe", 2.0),
    ],
}

# ---------------------------------------------------------------------------
# 3. Kampanya tipi sinyalleri
# ---------------------------------------------------------------------------
CAMPAIGN_SIGNALS: dict[str, list[tuple[str, float]]] = {
    "oran_indirimi": [
        ("indirimli kâr payı", 3.0), ("özel kâr payı", 2.5), ("düşük kâr payı", 2.5),
        ("avantajlı oran", 2.0), ("kâr payı oranıyla", 1.5),
    ],
    "ücret_muafiyeti": [
        ("tahsis ücreti yok", 3.0), ("masrafsız", 3.0), ("ücretsiz", 2.0),
        ("dosya masrafı alınmaz", 3.0), ("sıfır masraf", 3.0), ("aidatsız", 2.5),
        ("komisyon alınmaz", 2.5),
    ],
    "nakit_iade": [
        ("nakit iade", 3.0), ("cashback", 3.0), ("para iadesi", 2.5), ("iade edilecek", 2.0),
    ],
    "para_puan": [
        ("para puan", 3.0), ("bonus puan", 2.5), ("puan kazan", 2.5), ("chip para", 2.5),
    ],
    "taksit_fırsatı": [
        ("taksit fırsatı", 3.0), ("ek taksit", 2.5), ("peşin fiyatına", 2.5),
        ("taksitle", 1.5),
    ],
    "ödüllü_hesap": [
        ("ödüllü", 3.0), ("çekiliş", 2.5), ("hediye çeki", 2.0),
    ],
    "vade_erteleme": [
        ("taksit erteleme", 3.0), ("ödemesiz dönem", 3.0), ("ilk taksit", 2.0),
        ("sonra öde", 2.0),
    ],
    "hediye": [
        ("hediye", 2.5), ("promosyon", 2.0), ("sürpriz", 1.5),
    ],
}


# ---------------------------------------------------------------------------
# 4. Regex tabanlı kampanya sinyalleri
# Sabit ifade listeleri Türkçe'nin çekim zenginliğini kaçırır
# ("alınmaz" / "yoktur" / "talep edilmez" / "muaftır"). Bu katman
# kalıp düzeyinde yakalar ve sınıflandırıcıya ek ağırlık verir.
# ---------------------------------------------------------------------------
CAMPAIGN_REGEX_SIGNALS: dict[str, list[tuple[str, float]]] = {
    "ücret_muafiyeti": [
        (r"(ücret|masraf|komisyon|aidat|bedel)\w*[^.;]{0,25}"
         r"(alınmaz|alınmamaktadır|yok(?:tur)?|ücretsiz|muaf\w*|bedelsiz|talep edilmez)", 3.2),
        (r"(ücretsiz|masrafsız|aidatsız|komisyonsuz|sıfır masraf)", 3.0),
    ],
    "oran_indirimi": [
        (r"%\s*0\s*(kâr|kar)\s*payı|sıfır\s*(kâr|kar)\s*payı|sıfır faiz", 3.4),
        (r"%\s*\d+(?:[.,]\d+)?\s*indirim", 3.0),
        (r"(indirimli|avantajlı|özel)\s*(kâr payı|oran)", 3.0),
        (r"indirim(?:li)?\b", 1.6),
    ],
    "nakit_iade": [(r"(nakit\s*iade|cashback|para\s*iadesi)", 3.2)],
    "para_puan": [(r"(para\s*puan|parapuan|chip\s*para|bonus\s*puan|puan kazan)", 3.2)],
    "vade_erteleme": [
        (r"(ödemesiz\s*dönem|taksit\s*erteleme|ilk\s*taksit[^.]{0,20}sonra)", 3.2),
    ],
    "taksit_fırsatı": [(r"(peşin fiyatına|ek taksit|\d+\s*taksit fırsatı)", 3.0)],
    "ödüllü_hesap": [(r"(çekiliş|ödül dağıt|ödüllü)", 3.0)],
    "hediye": [(r"hediye(?!\s*(?:para\s*puan|puan))", 2.0)],
}


def regex_scores(text: str, table: dict[str, list[tuple[str, float]]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for label, patterns in table.items():
        total = 0.0
        for pattern, weight in patterns:
            if re.search(pattern, text, re.I):
                total += weight
        if total:
            out[label] = total
    return out


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def _fold(text: str) -> str:
    """Türkçe duyarlı küçültme + aksan sadeleştirme (eşleşme toleransı için)."""
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t)


_FOLDED_ONTOLOGY: dict[str, list[tuple[str, str]]] = {
    concept: [(_fold(term), term) for term in meta["terms"]]
    for concept, meta in ONTOLOGY.items()
}


def map_conventional_terms(text: str) -> str:
    """Konvansiyonel bankacılık terimlerini katılım karşılıklarına çevirir."""
    out = text
    for conv, part in sorted(CONVENTIONAL_TO_PARTICIPATION.items(), key=lambda x: -len(x[0])):
        out = re.sub(rf"\b{re.escape(conv)}\b", part, out, flags=re.I)
    return out


def detect_concepts(text: str) -> list[dict]:
    """Metinde geçen ontoloji kavramlarını, eşleşen terimle birlikte döndürür."""
    folded = _fold(text)
    hits: list[dict] = []
    for concept, pairs in _FOLDED_ONTOLOGY.items():
        for folded_term, original in pairs:
            if folded_term in folded:
                hits.append(
                    {
                        "concept": concept,
                        "label": ONTOLOGY[concept]["label"],
                        "matched_term": original,
                    }
                )
                break
    return hits


def score_labels(text: str, signals: dict[str, list[tuple[str, float]]]) -> dict[str, float]:
    """Sinyal sözlüğüne göre etiket skorları üretir."""
    folded = _fold(text)
    scores: dict[str, float] = {}
    for label, terms in signals.items():
        total = 0.0
        for term, weight in terms:
            occ = folded.count(_fold(term))
            if occ:
                total += weight * (1 + 0.25 * (min(occ, 4) - 1))
        if total:
            scores[label] = round(total, 3)
    return scores


def product_scores(text: str) -> dict[str, float]:
    return score_labels(text, PRODUCT_SIGNALS)


def campaign_scores(text: str) -> dict[str, float]:
    """Sözlük sinyalleri + regex kalıp sinyalleri birleşimi."""
    scores = score_labels(text, CAMPAIGN_SIGNALS)
    for label, val in regex_scores(text, CAMPAIGN_REGEX_SIGNALS).items():
        scores[label] = scores.get(label, 0.0) + val
    return {k: round(v, 3) for k, v in scores.items()}


def concept_terms(concept: str) -> list[str]:
    return ONTOLOGY.get(concept, {}).get("terms", [])
