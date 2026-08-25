"""
SEZARNEXT Benchmark Suite — Classification Evaluation
=====================================================
Ürün tipi ve kampanya tipi sınıflandırıcıları için Macro-F1, sınıf bazlı
precision/recall ve karışıklık matrisi (confusion matrix) üretir.

Çalıştırma:
    python -m benchmark.evaluate_classifier
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nlp.campaign_classifier import classify_campaign, classify_product  # noqa: E402
from nlp.cleaner import clean  # noqa: E402

GOLD_PATH = Path("benchmark/gold_dataset.csv")


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def evaluate_task(rows: list[dict], gold_key: str, predictor) -> dict:
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    correct = 0

    for row in rows:
        gold = row[gold_key]
        pred = predictor(clean(row["text"]))["label"]
        confusion[gold][pred] += 1
        if pred == gold:
            tp[gold] += 1
            correct += 1
        else:
            fp[pred] += 1
            fn[gold] += 1

    labels = sorted(set(list(tp) + list(fp) + list(fn)))
    per_class, f1s = {}, []
    for lab in labels:
        p, r, f = _prf(tp[lab], fp[lab], fn[lab])
        support = tp[lab] + fn[lab]
        per_class[lab] = {"precision": round(p, 4), "recall": round(r, 4),
                          "f1": round(f, 4), "support": support}
        if support > 0:
            f1s.append(f)

    return {
        "accuracy": round(correct / len(rows), 4),
        "macro_f1": round(sum(f1s) / len(f1s), 4) if f1s else 0.0,
        "per_class": per_class,
        "confusion": {g: dict(p) for g, p in confusion.items()},
    }


def evaluate(split: str | None = None) -> dict:
    rows = list(csv.DictReader(GOLD_PATH.open(encoding="utf-8")))
    if split:
        rows = [r for r in rows if r.get("split") == split]
    return {
        "product": evaluate_task(rows, "product_type", classify_product),
        "campaign": evaluate_task(rows, "campaign_type", classify_campaign),
        "samples": len(rows),
    }


def _print_task(name: str, res: dict) -> None:
    print(f"\n{name}")
    print("-" * 62)
    print(f"{'Sınıf':<26}{'P':>8}{'R':>8}{'F1':>8}{'N':>7}")
    for lab, m in sorted(res["per_class"].items(), key=lambda x: -x[1]["support"]):
        print(f"{lab:<26}{m['precision']:>8.3f}{m['recall']:>8.3f}{m['f1']:>8.3f}{m['support']:>7}")
    print("-" * 62)
    print(f"{'Accuracy':<26}{res['accuracy']:>30.4f}")
    print(f"{'Macro-F1':<26}{res['macro_f1']:>30.4f}")


def main() -> None:
    print("SEZARNEXT Benchmark Suite — Classification")
    print("=" * 62)
    for split, label in (("dev", "DEV"), ("test", "HELD-OUT TEST")):
        res = evaluate(split=split)
        print(f"\n### {label} (n={res['samples']})")
        _print_task("Ürün Tipi", res["product"])
        _print_task("Kampanya Tipi", res["campaign"])


if __name__ == "__main__":
    main()
