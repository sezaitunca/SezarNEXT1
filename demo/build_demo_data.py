"""
SEZARNEXT — Demo Veri Üreteci
=============================
ÖNEMLİ: Buradaki metinler SENTETİK'tir. Gerçek banka oranları değildir.
Bankalar anonimleştirilmiştir (A/B/C... Katılım). Amaç, NLP Core → Benefit
Engine → SEZAR Agent zincirini ağ erişimi olmadan uçtan uca çalıştırmaktır.

Canlı veri için: `python -m demo.run_collect` (crawler + adapters).

Çalıştırma:
    python -m demo.build_demo_data
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collectors.store import save_campaigns  # noqa: E402
from nlp.pipeline import run_pipeline  # noqa: E402

BASE = datetime(2026, 8, 25, 15, 20)

# (banka, ürün adı, url yolu, ham kampanya metni)
CORPUS: list[tuple[str, str, str, str]] = [
    # ---------------- Taşıt finansmanı ----------------
    ("A Katılım", "Sıfır Araç Taşıt Finansmanı", "/kampanya/sifir-arac",
     "Sıfır araç alımlarında 750.000 TL'ye kadar 36 ay vadeli, aylık %1,89 kâr payı oranıyla "
     "taşıt finansmanı fırsatı. Kampanya kapsamında tahsis ücreti alınmaz. 15.000 TL'ye varan "
     "nakit iade kazanın. Kampanya 01.08.2026 - 31.10.2026 tarihleri arasında geçerlidir. "
     "Yeni müşteri olmak şartıyla geçerlidir."),
    ("B Katılım", "Taşıt Finansmanı Avantaj Paketi", "/urun/tasit-finansmani",
     "İkinci el ve sıfır araç için 1.000.000 TL'ye kadar finansman. 24 ay vadelerde aylık "
     "%1,92 kâr payı oranı uygulanır. Tahsis ücreti 7.500 TL'dir. Ekspertiz ücreti alınmaz. "
     "Başvurunun onaylanması gereklidir."),
    ("C Katılım", "Hızlı Taşıt Finansmanı", "/kampanyalar/hizli-tasit",
     "Aylık yüzde 1,79 kâr payı oranıyla 500 bin TL'ye kadar taşıt finansmanı. Vade 24 ay. "
     "Dosya masrafı %0,5 oranında uygulanır. 5.000 TL para puan hediye. "
     "31 Aralık 2026 tarihine kadar geçerlidir."),
    ("D Katılım", "Elektrikli Araç Finansmanı", "/kampanya/elektrikli-arac",
     "Elektrikli ve hibrit araçlarda 1.500.000 TL'ye kadar, 48 aya varan vadelerle aylık "
     "%2,05 kâr payı. Masrafsız kullandırım, sıfır tahsis ücreti. Sadece elektrikli araçlar "
     "için geçerlidir."),
    ("E Katılım", "Taşıt Finansmanı Kampanyası", "/tasit",
     "Taşıt finansmanında 600.000 TL'ye kadar 30 ay vade, aylık %1,95 kâr payı oranı. "
     "Tahsis ücreti 4.500 TL. 10.000 TL nakit iade fırsatı. Maaş müşterisi olmak koşuluyla."),
    ("F Katılım", "Araç Finansman Desteği", "/finansman/arac",
     "Aylık %1,85 kâr payı oranıyla 800.000 TL'ye kadar araç finansmanı. 36 ay vadeli. "
     "Tahsis ücreti 9.000 TL'dir. Kasko yaptırma şartıyla geçerlidir."),
    ("G Katılım", "Taşıt Finansmanı Özel Teklif", "/ozel/tasit",
     "24 aya kadar vadelerde aylık %1,88 kâr payı ile 550.000 TL taşıt finansmanı. "
     "Dosya masrafı alınmaz. 8.000 TL'ye varan para puan kazanma fırsatı. "
     "Kampanya 15.07.2026 - 30.11.2026 arasında geçerlidir."),
    ("H Katılım", "İkinci El Taşıt Finansmanı", "/tasit/ikinci-el",
     "İkinci el araç alımlarında 450.000 TL'ye kadar, 24 ay vadeli, aylık %2,10 kâr payı. "
     "Tahsis ücreti %0,75 oranındadır. Aracın 10 yaşından küçük olması gereklidir."),
    ("I Katılım", "Taşıt Finansmanı", "/urunler/tasit-finansmani",
     "Taşıt finansmanı kapsamında en az 100.000 TL, en fazla 2.000.000 TL tutarında "
     "kullandırım yapılır. 60 aya kadar vade seçenekleri mevcuttur. Aylık kâr payı oranı "
     "%2,25'ten başlar. Tahsis ücreti 12.000 TL."),
    ("J Katılım", "Yeşil Taşıt Finansmanı", "/yesil-tasit",
     "Çevre dostu araçlarda 900.000 TL'ye kadar 36 ay vadeli finansman. Aylık %1,97 kâr payı "
     "oranı. Ekspertiz ücreti 2.500 TL. 12.000 TL nakit iade. %10 indirim uygulanır."),
    ("K Katılım", "Taşıt Finansmanı Fırsatı", "/kampanya/tasit-firsat",
     "500.000 TL'ye kadar taşıt finansmanında aylık %1,91 kâr payı, 24 ay vade. "
     "Hiçbir ücret alınmaz, masrafsızdır. 6.000 TL para puan avantajı."),
    ("A Katılım", "İkinci El Araç Finansmanı", "/kampanya/ikinci-el-arac",
     "İkinci el araçlarda 400.000 TL'ye kadar 24 ay vadeli finansman, aylık %2,15 kâr payı "
     "oranıyla. Tahsis ücreti 5.000 TL'dir."),
    ("C Katılım", "Motosiklet Finansmanı", "/kampanya/motosiklet",
     "Motosiklet alımlarında 150.000 TL'ye kadar 18 ay vade, aylık %2,30 kâr payı. "
     "Tahsis ücreti alınmaz."),

    # ---------------- Konut finansmanı ----------------
    ("A Katılım", "Konut Finansmanı Kampanyası", "/kampanya/konut",
     "Konut finansmanında 5.000.000 TL'ye kadar 120 ay vadeli, aylık %2,49 kâr payı oranı. "
     "Ekspertiz ücreti 8.500 TL. DASK zorunludur. Tapu işlemleri müşteriye aittir."),
    ("B Katılım", "Ev Sahibi Ol Konut Finansmanı", "/konut-finansmani",
     "10 milyon TL'ye kadar konut finansmanı, 180 aya varan vade, aylık %2,39 kâr payı. "
     "Tahsis ücreti %0,5. Ekspertiz ücreti alınmaz."),
    ("D Katılım", "İlk Evim Konut Finansmanı", "/ilk-evim",
     "İlk kez ev alacaklara özel 3.000.000 TL'ye kadar 120 ay vadeli konut finansmanı. "
     "Aylık %2,29 kâr payı oranı. 25.000 TL nakit iade. İlk kez konut alıyor olmak şartıyla."),
    ("F Katılım", "Konut Finansmanı", "/urunler/konut",
     "Konut finansmanı 8.000.000 TL'ye kadar kullandırılır. Vade 240 aya kadardır. "
     "Aylık kâr payı oranı %2,55. Ekspertiz ücreti 9.000 TL, tahsis ücreti 15.000 TL."),

    # ---------------- İhtiyaç finansmanı ----------------
    ("C Katılım", "İhtiyaç Finansmanı", "/ihtiyac-finansmani",
     "İhtiyaç finansmanında 300.000 TL'ye kadar 36 ay vade, aylık %3,19 kâr payı. "
     "Tahsis ücreti %0,4 oranındadır."),
    ("E Katılım", "Bireysel Finansman Desteği", "/bireysel-finansman",
     "200.000 TL'ye kadar bireysel finansman, 24 ay vadeli, aylık %3,29 kâr payı oranıyla. "
     "Masrafsız. 3.000 TL nakit iade."),
    ("G Katılım", "İhtiyaç Finansmanı Fırsatı", "/kampanya/ihtiyac",
     "Aylık %2,99 kâr payı ile 250.000 TL'ye kadar ihtiyaç finansmanı. 36 ay vade. "
     "Dosya masrafı 3.500 TL. İlk taksit 3 ay sonra, ödemesiz dönem avantajı."),
    ("H Katılım", "Nakit İhtiyaç Finansmanı", "/nakit-ihtiyac",
     "150.000 TL'ye kadar 12 ay vadeli nakit ihtiyaç finansmanı. Aylık %3,45 kâr payı. "
     "Tahsis ücreti 2.000 TL."),

    # ---------------- Kredi kartı ----------------
    ("A Katılım", "Katılım Kart Alışveriş Kampanyası", "/kart/alisveris",
     "Market ve akaryakıt harcamalarında 2.500 TL'ye varan para puan kazanın. "
     "Kart aidatı alınmaz, aidatsızdır. Kampanya 01.09.2026 - 31.12.2026 arasında geçerlidir. "
     "Ayda en az 5.000 TL harcama yapılması gereklidir."),
    ("B Katılım", "Kredi Kartı Nakit İade Kampanyası", "/kart/nakit-iade",
     "Online alışverişlerde %10 indirim ve 1.500 TL nakit iade fırsatı. "
     "Taksitli alışverişte 3 ek taksit. Sadece yeni kart sahipleri için geçerlidir."),
    ("D Katılım", "Seyahat Kartı Kampanyası", "/kart/seyahat",
     "Yurt dışı harcamalarında 5.000 TL'ye varan para puan. Aidatsız kredi kartı. "
     "Havalimanı lounge hizmeti hediye."),
    ("I Katılım", "Kart Taksit Fırsatı", "/kart/taksit",
     "Beyaz eşya ve elektronikte peşin fiyatına 9 taksit fırsatı. 2.000 TL para puan hediye. "
     "Kampanya 30.09.2026 tarihine kadar geçerlidir."),

    # ---------------- Katılma hesabı / yatırım ----------------
    ("A Katılım", "Katılma Hesabı Kampanyası", "/katilma-hesabi",
     "32 gün vadeli katılma hesabında yıllık %42 kâr payı oranı. En az 50.000 TL "
     "ile hesap açılışı gereklidir. Yeni müşterilere özeldir."),
    ("C Katılım", "Altın Birikim Hesabı", "/altin-hesabi",
     "Gram altın birikim hesabı ile altın biriktirin. En az 1 gram altın ile başlayabilirsiniz. "
     "Hesap işletim ücreti alınmaz."),
    ("E Katılım", "Kira Sertifikası Halka Arzı", "/sukuk",
     "Kira sertifikası halka arzında en az 10.000 TL ile katılım sağlayabilirsiniz. "
     "Vade 6 aydır. Yıllık %45 kâr payı öngörülmektedir."),
    ("F Katılım", "Ödüllü Katılma Hesabı", "/odullu-hesap",
     "Katılma hesabı açanlara çekilişle 100.000 TL ödül. En az 25.000 TL bakiye gereklidir."),

    # ---------------- KOBİ / işyeri ----------------
    ("B Katılım", "KOBİ İşletme Finansmanı", "/kobi-finansmani",
     "KOBİ'lere 5.000.000 TL'ye kadar 48 ay vadeli işletme finansmanı. Aylık %2,75 kâr payı. "
     "Tahsis ücreti %0,3."),
    ("G Katılım", "Esnaf Destek Finansmanı", "/esnaf-destek",
     "Esnaf ve sanatkârlara 750.000 TL'ye kadar 36 ay vadeli finansman, aylık %2,65 kâr payı "
     "oranıyla. Dosya masrafı alınmaz."),
    ("J Katılım", "İşyeri Finansmanı", "/isyeri-finansmani",
     "İşyeri alımlarında 4.000.000 TL'ye kadar 120 ay vade. Aylık %2,85 kâr payı. "
     "Ekspertiz ücreti 11.000 TL."),
]


def build() -> list:
    campaigns = []
    for i, (bank, product, path, text) in enumerate(CORPUS):
        slug = bank.split()[0].lower()
        result = run_pipeline(
            raw_text=text,
            bank=bank,
            source_url=f"https://demo.sezarnext.local/{slug}{path}",
            product_name=product,
            scraped_at=BASE - timedelta(hours=i % 12),
            is_synthetic=True,
        )
        if result.campaign is not None:
            campaigns.append(result.campaign)
        else:
            print(f"  ! şema hatası: {bank} / {product} → {result.validation_errors}")
    return campaigns


def main() -> None:
    print("SEZARNEXT — demo veri üretimi (SENTETİK)")
    print("-" * 60)
    campaigns = build()
    path = save_campaigns(campaigns)
    print(f"{len(campaigns)}/{len(CORPUS)} kayıt üretildi → {path}")

    from collections import Counter

    by_type = Counter(c.product_type.value for c in campaigns)
    for k, v in by_type.most_common():
        print(f"  {k:<24}{v}")
    rates = [c.profit_rate for c in campaigns if c.profit_rate]
    print(f"  kâr payı çıkarılan kayıt : {len(rates)}/{len(campaigns)}")
    print(f"  ortalama confidence      : "
          f"{sum(c.confidence_score for c in campaigns)/max(1,len(campaigns)):.3f}")


if __name__ == "__main__":
    main()
