"""
SEZARNEXT — Canlı Toplama Akışı
===============================
BDDK listesi → banka keşfi → nazik tarama → NLP Core → şema → depolama.

Ağ erişimi gerektirir. Erişim yoksa hata vermez; toplanan kayıt sayısı 0 döner
ve mevcut demo verisi korunur.

Çalıştırma:
    python -m demo.run_collect --limit 3 --dry-run
    python -m demo.run_collect
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collectors.bank_adapters.base_adapter import GenericAdapter  # noqa: E402
from collectors.bank_discovery import discover  # noqa: E402
from collectors.bddk_collector import get_banks  # noqa: E402
from collectors.crawler import PoliteCrawler  # noqa: E402
from collectors.store import load_campaigns, save_campaigns  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="SEZARNEXT canlı veri toplama")
    ap.add_argument("--limit", type=int, default=3, help="taranacak banka sayısı")
    ap.add_argument("--pages", type=int, default=4, help="banka başına sayfa sayısı")
    ap.add_argument("--delay", type=float, default=2.0, help="istekler arası bekleme (sn)")
    ap.add_argument("--dry-run", action="store_true", help="yalnızca hedef URL'leri listele")
    ap.add_argument("--merge", action="store_true", help="mevcut kayıtlara ekle")
    args = ap.parse_args()

    banks = get_banks(offline=True)[: args.limit]
    crawler = PoliteCrawler(delay=args.delay)
    collected = []

    print("SEZARNEXT — canlı toplama")
    print("=" * 66)

    for bank in banks:
        if not bank.website:
            continue
        targets = discover(bank.website)
        urls = (targets["campaign"] + targets["product"])[: args.pages]
        print(f"\n{bank.name}")
        for u in urls:
            print(f"  → {u}")
        if args.dry_run:
            continue

        adapter = GenericAdapter(bank.name, bank.website)
        for res in crawler.crawl(urls):
            if res.status != 200 or not res.html:
                print(f"  [atlandı] {res.url} ({res.error or res.status})")
                continue
            if not res.changed:
                print(f"  [değişmedi] {res.url}")
                continue
            for raw in adapter.parse_list(res.html, res.url):
                out = adapter.to_pipeline(raw)
                if out.campaign is not None and out.is_valid:
                    collected.append(out.campaign)

    print("\n" + "=" * 66)
    if args.dry_run:
        print("Kuru koşu tamamlandı; hiçbir istek gönderilmedi.")
        return

    if not collected:
        print("Kayıt toplanamadı (ağ erişimi yok veya sayfa yapısı tanınmadı).")
        print("Mevcut veri korundu. Demo için: python -m demo.build_demo_data")
        return

    if args.merge:
        collected = load_campaigns() + collected
    path = save_campaigns(collected)
    print(f"{len(collected)} kayıt kaydedildi → {path}")


if __name__ == "__main__":
    main()
