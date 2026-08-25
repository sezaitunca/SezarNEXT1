"""
SEZARNEXT NLP Core — Entity Extraction
======================================
Türkçe katılım bankacılığı metninden finansal varlıkları çıkarır.

Yöntem: Rule Engine (regex) + Participation Ontology + güven skorlaması.
Her çıkarılan alan için kanıt (evidence span) üretilir → SEZARNEXT Evidence.
"""

from __future__ import annotations

import re
from datetime import date

from nlp import participation_ontology as onto
from nlp.normalizer import detect_currency, parse_number
from schemas.campaign_schema import Evidence, ExtractionMethod

# ---------------------------------------------------------------------------
# Yardımcı desen parçaları
# ---------------------------------------------------------------------------
NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+\.\d{1,2}(?!\d)|\d+(?:,\d+)?"
SCALE = r"(?:\s*(bin|milyon|milyar))?"
MONEY_UNIT = r"(?:\s*(?:TL|₺|TRY|Türk Lirası|lira|USD|\$|dolar|EUR|€|euro))"

_SCALE_MULT = {"bin": 1_000, "milyon": 1_000_000, "milyar": 1_000_000_000, None: 1, "": 1}

MONTHS_TR = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
    "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}


def _amount_from_match(num_txt: str, scale: str | None) -> float | None:
    val = parse_number(num_txt)
    if val is None:
        return None
    return val * _SCALE_MULT.get((scale or "").lower(), 1)


def _snippet(text: str, start: int, end: int, pad: int = 45) -> str:
    s = max(0, start - pad)
    e = min(len(text), end + pad)
    return ("..." if s > 0 else "") + text[s:e].strip() + ("..." if e < len(text) else "")


class _Collector:
    """Alan + kanıt biriktirici."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.fields: dict = {}
        self.evidence: list[Evidence] = []

    def add(self, field: str, value, m: re.Match, conf: float,
            method: ExtractionMethod = ExtractionMethod.REGEX) -> None:
        if value is None or field in self.fields:
            return
        self.fields[field] = value
        self.evidence.append(
            Evidence(
                field_name=field,
                raw_snippet=_snippet(self.text, m.start(), m.end()),
                char_start=m.start(),
                char_end=m.end(),
                extraction_method=method,
                confidence=round(conf, 3),
            )
        )


# ---------------------------------------------------------------------------
# 1. Kâr payı oranı
# ---------------------------------------------------------------------------
PCT = r"(?:%|yüzde)\s*"

RATE_PATTERNS: list[tuple[str, float, str]] = [
    (rf"(?:aylık|ayda)\s*{PCT}({NUM})", 0.98, "monthly"),
    (rf"{PCT}({NUM})\s*(?:aylık|ay(?:lık)?\s*kâr\s*payı|oranıyla)", 0.97, "monthly"),
    (rf"kâr\s*payı\s*oranı[^%\d]{{0,25}}{PCT}({NUM})", 0.95, "monthly"),
    (rf"k[âa]r\s*payı[^%\d]{{0,25}}{PCT}({NUM})", 0.92, "monthly"),
    (rf"{PCT}({NUM})\s*(?:'?den|'?dan)?\s*(?:başlayan|başlar)\s*(?:kâr|kar)?\s*(?:payı)?", 0.93, "monthly"),
    (rf"(?:yıllık)\s*{PCT}({NUM})", 0.90, "annual"),
    (rf"{PCT}({NUM})\s*kâr\s*payı", 0.90, "monthly"),
]


def extract_profit_rate(text: str, c: _Collector) -> None:
    for pattern, conf, kind in RATE_PATTERNS:
        m = re.search(pattern, text, re.I)
        if not m:
            continue
        val = parse_number(m.group(1))
        if val is None:
            continue
        if kind == "annual":
            # Yıllık oran ayrı bir alandır; aylık orana BÖLEREK türetilmez.
            # Türetilmiş sayı kaynak metinde geçmez → hallucination sayılır.
            if 0 < val <= 500:
                c.add("annual_cost_rate", round(val, 4), m, conf)
            return
        if 0 <= val <= 20:  # %0 kampanyaları dahil makul aralık
            c.add("profit_rate", round(val, 4), m, conf)
            return


# ---------------------------------------------------------------------------
# 2. Tutarlar
# ---------------------------------------------------------------------------
def extract_profit_rate_fallback(text: str, c: _Collector) -> None:
    """Yüzde işareti olmadan yazılmış oranlar ("kâr payı oranımız 1,95")."""
    if "profit_rate" in c.fields:
        return
    m = re.search(rf"k[âa]r\s*payı(?:\s*oranı\w*)?[^%\d]{{0,20}}(\d{{1,2}},\d{{1,2}})", text, re.I)
    if m:
        val = parse_number(m.group(1))
        if val is not None and 0 <= val <= 20:
            c.add("profit_rate", round(val, 4), m, 0.80)
            return
    # Yazıyla oran: "yüzde iki virgül seksen dokuz"
    m = re.search(r"yüzde\s+([a-zçğıöşü\s]+?virgül[a-zçğıöşü\s]+?)(?:'?dur|'?dır|\.|,|$)", text, re.I)
    if m:
        from nlp.normalizer import parse_word_number

        whole, _, frac = m.group(1).partition("virgül")
        w, f = parse_word_number(whole), parse_word_number(frac)
        if w is not None and f is not None:
            val = float(f"{int(w)}.{int(f):02d}")
            if 0 <= val <= 20:
                c.add("profit_rate", val, m, 0.75)


def extract_amounts(text: str, c: _Collector) -> None:
    # Aralık: "300.000 TL ila 1.200.000 TL arasındadır"
    m = re.search(
        rf"({NUM}){SCALE}\s*(?:TL|₺)?\s*(?:ila|ile|[-–])\s*({NUM}){SCALE}\s*(?:TL|₺)\s*"
        rf"(?:aras|tutarında)?",
        text, re.I,
    )
    if m:
        v1 = _amount_from_match(m.group(1), m.group(2))
        v2 = _amount_from_match(m.group(3), m.group(4))
        if v1 and v2 and v2 > v1 >= 1000:
            c.add("financing_amount_min", v1, m, 0.93)
            c.add("financing_amount_max", v2, m, 0.93)

    # üst limit
    for pattern, conf in [
        (rf"({NUM}){SCALE}\s*(?:TL|₺|TRY)?\s*(?:'?ye|'?ya|'?e|'?a)?\s*kadar", 0.96),
        (rf"(?:azami|en fazla|maksimum|üst limit)[^\d]{{0,15}}({NUM}){SCALE}{MONEY_UNIT}?", 0.94),
        (rf"(?:limiti|tutarı)[^\d]{{0,15}}({NUM}){SCALE}{MONEY_UNIT}", 0.88),
    ]:
        m = re.search(pattern, text, re.I)
        if m:
            val = _amount_from_match(m.group(1), m.group(2) if m.lastindex and m.lastindex >= 2 else None)
            if val and val >= 1000:
                c.add("financing_amount_max", val, m, conf)
                break

    # alt limit
    m = re.search(
        rf"(?:en az|asgari|minimum)[^\d]{{0,15}}({NUM}){SCALE}{MONEY_UNIT}?", text, re.I
    )
    if m:
        val = _amount_from_match(m.group(1), m.group(2))
        if val and val >= 100:
            c.add("financing_amount_min", val, m, 0.93)

    # Fallback: açık bir "kadar/azami" işareti yoksa, metindeki en büyük TL
    # tutarı düşük güvenle finansman limiti kabul edilir (>= 50.000 TL eşiği,
    # ödül/puan tutarlarını dışarıda bırakmak için).
    if "financing_amount_max" not in c.fields:
        neg_after = re.compile(
            r"^[^.]{0,20}?(ödül|hediye|puan|iade|çekiliş|bakiye|harcama|ücret|masraf|prim)",
            re.I,
        )
        neg_before = re.compile(
            r"(en az|asgari|minimum|ödül|hediye|puan|iade|çekiliş|bakiye|harcama|geri\s*ödeme|toplam)\s*$", re.I
        )
        min_val = c.fields.get("financing_amount_min")
        best_m, best_v = None, 0.0
        for mm in re.finditer(rf"({NUM}){SCALE}\s*(?:TL|₺|TRY)", text, re.I):
            v = _amount_from_match(mm.group(1), mm.group(2))
            if not v or v < 50_000 or v <= best_v:
                continue
            if min_val is not None and abs(v - min_val) < 1:
                continue
            if neg_after.search(text[mm.end(): mm.end() + 30]):
                continue
            if neg_before.search(text[max(0, mm.start() - 25): mm.start()]):
                continue
            best_m, best_v = mm, v
        if best_m is not None:
            c.add("financing_amount_max", best_v, best_m, 0.78)

    # Yazıyla tutar: "yedi yüz elli bin lira"
    if "financing_amount_max" not in c.fields:
        m = re.search(
            r"((?:[a-zçğıöşü]+\s+){1,6}(?:bin|milyon|milyar))\s*(?:TL|lira|₺)", text, re.I
        )
        if m:
            from nlp.normalizer import parse_word_number

            val = parse_word_number(m.group(1))
            if val and val >= 10_000:
                c.add("financing_amount_max", val, m, 0.82)

    m = re.search(rf"({NUM}){SCALE}\s*(?:TL|₺|TRY)\s*(?:ve üzeri|üzeri|ve üstü)", text, re.I)
    if m and "financing_amount_min" not in c.fields:
        val = _amount_from_match(m.group(1), m.group(2))
        if val:
            c.add("financing_amount_min", val, m, 0.9)


# ---------------------------------------------------------------------------
# 3. Vade
# ---------------------------------------------------------------------------
def extract_maturity(text: str, c: _Collector) -> None:
    # Aralık ifadesi ("12-48 ay") → konvansiyon gereği AZAMİ vade alınır
    m = re.search(r"(\d{1,3})\s*[-–]\s*(\d{1,3})\s*ay", text, re.I)
    if m:
        hi = max(int(m.group(1)), int(m.group(2)))
        if 1 <= hi <= 360:
            c.add("maturity_months", hi, m, 0.95)

    for pattern, conf, mult in [
        (r"(\d{1,3})\s*ay(?:a|'a)?\s*(?:kadar|varan)", 0.96, 1),
        (r"(\d{1,3})\s*ay\s*vade", 0.96, 1),
        (r"vade[si]{0,2}\s*(\d{1,3})\s*ay", 0.94, 1),
        (r"(\d{1,3})\s*ay\b", 0.85, 1),
        (r"(\d{1,2})\s*(?:yıl|sene)\s*(?:vade)?", 0.88, 12),
    ]:
        m = re.search(pattern, text, re.I)
        if m:
            val = int(m.group(1)) * mult
            if 1 <= val <= 360:
                c.add("maturity_months", val, m, conf)
                break

    if "maturity_months" not in c.fields:
        m = re.search(r"((?:[a-zçğıöşü]+\s+){1,3}?)ay(?:a|'a)?\s*(?:vade|kadar|varan|\b)", text, re.I)
        if m:
            from nlp.normalizer import parse_word_number

            val = parse_word_number(m.group(1))
            if val and 1 <= val <= 360:
                c.add("maturity_months", int(val), m, 0.82)

    m = re.search(r"(\d{1,3})\s*taksit", text, re.I)
    if m:
        val = int(m.group(1))
        if 1 <= val <= 360:
            c.add("installment_count", val, m, 0.93)


# ---------------------------------------------------------------------------
# 4. Ücret ve masraflar
# ---------------------------------------------------------------------------
FEE_TERMS = {
    "allocation_fee": ["tahsis ücreti", "tahsis komisyonu", "dosya masrafı", "dosya ücreti",
                       "kullandırım ücreti", "tahsis bedeli"],
    "expertise_fee": ["ekspertiz ücreti", "ekspertiz", "değerleme ücreti", "değerleme bedeli"],
    "insurance_fee": ["sigorta bedeli", "hayat sigortası", "kasko bedeli", "tekafül bedeli"],
}

WAIVER_RE = re.compile(
    r"\b(?:yok(?:tur)?|alınmaz|alınmamaktadır|ücretsiz|sıfır|muaf(?:tır)?|bedelsiz|"
    r"talep\s+edilmez|0\s*TL)\b",
    re.I,
)
GLOBAL_WAIVER_RE = re.compile(
    r"masrafsız|sıfır\s+masraf|hiçbir\s+ücret\s+alınmaz|aidatsız|komisyon\s+alınmaz|"
    r"tüm\s+masraflar(?:dan)?\s+muaf",
    re.I,
)


def extract_fees(text: str, c: _Collector) -> None:
    """
    Alan bazlı ücret çıkarımı.
    Önemli: bir alanın muaf olması (ör. ekspertiz) diğer alanları etkilemez.
    Genel muafiyet (fee_waiver) yalnızca kapsayıcı ifadelerle set edilir.
    """
    for field, terms in FEE_TERMS.items():
        for term in terms:
            for m in re.finditer(re.escape(term), text, re.I):
                window = text[m.end(): m.end() + 45]
                pre = text[max(0, m.start() - 25): m.start()]

                # Önce sayısal değer aranır; yoksa muafiyet ifadesi kontrol edilir.
                mm = re.search(rf"^[^.;]{{0,20}}?({NUM}){SCALE}\s*(?:TL|₺)", window)
                if mm:
                    val = _amount_from_match(mm.group(1), mm.group(2))
                    if val is not None:
                        c.add(field, val, m, 0.92, ExtractionMethod.HYBRID)
                        break

                mp = re.search(rf"^[^.;]{{0,15}}?%\s*({NUM})", window)
                if mp:
                    val = parse_number(mp.group(1))
                    if val is not None and val <= 20:
                        c.add(field, val, m, 0.90, ExtractionMethod.HYBRID)
                        if field == "allocation_fee":
                            c.fields["allocation_fee_is_rate"] = True
                        break

                clause = window.split(".")[0]
                if WAIVER_RE.search(clause) or re.search(r"\b(ücretsiz|sıfır)\b", pre, re.I):
                    c.add(field, 0.0, m, 0.95, ExtractionMethod.ONTOLOGY)
                    break
            if field in c.fields:
                break

    # Kapsayıcı muafiyet ifadeleri → fee_waiver
    m = GLOBAL_WAIVER_RE.search(text)
    if m:
        c.add("fee_waiver", True, m, 0.94, ExtractionMethod.ONTOLOGY)


# ---------------------------------------------------------------------------
# 5. Kampanya kazançları
# ---------------------------------------------------------------------------
def extract_rewards(text: str, c: _Collector) -> None:
    for pattern, field, conf in [
        (rf"({NUM}){SCALE}\s*(?:TL|₺)\s*(?:'?ye|'?ya)?\s*(?:varan\s*)?(?:nakit\s*iade|iade|para\s*iadesi|cashback)",
         "reward_amount", 0.95),
        (rf"(?:nakit\s*iade|cashback|para\s*iadesi|iade)[^\d]{{0,25}}({NUM}){SCALE}\s*(?:TL|₺)",
         "reward_amount", 0.94),
        (rf"({NUM}){SCALE}\s*(?:TL|₺)\s*(?:'?ye|'?ya)?\s*(?:varan\s*)?(?:para\s*puan|parapuan|bonus)",
         "shopping_points", 0.94),
        (rf"(?:para\s*puan|parapuan|bonus\s*puan|chip\s*para)[^\d]{{0,25}}({NUM}){SCALE}\s*(?:TL|₺)",
         "shopping_points", 0.92),
        (rf"({NUM}){SCALE}\s*(?:TL|₺)\s*(?:'?lik|'?lık)?\s*(?:hediye|ödül|promosyon)",
         "reward_amount", 0.88),
    ]:
        m = re.search(pattern, text, re.I)
        if m:
            val = _amount_from_match(m.group(1), m.group(2))
            if val:
                c.add(field, val, m, conf)

    m = re.search(rf"%\s*({NUM})\s*(?:indirim|'?lik indirim)", text, re.I)
    if m:
        val = parse_number(m.group(1))
        if val is not None and val <= 100:
            c.add("discount_rate", val, m, 0.93)


# ---------------------------------------------------------------------------
# 6. Tarihler
# ---------------------------------------------------------------------------
def _parse_date(txt: str) -> date | None:
    txt = txt.strip()
    m = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", txt)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    m = re.match(r"(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})", txt)
    if m:
        mon = MONTHS_TR.get(m.group(2).lower())
        if mon:
            try:
                return date(int(m.group(3)), mon, int(m.group(1)))
            except ValueError:
                return None
    return None


DATE_TOKEN = r"\d{1,2}[./]\d{1,2}[./]\d{4}|\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4}"


def extract_dates(text: str, c: _Collector) -> None:
    m = re.search(rf"({DATE_TOKEN})\s*[-–—]\s*({DATE_TOKEN})", text)
    if m:
        d1, d2 = _parse_date(m.group(1)), _parse_date(m.group(2))
        if d1:
            c.add("campaign_start_date", d1, m, 0.95)
        if d2:
            c.add("campaign_end_date", d2, m, 0.95)
        return

    m = re.search(rf"({DATE_TOKEN})\s*(?:tarihine kadar|'?e kadar|'?a kadar|son(?:una)? kadar)", text, re.I)
    if m:
        d = _parse_date(m.group(1))
        if d:
            c.add("campaign_end_date", d, m, 0.93)

    m = re.search(rf"({DATE_TOKEN})\s*(?:tarihinden itibaren|'?den itibaren|'?dan itibaren)", text, re.I)
    if m:
        d = _parse_date(m.group(1))
        if d:
            c.add("campaign_start_date", d, m, 0.92)


# ---------------------------------------------------------------------------
# 7. Koşullar
# ---------------------------------------------------------------------------
CONDITION_MARKERS = [
    "şartıyla", "koşuluyla", "geçerlidir", "gereklidir", "olmak kaydıyla",
    "ilk kez", "yeni müşteri", "maaş müşterisi", "başvuru yapan", "sadece",
    "hariç", "asgari", "en az", "dahil değildir", "geçerli değildir",
]


def extract_conditions(text: str) -> list[str]:
    from nlp.cleaner import split_sentences

    out = []
    for sent in split_sentences(text):
        low = sent.lower()
        if any(mk in low for mk in CONDITION_MARKERS):
            s = sent.strip()
            if 15 < len(s) < 260 and s not in out:
                out.append(s)
    return out[:8]


# ---------------------------------------------------------------------------
# Ana API
# ---------------------------------------------------------------------------
def extract_entities(text: str) -> dict:
    """
    Metinden tüm finansal varlıkları çıkarır.

    Dönüş:
        {
          "fields": {...},                 # şemaya doğrudan beslenebilir
          "evidence": [Evidence, ...],
          "ontology_hits": [...],
          "confidence": float
        }
    """
    if not text:
        return {"fields": {}, "evidence": [], "ontology_hits": [], "confidence": 0.0}

    text = onto.map_conventional_terms(text)
    c = _Collector(text)

    extract_profit_rate(text, c)
    extract_profit_rate_fallback(text, c)
    extract_amounts(text, c)
    extract_maturity(text, c)
    extract_fees(text, c)
    extract_rewards(text, c)
    extract_dates(text, c)

    c.fields["currency"] = detect_currency(text)
    conditions = extract_conditions(text)
    if conditions:
        c.fields["conditions"] = conditions

    hits = onto.detect_concepts(text)

    # Güven skoru: alan kanıtlarının ağırlıklı ortalaması + ontoloji desteği
    if c.evidence:
        base = sum(e.confidence for e in c.evidence) / len(c.evidence)
    else:
        base = 0.0
    onto_bonus = min(0.06, 0.015 * len(hits))
    confidence = round(min(0.995, base + onto_bonus), 3)

    return {
        "fields": c.fields,
        "evidence": c.evidence,
        "ontology_hits": hits,
        "confidence": confidence,
    }
