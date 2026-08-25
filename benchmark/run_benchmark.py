"""
SEZARNEXT Benchmark Suite — Runner
==================================
Tüm metrikleri hesaplar ve benchmark_results.json'a yazar.

    python -m benchmark.run_benchmark
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark.evaluate_classifier import evaluate as eval_cls  # noqa: E402
from benchmark.evaluate_extraction import evaluate as eval_ext  # noqa: E402

OUT = Path("benchmark/benchmark_results.json")

TARGETS = {
    "product_classification_macro_f1": 0.90,
    "campaign_classification_macro_f1": 0.90,
    "entity_extraction_f1": 0.93,
    "profit_rate_exact_match": 0.95,
    "amount_exact_match": 0.95,
    "maturity_exact_match": 0.95,
    "hallucination_rate": 0.01,   # düşük olmalı
    "evidence_coverage": 0.98,
}


def main() -> None:
    dev = eval_ext(split="dev")
    test = eval_ext(split="test")
    cls = eval_cls(split="test")
    cls_dev = eval_cls(split="dev")

    summary = {
        "product_classification_macro_f1": cls["product"]["macro_f1"],
        "campaign_classification_macro_f1": cls["campaign"]["macro_f1"],
        "entity_extraction_f1": test["entity_extraction_f1"],
        "profit_rate_exact_match": test["per_field"]["profit_rate"]["exact_match"],
        "amount_exact_match": test["per_field"]["financing_amount_max"]["exact_match"],
        "maturity_exact_match": test["per_field"]["maturity_months"]["exact_match"],
        "hallucination_rate": test["hallucination_rate"],
        "evidence_coverage": test["evidence_coverage"],
    }

    results = {
        "version": "1.1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": {
            "name": "SEZARNEXT Gold Dataset",
            "nature": "sentetik, elle etiketlenmiş",
            "dev_samples": dev["samples"],
            "test_samples": test["samples"],
            "note": "DEV kümesi geliştirme sırasında kullanılmıştır; TEST kümesi "
                    "held-out'tur ve raporlanan genelleme metrikleri buradan gelir. "
                    "v1.0 sonuçları benchmark_results_v1.0_frozen.json içinde "
                    "dondurulmuştur; v1.1'de test kümesindeki 'İki yüz bin' hatası "
                    "giderildiğinden test kümesi artık tam anlamıyla held-out DEĞİLDİR. "
                    "v1.2 için yeni bir held-out küme yazılmalıdır.",
        },
        "headline_metrics": summary,
        "targets": TARGETS,
        "target_status": {
            k: ("PASS" if (v <= TARGETS[k] if k == "hallucination_rate" else v >= TARGETS[k])
                else "FAIL")
            for k, v in summary.items() if v is not None
        },
        "extraction_dev": dev,
        "extraction_test": test,
        "classification_test": cls,
        "classification_dev": cls_dev,
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("SEZARNEXT Benchmark Suite")
    print("=" * 64)
    print(f"{'Metric':<38}{'Result':>10}{'Target':>9}{'':>7}")
    print("-" * 64)
    for k, v in summary.items():
        if v is None:
            continue
        tgt = TARGETS[k]
        status = results["target_status"][k]
        op = "<=" if k == "hallucination_rate" else ">="
        print(f"{k:<38}{v:>10.4f}{op + str(tgt):>9}{status:>7}")
    print("-" * 64)
    print(f"Sonuçlar → {OUT}")


if __name__ == "__main__":
    main()
