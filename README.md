# SEZARNEXT

**Explainable AI for Participation Finance Intelligence**

Katılım bankalarının ürün, finansman ve kampanya verilerini otomatik toplayan,
Türkçe finansal metinden yapılandırılmış bilgi çıkaran, bankaları **net ekonomik
maliyet** üzerinden karşılaştıran ve her cevabını kanıtla sunan, tamamen kurum
içinde çalışabilen bir finansal karar destek platformu.

> SEZARNEXT bir chatbot değildir. Katılım finansını veriden karara dönüştüren
> açıklanabilir bir yapay zekâ ajanıdır.

---

## Neden farklı

Karşılaştırma araçlarının çoğu oran sıralar. Oran tek başına yanıltıcıdır.

SEZARNEXT'in **Benefit Engine**'i gerçek ekonomik sonucu hesaplar:

```
Finansman maliyeti + ücretler + masraflar
  − kampanya kazançları − ödüller − muafiyetler
  ────────────────────────────────────────────
  = NET EKONOMİK MALİYET
```

Demo verisinde ürettiği tipik sonuç: **%1,97 kâr payı sunan banka, %1,79 sunan
bankayı yener** — çünkü kampanya kazançları oran farkını aşar. Sistem bunu
hesaplar, gerekçesini yazar ve kaynağını gösterir.

## Mimari

**Hybrid Neuro-Symbolic Financial AI**

```
Regex / Rule Engine + Katılım Ontolojisi + NLP + Local LLM + Finansal Hesaplama
```

```
BDDK Listesi → Crawler → Raw Data → SEZARNEXT NLP Core → Pydantic JSON
                                          │
                        ┌─────────────────┴─────────────────┐
                   Benefit Engine                    Knowledge Layer
                        └─────────────────┬─────────────────┘
                                    SEZAR Agent
                                          │
                            Dashboard  ·  REST API
```

Karar üreten tüm katmanlar saf Python'dur. **LLM asla sayı üretmez, sadece
onaylar veya reddeder** — bu, hallucination oranını mimari olarak sınırlar.

Ayrıntı: [`docs/architecture.md`](docs/architecture.md) ·
[`docs/methodology.md`](docs/methodology.md) ·
[`docs/model_card.md`](docs/model_card.md)

## Kurulum

```bash
git clone <repo> && cd SEZARNEXT
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Çekirdek yalnızca `pydantic` gerektirir; ağ, vektör veritabanı veya model
sunucusu yoksa sistem düşük yetenekle çalışmaya devam eder.

## Çalıştırma

```bash
# 1) Demo verisini üret (sentetik, ağ gerektirmez)
python -m demo.build_demo_data

# 2) Jüri demosu — SEZARNEXT Live Decision Journey
python -m demo.scenarios.live_decision_journey

# 3) Dashboard
streamlit run app/dashboard.py

# 4) REST API
uvicorn app.api:app --reload

# 5) Benchmark
python -m benchmark.run_benchmark

# 6) Testler
pytest tests -q

# 7) Canlı toplama (ağ gerekir)
python -m demo.run_collect --dry-run
```

Docker ile tam yığın (API + dashboard + PostgreSQL + Qdrant + Ollama):

```bash
docker compose up --build
docker exec sezarnext-llm ollama pull qwen2.5:7b-instruct   # opsiyonel
```

## Benchmark Suite

Held-out test kümesi (n=12), v1.1:

| Metrik | Sonuç | Hedef | Durum |
|---|---|---|---|
| Ürün sınıflandırma Macro-F1 | 0,9444 | ≥ 0,90 | PASS |
| Kampanya sınıflandırma Macro-F1 | 1,0000 | ≥ 0,90 | PASS |
| Entity extraction F1 | 1,0000 | ≥ 0,93 | PASS |
| Kâr payı / tutar / vade exact match | 1,0000 | ≥ 0,95 | PASS |
| Hallucination rate | 0,0000 | ≤ 0,01 | PASS |
| Evidence coverage | 1,0000 | ≥ 0,98 | PASS |

**Dürüstlük notu.** Bu sayılar üst sınırdır, genelleme performansı değildir.
Gerçek held-out ilk koşusu (v1.0) extraction F1 **0,9667** ve kampanya Macro-F1
**0,7900** vermiştir; bu koşuda bulunan iki gerçek hata giderildiği için test
kümesi artık bağımsız değildir. v1.0 sonuçları
`benchmark/benchmark_results_v1.0_frozen.json` içinde dondurulmuştur.
Ayrıntılı gerekçe: [`docs/model_card.md`](docs/model_card.md) §4.

## Veri uyarısı

Depoyla gelen kampanya verisi **sentetiktir**. Banka adları anonimleştirilmiştir
(A Katılım, B Katılım, …); oran ve tutarlar gerçek değildir. Her kayıtta
`is_synthetic: true` bayrağı bulunur ve tüm çıktılarda `[DEMO VERİSİ]` uyarısı
gösterilir. `collectors/bddk_collector.py` içindeki gerçek banka listesi kamuya
açık kurumsal bilgidir ve sentetik oranlarla ilişkilendirilmemiştir.

SEZARNEXT finansal tavsiye vermez; bir karar destek aracıdır.

## Proje yapısı

```
SEZARNEXT/
├── app/            REST API (FastAPI) + Intelligence Dashboard (Streamlit)
├── collectors/     BDDK collector, bank discovery, crawler, bank adapters
├── nlp/            SEZARNEXT NLP Core (cleaner, normalizer, ontology,
│                   entity extractor, classifier, semantic validator, pipeline)
├── schemas/        SezarNextCampaign — Pydantic çıktı sözleşmesi
├── engine/         Financial math, Benefit Engine, Comparison, Ranking
├── knowledge/      Indexer (BM25), retriever, evidence cards
├── agent/          SEZAR Agent — query router, response generator
├── benchmark/      Gold dataset + değerlendirme + sonuçlar
├── demo/           Demo veri üretimi, canlı toplama, Live Decision Journey
├── tests/          51 test
├── docs/           architecture · methodology · model card
└── data/           raw · processed · benchmark
```

## Terminoloji

| Bileşen | Ad |
|---|---|
| NLP motoru | SEZARNEXT NLP Core |
| Karşılaştırıcı | Comparison Engine |
| Fayda motoru | Benefit Engine |
| Kanıt katmanı | Evidence |
| Değerlendirme | Benchmark Suite |
| Yerel mimari | Local AI Stack |
| Arayüz | Intelligence Dashboard |
| Ajan | SEZAR Agent |

## Lisans

MIT — bkz. [`LICENSE`](LICENSE)
