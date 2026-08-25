"""
SEZARNEXT Benchmark Suite — Gold Dataset Builder
================================================
Elle etiketlenmiş değerlendirme kümesini üretir.

ÖNEMLİ: Bu korpus demo verisinden BAĞIMSIZDIR (train/test ayrımı).
Metinler sentetiktir; gerçek banka duyurularının dilsel yapısını taklit eder:
farklı yazım varyantları, yazıyla sayılar, eksik alanlar ve tuzak ifadeler
(ör. ödül tutarının finansman limiti sanılması) bilinçli olarak eklenmiştir.

Boş hücre = alanın metinde bulunmadığı anlamına gelir; model de boş bırakmalıdır.

Çalıştırma:
    python -m benchmark.build_gold_dataset
"""

from __future__ import annotations

import csv
from pathlib import Path

OUT = Path("benchmark/gold_dataset.csv")

# (id, text, product_type, campaign_type, profit_rate, amount_max, maturity_months)
GOLD: list[tuple] = [
    ("g001", "Sıfır araç alımlarında 600.000 TL'ye kadar 36 ay vadeli, aylık %1,79 kâr payı oranıyla taşıt finansmanı.",
     "taşıt_finansmanı", "oran_indirimi", 1.79, 600000, 36),
    ("g002", "Taşıt finansmanında azami 1.200.000 TL tutarında kullandırım, 48 ay vade, aylık %2,15 kâr payı.",
     "taşıt_finansmanı", "diğer", 2.15, 1200000, 48),
    ("g003", "İkinci el araçta 350 bin TL'ye kadar finansman, 24 ay vadeli, aylık yüzde 2,45 kâr payı oranı.",
     "taşıt_finansmanı", "diğer", 2.45, 350000, 24),
    ("g004", "Araç kredisi kampanyamızda 900.000 TL'ye kadar 36 ay vade ve aylık %1,95 faiz oranı uygulanır.",
     "taşıt_finansmanı", "diğer", 1.95, 900000, 36),
    ("g005", "Elektrikli araç finansmanında tahsis ücreti alınmaz. 2.000.000 TL'ye kadar, 60 aya varan vade, aylık %2,05 kâr payı.",
     "taşıt_finansmanı", "ücret_muafiyeti", 2.05, 2000000, 60),
    ("g006", "Konut finansmanında 7.500.000 TL'ye kadar 180 ay vadeli, aylık %2,39 kâr payı oranı geçerlidir.",
     "konut_finansmanı", "diğer", 2.39, 7500000, 180),
    ("g007", "İlk evini alacaklara 3 milyon TL'ye kadar konut finansmanı, 120 ay vade, aylık %2,29 kâr payı.",
     "konut_finansmanı", "diğer", 2.29, 3000000, 120),
    ("g008", "Konut finansmanı kampanyasında ekspertiz ücreti alınmaz, dosya masrafı yoktur. 5.000.000 TL'ye kadar 15 yıl vade.",
     "konut_finansmanı", "ücret_muafiyeti", None, 5000000, 180),
    ("g009", "Mortgage ürünümüzde aylık %2,55 kâr payı ile 240 ay vadeye kadar 10.000.000 TL finansman.",
     "konut_finansmanı", "diğer", 2.55, 10000000, 240),
    ("g010", "İhtiyaç finansmanında 250.000 TL'ye kadar 36 ay vadeli, aylık %3,19 kâr payı oranı.",
     "ihtiyaç_finansmanı", "diğer", 3.19, 250000, 36),
    ("g011", "Bireysel finansman desteğinde 100 bin TL'ye kadar 12 ay vade, aylık %3,45 kâr payı.",
     "ihtiyaç_finansmanı", "diğer", 3.45, 100000, 12),
    ("g012", "Nakit ihtiyaç finansmanı: 180.000 TL'ye kadar, 24 ay vadeli, aylık %2,99 kâr payı oranıyla. Masrafsız.",
     "ihtiyaç_finansmanı", "ücret_muafiyeti", 2.99, 180000, 24),
    ("g013", "İhtiyaç finansmanında ilk taksit 3 ay sonra, ödemesiz dönem avantajı. 200.000 TL'ye kadar 36 ay vade, aylık %3,09 kâr payı.",
     "ihtiyaç_finansmanı", "vade_erteleme", 3.09, 200000, 36),
    ("g014", "Kredi kartınızla market harcamalarında 2.000 TL'ye varan para puan kazanın. Kart aidatı alınmaz.",
     "kredi_kartı", "para_puan", None, None, None),
    ("g015", "Online alışverişlerde 1.250 TL nakit iade fırsatı. Sadece yeni kart sahiplerine özeldir.",
     "kredi_kartı", "nakit_iade", None, None, None),
    ("g016", "Beyaz eşyada peşin fiyatına 12 taksit fırsatı. Kampanya 31.12.2026 tarihine kadar geçerlidir.",
     "kredi_kartı", "taksit_fırsatı", None, None, None),
    ("g017", "Akaryakıtta %8 indirim ve 500 TL chip para hediye. Aidatsız kredi kartı.",
     "kredi_kartı", "para_puan", None, None, None),
    ("g018", "32 gün vadeli katılma hesabında yıllık %45 kâr payı oranı. En az 50.000 TL ile hesap açılabilir.",
     "katılma_hesabı", "diğer", None, None, None),
    ("g019", "Ödüllü katılma hesabı açanlara çekilişle 250.000 TL ödül. En az 25.000 TL bakiye gereklidir.",
     "katılma_hesabı", "ödüllü_hesap", None, None, None),
    ("g020", "Kira sertifikası halka arzında en az 5.000 TL ile katılabilirsiniz. Vade 6 aydır.",
     "kira_sertifikası", "diğer", None, None, 6),
    ("g021", "KOBİ'lere 4.000.000 TL'ye kadar 48 ay vadeli işletme finansmanı, aylık %2,75 kâr payı.",
     "kobi_finansmanı", "diğer", 2.75, 4000000, 48),
    ("g022", "Esnaf destek finansmanında 500.000 TL'ye kadar 36 ay vade, aylık %2,65 kâr payı. Dosya masrafı alınmaz.",
     "kobi_finansmanı", "ücret_muafiyeti", 2.65, 500000, 36),
    ("g023", "İşyeri finansmanında 6.000.000 TL'ye kadar 120 ay vade, aylık %2,85 kâr payı oranı.",
     "işyeri_finansmanı", "diğer", 2.85, 6000000, 120),
    ("g024", "Gram altın birikim hesabıyla altın biriktirin, hesap işletim ücreti yoktur.",
     "altın_hesabı", "ücret_muafiyeti", None, None, None),
    ("g025", "Taşıt finansmanında aylık kâr payı oranı %1,89'dan başlar. Azami tutar 800.000 TL, vade 36 aydır.",
     "taşıt_finansmanı", "diğer", 1.89, 800000, 36),
    ("g026", "Motosiklet alımında 120.000 TL'ye kadar 18 ay vadeli finansman. Aylık %2,35 kâr payı.",
     "taşıt_finansmanı", "diğer", 2.35, 120000, 18),
    ("g027", "Taşıt finansmanı kampanyasında 10.000 TL nakit iade. 700.000 TL'ye kadar, 24 ay, aylık %2,02 kâr payı.",
     "taşıt_finansmanı", "nakit_iade", 2.02, 700000, 24),
    ("g028", "Konut finansmanında tahsis ücreti %0,5 oranındadır. 4.000.000 TL'ye kadar 120 ay vade, aylık %2,45 kâr payı.",
     "konut_finansmanı", "diğer", 2.45, 4000000, 120),
    ("g029", "Yeni müşterilere özel ihtiyaç finansmanında hiçbir ücret alınmaz. 150.000 TL'ye kadar 24 ay, aylık %3,25 kâr payı.",
     "ihtiyaç_finansmanı", "ücret_muafiyeti", 3.25, 150000, 24),
    ("g030", "Tekafül katılım sigortası poliçenizde %15 indirim fırsatı.",
     "sigorta", "oran_indirimi", None, None, None),
    ("g031", "Taşıt finansmanı: en az 50.000 TL, en fazla 1.500.000 TL. Vade 12-48 ay. Aylık %2,10 kâr payı.",
     "taşıt_finansmanı", "diğer", 2.10, 1500000, 48),  # konvansiyon: azami vade
    ("g032", "Konut finansmanınızda 3 yıl vadeye kadar aylık %2,20 kâr payı, 2.500.000 TL'ye kadar.",
     "konut_finansmanı", "diğer", 2.20, 2500000, 36),
    ("g033", "İhtiyaç finansmanında 36 aya varan vade seçenekleri. 300.000 TL'ye kadar aylık %2,89 kâr payı oranıyla.",
     "ihtiyaç_finansmanı", "diğer", 2.89, 300000, 36),
    ("g034", "Kredi kartı taksitli alışverişte 6 ek taksit ve 3.000 TL'ye varan para puan.",
     "kredi_kartı", "para_puan", None, None, None),
    ("g035", "Taşıt finansmanında kampanya 01.09.2026 - 31.12.2026 arasında geçerlidir. 550.000 TL'ye kadar, aylık %1,99 kâr payı, 30 ay vade.",
     "taşıt_finansmanı", "diğer", 1.99, 550000, 30),
    ("g036", "Sıfır araçta tahsis ücreti yok, ekspertiz yok. 650.000 TL'ye kadar 24 ay vade, aylık %1,85 kâr payı.",
     "taşıt_finansmanı", "ücret_muafiyeti", 1.85, 650000, 24),
    ("g037", "İşletme finansmanında 2 milyon TL'ye kadar 24 ay vade. Aylık kâr payı %2,95.",
     "kobi_finansmanı", "diğer", 2.95, 2000000, 24),
    ("g038", "Konut finansmanı başvurunuzda ekspertiz ücreti 9.500 TL'dir. 8.000.000 TL'ye kadar 180 ay vade, aylık %2,60 kâr payı.",
     "konut_finansmanı", "diğer", 2.60, 8000000, 180),
    ("g039", "Taşıt finansmanında 5.000 TL hediye para puan. 480.000 TL'ye kadar 24 ay, aylık %2,08 kâr payı.",
     "taşıt_finansmanı", "para_puan", 2.08, 480000, 24),
    ("g040", "Yatırım hesabınızda kira sertifikası alım satımı komisyonsuzdur.",
     "kira_sertifikası", "ücret_muafiyeti", None, None, None),
    ("g041", "Bireysel finansmanda 24 ay vadeli 220.000 TL'ye kadar kullandırım, aylık %3,15 kâr payı oranı ile.",
     "ihtiyaç_finansmanı", "diğer", 3.15, 220000, 24),
    ("g042", "Taşıt finansmanı fırsatında 12.000 TL'ye varan nakit iade kazanın. Finansman limiti 1.000.000 TL, vade 36 ay, aylık %2,12 kâr payı.",
     "taşıt_finansmanı", "nakit_iade", 2.12, 1000000, 36),
    ("g043", "Kart aidatınız ilk yıl alınmaz, aidatsız kullanım imkanı.",
     "kredi_kartı", "ücret_muafiyeti", None, None, None),
    ("g044", "Konut finansmanında ilk 6 ay ödemesiz dönem. 6.000.000 TL'ye kadar 240 ay vade, aylık %2,70 kâr payı.",
     "konut_finansmanı", "vade_erteleme", 2.70, 6000000, 240),
    ("g045", "Esnafa özel 350.000 TL'ye kadar 18 ay vadeli ticari finansman, aylık %2,88 kâr payı oranıyla.",
     "kobi_finansmanı", "diğer", 2.88, 350000, 18),

    # ------------------------------------------------------------------
    # ZOR (adversarial) küme — h0xx
    # Amaç: gerçek banka duyurularındaki tuzakları taklit etmek.
    # Sistemin bu örneklerde hata yapması BEKLENİR ve raporlanır.
    # ------------------------------------------------------------------
    ("h001", "Otuz altı ay vadeye kadar taşıt finansmanı imkanı. Aylık kâr payı oranımız 1,95 seviyesindedir. Limit yedi yüz elli bin liradır.",
     "taşıt_finansmanı", "diğer", 1.95, 750000, 36),
    ("h002", "Taşıt finansmanı: 24 ay için aylık %1,89; 36 ay için aylık %2,15; 48 ay için aylık %2,45 kâr payı. Azami 900.000 TL.",
     "taşıt_finansmanı", "diğer", 1.89, 900000, 24),
    ("h003", "Kampanyamızda 25.000 TL'ye varan nakit iade sunulmaktadır. Konut finansmanı limiti ayrıca belirlenir.",
     "konut_finansmanı", "nakit_iade", None, None, None),
    ("h004", "İhtiyaç finansmanında aylık kar payi orani %3.19'dur. 200.000 TL, 36 ay.",
     "ihtiyaç_finansmanı", "diğer", 3.19, 200000, 36),
    ("h005", "Yıllık maliyet oranı %38,42 olan taşıt finansmanımızda aylık kâr payı %2,05'tir. 500.000 TL'ye kadar 24 ay.",
     "taşıt_finansmanı", "diğer", 2.05, 500000, 24),
    ("h006", "Araç finansmanınızda kasko bedeli 18.000 TL, tahsis ücreti 6.500 TL'dir. 650.000 TL'ye kadar 30 ay vade, aylık %2,12 kâr payı.",
     "taşıt_finansmanı", "diğer", 2.12, 650000, 30),
    ("h007", "Bu bir taşıt finansmanı kampanyası DEĞİLDİR. Konut finansmanında 4.500.000 TL'ye kadar 180 ay vade, aylık %2,44 kâr payı.",
     "konut_finansmanı", "diğer", 2.44, 4500000, 180),
    ("h008", "1.5 milyon TL'ye kadar konut finansmanı, 10 yıl vade, aylık %2,35 kâr payı oranı.",
     "konut_finansmanı", "diğer", 2.35, 1500000, 120),
    ("h009", "Kredi kartı borcunuzu 500.000 TL'ye kadar 36 aya varan vadelerle yapılandırın. Aylık %2,89 kâr payı.",
     "kredi_kartı", "diğer", 2.89, 500000, 36),
    ("h010", "Taşıt finansmanında ilk 3 ay ödemesiz, kalan 21 ay taksitli. Toplam vade 24 ay, aylık %2,20 kâr payı, 400.000 TL.",
     "taşıt_finansmanı", "vade_erteleme", 2.20, 400000, 24),
    ("h011", "%0 kâr payı ile 12 ay vadeli 100.000 TL'ye kadar kampanyalı taşıt finansmanı.",
     "taşıt_finansmanı", "oran_indirimi", 0.0, 100000, 12),
    ("h012", "Finansman tutarı 300.000 TL ila 1.200.000 TL arasındadır. Vade 24 ila 60 ay. Aylık kâr payı %2,28.",
     "taşıt_finansmanı", "diğer", 2.28, 1200000, 60),
    ("h013", "Emeklilere özel ihtiyaç finansmanı: 120.000 TL, 24 ay, aylık kâr payı oranı yüzde iki virgül seksen dokuz.",
     "ihtiyaç_finansmanı", "diğer", 2.89, 120000, 24),
    ("h014", "Kampanya kapsamında 750.000 TL'lik taşıt finansmanı için toplam geri ödeme 980.000 TL'dir. Vade 36 ay, aylık %2,02 kâr payı.",
     "taşıt_finansmanı", "diğer", 2.02, 750000, 36),
    ("h015", "Katılma hesabı kâr payı oranları piyasa koşullarına göre belirlenir; sabit bir oran taahhüt edilmez.",
     "katılma_hesabı", "diğer", None, None, None),
]


HEADER = ["id", "split", "text", "product_type", "campaign_type", "profit_rate",
          "financing_amount_max", "maturity_months"]

# ----------------------------------------------------------------------
# HELD-OUT TEST KÜMESİ
# Bu örnekler yazıldıktan SONRA sisteme hiçbir düzeltme yapılmamıştır.
# Dev kümesi geliştirme sırasında kullanıldığı için üst sınır (optimistik)
# değer üretir; genelleme performansı için bu küme referans alınmalıdır.
# ----------------------------------------------------------------------
TEST: list[tuple] = [
    ("t001", "Bayram kampanyası kapsamında sıfır kilometre araçlarda 850.000 TL'ye varan finansman, 42 ay vadeye kadar, aylık %2,07 kâr payı oranı ile sunulmaktadır.",
     "taşıt_finansmanı", "diğer", 2.07, 850000, 42),
    ("t002", "Konut sahibi olmak isteyenlere 12.000.000 TL'ye kadar finansman desteği. Geri ödeme süresi en fazla 20 yıldır. Aylık kâr payı oranı %2,52 olarak uygulanacaktır.",
     "konut_finansmanı", "diğer", 2.52, 12000000, 240),
    ("t003", "Şubelerimizden yapılacak ihtiyaç finansmanı başvurularında dosya ücreti talep edilmez. Tutar 175.000 TL, vade 30 ay, aylık kâr payı %3,05.",
     "ihtiyaç_finansmanı", "ücret_muafiyeti", 3.05, 175000, 30),
    ("t004", "Kartınızla yapacağınız restoran harcamalarında 750 TL'ye kadar parapuan kazanabilirsiniz. Kampanya 15 Eylül 2026 tarihine kadar sürecektir.",
     "kredi_kartı", "para_puan", None, None, None),
    ("t005", "Ticari müşterilerimize yönelik işletme finansmanında üst limit 3.500.000 TL, azami vade 42 aydır. Aylık kâr payı oranı %2,68'dir.",
     "kobi_finansmanı", "diğer", 2.68, 3500000, 42),
    ("t006", "İki yüz bin liraya kadar bireysel finansman, on sekiz ay vadeli, aylık kâr payı oranı %3,12.",
     "ihtiyaç_finansmanı", "diğer", 3.12, 200000, 18),
    ("t007", "Taşıt finansmanı başvurularında tahsis ücreti finansman tutarının %0,45'i kadardır. 620.000 TL'ye kadar 36 ay vade, aylık %1,96 kâr payı.",
     "taşıt_finansmanı", "diğer", 1.96, 620000, 36),
    ("t008", "Katılma hesabı müşterilerimize özel çekilişte 500.000 TL tutarında ödül dağıtılacaktır. Katılım için asgari 30.000 TL bakiye şarttır.",
     "katılma_hesabı", "ödüllü_hesap", None, None, None),
    ("t009", "Sıfır faizli taşıt kampanyası: %0 kâr payı, 6 ay vade, 250.000 TL'ye kadar.",
     "taşıt_finansmanı", "oran_indirimi", 0.0, 250000, 6),
    ("t010", "Yenilenebilir enerji yatırımlarına 25 milyon TL'ye kadar 84 ay vadeli finansman. Aylık kâr payı %2,42.",
     "kobi_finansmanı", "diğer", 2.42, 25000000, 84),
    ("t011", "Kredi kartı borç transferinde 36 aya varan vade ve aylık %2,79 kâr payı oranı. Transfer tutarı 400.000 TL ile sınırlıdır.",
     "kredi_kartı", "diğer", 2.79, 400000, 36),
    ("t012", "Konut finansmanında ekspertiz ücreti 10.500 TL olarak uygulanır; tahsis ücreti alınmaz. 9.000.000 TL'ye kadar 150 ay vade, aylık %2,58 kâr payı.",
     "konut_finansmanı", "ücret_muafiyeti", 2.58, 9000000, 150),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for row in GOLD:
            w.writerow([row[0], "dev"] + ["" if v is None else v for v in row[1:]])
        for row in TEST:
            w.writerow([row[0], "test"] + ["" if v is None else v for v in row[1:]])
    print(f"{len(GOLD)} dev + {len(TEST)} test örneği yazıldı → {OUT}")


if __name__ == "__main__":
    main()
