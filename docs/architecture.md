# SEZARNEXT — Mimari

## 1. Konumlandırma

SEZARNEXT, katılım bankalarının ürün, finansman ve kampanya içeriklerini otomatik
toplayan, Türkçe finansal metinlerden yapılandırılmış bilgi çıkaran, bankaları çok
kriterli biçimde karşılaştıran ve sonuçları açıklanabilir bir yapay zekâ ajanı
üzerinden sunan, **on-premise çalışabilen** finansal karar destek platformudur.

**Temel yaklaşım: Hybrid Neuro-Symbolic Financial AI**

```
Regex / Rule Engine + Katılım Bankacılığı Ontolojisi + NLP Modelleri
+ Local LLM + Finansal Hesaplama Motoru = SEZARNEXT
```

Sembolik katman sayıları çıkarır ve doğrular; sinirsel katman yalnızca *doğrulama*
ve *belirsizlik çözümü* için devreye girer. Bu ayrım, sistemin hallucination
oranını mimari olarak sınırlar: **LLM asla sayı üretmez, sadece onaylar veya reddeder.**

## 2. Veri akışı

```
                    BDDK / TKBB
              Katılım Bankaları Listesi
                         │
                         ▼
                SEZARNEXT CRAWLER  (robots.txt uyumlu, hash tabanlı değişiklik takibi)
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
      Kampanya Sayfaları        Ürün Sayfaları
            └────────────┬────────────┘
                         ▼
                  RAW FINANCIAL DATA  (data/raw, tarih damgalı arşiv)
                         │
                         ▼
        ┌─────────────────────────────────────┐
        │        SEZARNEXT NLP CORE           │
        ├─────────────────────────────────────┤
        │ cleaner.py        Text Cleaning     │
        │ normalizer.py     Numeric Norm.     │
        │ participation_    Ontology          │
        │   ontology.py                       │
        │ entity_           Entity Extraction │
        │   extractor.py    (+ evidence span) │
        │ campaign_         Classification    │
        │   classifier.py                     │
        │ semantic_         Validation        │
        │   validator.py    (+ Local LLM)     │
        └─────────────────────────────────────┘
                         │
                         ▼
                  PYDANTIC JSON  (schemas/campaign_schema.py)
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
   SEZARNEXT Benefit Engine   SEZARNEXT Knowledge Layer
   (net ekonomik maliyet)     (BM25 / vektör geri getirme)
            └────────────┬────────────┘
                         ▼
                   SEZAR AGENT
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
         Dashboard              REST API
```

## 3. Katmanlar ve sorumlulukları

| Katman | Dizin | Sorumluluk | Harici bağımlılık |
|---|---|---|---|
| Collect | `collectors/` | Banka keşfi, tarama, arşivleme, değişiklik takibi | requests, bs4 |
| Extract | `nlp/` | Temizleme, normalizasyon, ontoloji, varlık çıkarımı, sınıflandırma, doğrulama | yok (bs4 opsiyonel) |
| Schema | `schemas/` | Çıktı sözleşmesi, tip güvenliği | pydantic |
| Compare | `engine/` | Uygunluk, finansal matematik, fayda, sıralama | yok |
| Knowledge | `knowledge/` | Dizinleme, geri getirme, kanıt kartları | yok |
| Agent | `agent/` | Niyet çözümleme, orkestrasyon, yanıt üretimi | yok |
| Interface | `app/` | REST API, dashboard | fastapi, streamlit |

**Tasarım kararı:** karar üreten tüm katmanlar (Extract → Compare → Agent) saf
Python'dur. Ağ, model sunucusu veya vektör veritabanı kullanılamadığında sistem
düşük yetenekle çalışmaya devam eder (graceful degradation); sessizce yanlış
cevap üretmez.

## 4. Açıklanabilirlik zinciri

Her sayı, kaynağına kadar izlenebilir:

```
SEZAR cevabı
   → CostBreakdown (hangi kalem, ne kadar)
      → SezarNextCampaign (hangi banka, hangi ürün)
         → Evidence (hangi cümle, hangi karakter aralığı, hangi yöntem, hangi güven)
            → source_url + scraped_at (hangi sayfa, ne zaman)
```

`semantic_validator.enforce_evidence()` kanıtı olmayan sayısal alanı **düşürür**.
Yani kanıtlanamayan bir sayı sisteme hiç girmez.

## 5. SEZARNEXT Local AI Stack

```
Docker
├── FastAPI          (app/api.py)
├── Streamlit        (app/dashboard.py)
├── PostgreSQL       (kalıcı kayıt — şu an JSON store ile aynı arayüz)
├── Qdrant           (vektör arama — opsiyonel, BM25 varsayılan)
├── Ollama + Local LLM  (semantic validation — opsiyonel)
├── NLP Core
└── Benefit Engine
```

Harici yapay zekâ API'si yoktur. Tüm bileşenler kurum içinde çalışır; finansal
veri kurum sınırlarının dışına çıkmaz.
