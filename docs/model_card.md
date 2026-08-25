# SEZARNEXT — Model Card

Sürüm: **1.1** · Tarih: 25.08.2026

Bu belge, SEZARNEXT'in ne yaptığını, neyi yapmadığını ve ölçüm sonuçlarının
hangi koşullarda geçerli olduğunu açıkça ortaya koyar. Jüri, denetçi veya
kurumsal değerlendirici için birincil referans budur.

---

## 1. Sistemin tanımı

SEZARNEXT, Türkçe katılım bankacılığı metinlerinden finansal bilgi çıkaran,
bankaları net ekonomik maliyete göre karşılaştıran ve sonucu kanıtla birlikte
sunan bir karar destek sistemidir.

- **Yaklaşım:** Hybrid Neuro-Symbolic (kural motoru + ontoloji + sınıflandırıcı
  + opsiyonel yerel LLM + finansal hesaplama)
- **Üretken model kullanımı:** yalnızca doğrulama amaçlı, opsiyonel ve yereldir.
  Sistem sayı üretmek için dil modeli kullanmaz.
- **Çalışma yeri:** tamamen kurum içi (on-premise). Harici yapay zekâ API'si yok.

## 2. Kullanım amacı

**Amaçlanan kullanım**
- Katılım bankası ürün ve kampanyalarının otomatik izlenmesi
- Finansman tekliflerinin net ekonomik maliyet üzerinden karşılaştırılması
- Banka içi ürün konumlandırma ve rekabet analizi
- Finansal metinden yapılandırılmış veri üretimi (araştırma / veri altyapısı)

**Amaçlanmayan kullanım**
- Yatırım, finansman veya kredi tavsiyesi vermek
- Müşteriye bağlayıcı teklif veya fiyat sunmak
- Bireysel kredi uygunluk / risk değerlendirmesi yapmak
- Bankaların resmî oranlarının doğrulanmış kaynağı olarak kullanılmak

SEZARNEXT bir **karar destek** aracıdır, karar verici değildir. Çıktıları
finansal tavsiye niteliği taşımaz; nihai bilgi için bankanın resmî kaynağı
esastır.

## 3. Veri

### 3.1 Demo verisi — SENTETİK

Depoda gelen `data/processed/campaigns.json` **tamamen sentetiktir**.

- Banka adları anonimleştirilmiştir (A Katılım, B Katılım, …).
- Oran, tutar, vade ve kampanya bilgileri **gerçek değildir**; hiçbir gerçek
  bankanın gerçek teklifini temsil etmez.
- Her kayıtta `is_synthetic: true` bayrağı vardır ve tüm çıktılarda
  `[DEMO VERİSİ]` uyarısı gösterilir.

Amaç, ağ erişimi olmadan tüm zinciri (Extract → Compare → Agent → Evidence)
uçtan uca çalıştırabilmektir.

### 3.2 Kurumsal liste — kamuya açık

`collectors/bddk_collector.py` içindeki katılım bankası listesi kamuya açık
kurumsal bilgidir ve yalnızca **kurum keşfi** için kullanılır. Bu listedeki
gerçek banka adları, demo verisindeki sentetik oranlarla **ilişkilendirilmemiştir**.

### 3.3 Canlı veri

Canlı toplama (`python -m demo.run_collect`) robots.txt kurallarına uyar, hız
sınırlar ve ham sayfayı tarih damgasıyla arşivler. Canlı veri kullanıldığında
`is_synthetic` bayrağı `false` olur ve demo uyarısı kalkar.

## 4. Değerlendirme

### 4.1 Değerlendirme kümesi

`benchmark/gold_dataset.csv` — 60 dev + 12 held-out test örneği, elle etiketlenmiş.

**Bu küme sentetiktir ve proje ekibi tarafından yazılmıştır.** Gerçek banka
duyurularının dilsel yapısını taklit eder (yazım varyantları, yazıyla sayılar,
tuzak ifadeler) ancak gerçek dünya dağılımını temsil ettiği **kanıtlanmamıştır**.

### 4.2 Sonuçlar (v1.1, held-out test kümesi, n=12)

| Metrik | Sonuç | Hedef | Durum |
|---|---|---|---|
| Ürün sınıflandırma Macro-F1 | 0,9444 | ≥ 0,90 | PASS |
| Kampanya sınıflandırma Macro-F1 | 1,0000 | ≥ 0,90 | PASS |
| Entity extraction F1 | 1,0000 | ≥ 0,93 | PASS |
| Kâr payı exact match | 1,0000 | ≥ 0,95 | PASS |
| Tutar exact match | 1,0000 | ≥ 0,95 | PASS |
| Vade exact match | 1,0000 | ≥ 0,95 | PASS |
| Hallucination rate | 0,0000 | ≤ 0,01 | PASS |
| Evidence coverage | 1,0000 | ≥ 0,98 | PASS |

Dev kümesi (n=60): extraction F1 1,0000 · kampanya Macro-F1 0,9383 ·
ürün Macro-F1 0,9828.

### 4.3 Bu sonuçlar nasıl okunmalı — ÖNEMLİ

Yukarıdaki tablo **üst sınır** niteliğindedir ve genelleme performansı
olarak sunulmamalıdır. Üç neden:

1. **Dev kümesi geliştirmede kullanıldı.** Regex desenleri ve ontoloji
   sinyalleri bu küme üzerindeki hatalara bakılarak iyileştirildi. Dev
   sonuçları tanım gereği optimistiktir.

2. **Test kümesi artık tam anlamıyla held-out değildir.** İlk held-out koşusu
   (**v1.0**) `benchmark/benchmark_results_v1.0_frozen.json` içinde
   dondurulmuştur ve şu sonucu vermiştir:

   | Metrik | v1.0 (gerçek held-out) |
   |---|---|
   | Entity extraction F1 | **0,9667** |
   | Tutar exact match | 0,9000 |
   | Kampanya sınıflandırma Macro-F1 | **0,7900** |

   Bu koşuda ortaya çıkan iki gerçek hata (`"İki yüz bin"` ifadesinde Türkçe
   `'İ'.lower()` kaynaklı kelime bölünmesi; kampanya sınıflandırıcısının
   Türkçe çekim varyantlarını kaçırması) giderildi. Düzeltme test kümesine
   bakılarak yapıldığı için v1.1 test sonuçları artık bağımsız değildir.

3. **v1.2 için yeni bir held-out küme yazılmalıdır.** Bu, açık bir eksiktir
   ve yol haritasında yer almaktadır.

### 4.4 Gerçek doğrulama için gereken

Güvenilir bir performans beyanı için, canlı banka sayfalarından alınmış
metinlerin bağımsız bir kişi tarafından elle etiketlenmesi ve modele hiç
gösterilmemiş bu küme üzerinde tek seferlik ölçüm yapılması gerekir. Bu
çalışma **henüz yapılmamıştır**.

## 5. Bilinen sınırlar ve hata modları

| Sınır | Etki |
|---|---|
| Vade bazlı oran tabloları (24/36/48 ay için farklı oranlar) tek orana indirgenir | Uzun vadelerde maliyet olduğundan düşük görünebilir |
| Metinde yazılmayan sigorta/kasko bedelleri hesaba katılmaz | Net maliyet **alt sınır** niteliğindedir |
| Yazıyla ifade edilen oranlar sınırlı desteklenir | Nadir formatlarda oran kaçırılabilir |
| Kampanya koşulları çıkarılır ama otomatik değerlendirilmez | Uygunluk kararı kullanıcıya aittir |
| Ontoloji sabit sözlüktür | Yeni ürün adları elle eklenmelidir |
| Banka sayfa yapısı değişirse adaptör bozulabilir | Hash tabanlı değişiklik takibi uyarı üretir, otomatik onarım yoktur |
| Değerlendirme kümesi sentetiktir | Gerçek dünya performansı bilinmemektedir |

## 6. Hallucination kontrolü

Dört katman:

1. **Kanıt zorunluluğu** — kanıt aralığı üretilmeyen sayısal alan şemaya
   girmez (`enforce_evidence`).
2. **Kural doğrulaması** — oran 0–20, vade 1–360, min ≤ max, tarih sırası.
3. **Türetilmiş sayı yasağı** — yıllık oran aylığa bölünerek türetilmez;
   türetilen sayı kaynak metinde geçmediği için kanıtlanamaz.
4. **Şablon üretimi** — SEZAR'ın cevabındaki her sayı motordan gelir; serbest
   metin üretimi kullanılmaz. Yerel LLM açıksa yalnızca onay/ret verir.

Ölçülen hallucination oranı 0,0000'dır; ancak bu, metrik tanımının
(*"üretilen değer kaynak metindeki bir sayıdan türetilebiliyor mu"*) sınırları
içinde geçerlidir. Doğru sayının **yanlış alana** yazılması bu metrikle
yakalanmaz; onu exact match metrikleri ölçer.

## 7. Adillik, gizlilik ve uyum

- Sistem kişisel veri işlemez; yalnızca kamuya açık ürün/kampanya sayfalarını okur.
- Tarama robots.txt kurallarına uyar ve hız sınırlar.
- Tüm işlem kurum içinde yapılır; veri üçüncü taraf bir modele gönderilmez.
- Sıralama tek bir bankayı kayıran gizli bir ağırlık içermez; ağırlık profilleri
  `engine/ranking_engine.py` içinde açıkça tanımlıdır ve denetlenebilir.
- Karşılaştırma sonucu, kullanıcı önceliğine (`net_cost`, `cash_flow`,
  `upfront`, `balanced`) göre değişir; tek bir "doğru sıralama" iddiası yoktur.

## 8. Sorumluluk beyanı

SEZARNEXT finansal tavsiye vermez. Ürettiği karşılaştırmalar, kaynak
sayfalardaki bilginin doğru okunmasına ve o bilginin güncel olmasına bağlıdır.
Bankaların koşulları değişebilir; nihai ve bağlayıcı bilgi yalnızca ilgili
bankanın resmî kanallarından alınabilir.
