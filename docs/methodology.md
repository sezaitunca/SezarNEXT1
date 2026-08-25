# SEZARNEXT — Yöntem

## 1. Neden hibrit (neuro-symbolic)?

Türkçe finansal metinde sayılar yüksek çeşitlilikte yazılır:

```
750.000 TL   |  750 bin TL  |  yedi yüz elli bin lira  |  1,5 milyon
%2,05        |  yüzde 2,05  |  %2.05                   |  yüzde iki virgül beş
36 ay        |  3 yıl       |  otuz altı ay            |  12-48 ay
```

Saf LLM yaklaşımı bu sayıları *yeniden üretir* ve üretim sırasında hata yapabilir
(bir basamak kayması, kampanya ödülünün finansman limiti sanılması). Finansal karar
desteğinde bu kabul edilemez.

SEZARNEXT bu yüzden şu iş bölümünü uygular:

| Görev | Katman | Gerekçe |
|---|---|---|
| Sayı çıkarma | Regex + kural motoru | Deterministik, denetlenebilir, kanıt aralığı üretir |
| Terim anlama | Ontoloji | Katılım bankacılığı terminolojisi kapalı bir sözlüktür |
| Sınıflandırma | Ağırlıklı sinyal + regex kalıpları | Az veriyle çalışır, kararı açıklanabilir |
| Belirsizlik çözümü | Yerel LLM | Yalnızca *onay/ret*; yeni değer üretmez |
| Hesaplama | Finansal matematik | Kapalı form formüller, LLM'e bırakılmaz |
| Açıklama | Şablon üretimi | Her cümle bir motor çıktısına bağlıdır |

## 2. Normalizasyon konvansiyonları

Etiketleme ve çıkarımda tutarlılık için sabitlenmiş kurallar:

- `profit_rate` **aylık** kâr payı oranıdır (%). Yıllık oran ayrı alandır
  (`annual_cost_rate`) ve **12'ye bölünerek aylığa çevrilmez** — türetilen sayı
  kaynak metinde geçmediği için kanıtlanamaz.
- Vade aralığı verilmişse (`12-48 ay`) **azami vade** alınır; uygunluk filtresi
  üst sınırla çalışır.
- Tutar aralığı (`300.000 TL ila 1.200.000 TL`) alt ve üst limite ayrılır.
- Ödül, para puan, çekiliş ve toplam geri ödeme tutarları **finansman limiti
  sayılmaz** (negatif bağlam filtresi).
- Bir ücret kaleminin muaf olması diğer kalemleri etkilemez; genel muafiyet
  (`fee_waiver`) yalnızca kapsayıcı ifadelerle (`masrafsız`, `hiçbir ücret
  alınmaz`) işaretlenir.

## 3. Benefit Engine — net ekonomik maliyet

Karşılaştırma sitelerinin çoğu yalnızca oran sıralar. Oran tek başına yanıltıcıdır:
ücretler, kampanya kazançları ve ödemenin zamanlaması sonucu tersine çevirebilir.

```
Finansman Maliyeti (toplam kâr payı yükü)
  + Tahsis ücreti + Ekspertiz + Sigorta + Diğer masraflar
  - Nakit iade        (bugünkü değere indirgenmiş)
  - Para puan         (nakde dönüşüm katsayısı 0,95)
  - Oran indirimi
  - Ücret muafiyeti
  ────────────────────────────────────────────
  = NET EKONOMİK MALİYET
```

Taksit, murabaha esaslı eşit taksit formülüyle hesaplanır:

```
T = P · r · (1+r)^n / ((1+r)^n − 1)        r = aylık kâr payı, n = vade
```

Peşin ücretler nakit akışına dahil edilerek **yıllık maliyet oranı** IRR ile
çözülür; bu, farklı ücret yapılarına sahip bankaları adil biçimde kıyaslar.

**Net Economic Benefit Score (0–100):** en düşük net maliyet 100, en yüksek 0.

Demo verisinde bu motorun ürettiği tipik sonuç şudur: **%1,97 kâr payı sunan bir
banka, %1,79 sunan bankayı yenebilir** — çünkü kampanya kazançları oran farkını
aşar. Bu, projenin temel farklılaştırıcısıdır.

## 4. Sıralama profilleri

Kullanıcının önceliği tek değildir. `engine/ranking_engine.py` dört ağırlık profili
sunar: `net_cost` (varsayılan), `cash_flow` (aylık taksit yükü), `upfront` (peşin
masraf), `balanced`. Sorgu yönlendirici, kullanıcının ifadesinden profili seçer
("aylık taksiti en düşük" → `cash_flow`).

## 5. Hallucination kontrolü

Üç bağımsız savunma katmanı:

1. **Kanıt zorunluluğu** — kanıt aralığı üretilmeyen sayısal alan şemaya girmez.
2. **Kural doğrulaması** — aralık ve tutarlılık kuralları (oran 0–20, vade 1–360,
   min ≤ max, tarih sırası).
3. **Şablon üretimi** — SEZAR'ın cevabındaki her sayı motordan gelir; serbest metin
   üretimi kullanılmaz.

Yerel LLM açıksa dördüncü katman olarak alan bazlı onay/ret kararı ekler.

## 6. Bilinen sınırlar

- Yazıyla ifade edilen oranlar (`yüzde iki virgül seksen dokuz`) sınırlı desteklenir.
- Tablo biçimli oran listeleri (24 ay / 36 ay / 48 ay ayrı oranlar) tek orana indirgenir.
- Sigorta ve kasko bedelleri metinde açıkça yazılmadıkça hesaba katılmaz;
  sistem tahmin üretmez, bu nedenle net maliyet **alt sınır** niteliğindedir.
- Kampanya koşulları (uygunluk şartları) çıkarılır ama otomatik olarak
  değerlendirilmez; kullanıcıya gösterilir.
