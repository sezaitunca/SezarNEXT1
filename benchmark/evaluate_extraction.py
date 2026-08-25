"""
SEZARNEXT Benchmark Suite — Entity Extraction Evaluation
========================================================
Metrikler:
  - Exact match (alan bazlı): doğru çıkarılan / gold'da dolu olan
  - Precision / Recall / F1  : boş bırakılması gereken alanı doldurmak da hatadır
  - Hallucination rate       : kaynak metinde geçmeyen bir değerin üretilmesi
  - Evidence coverage        : çıkarılan sayısal alanların kanıtlı olma oranı

Çalıştırma:
    python -m benchmark.evaluate_extraction
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nlp.cleaner import clean  # noqa: E402
from nlp.entity_extractor import extract_entities  # noqa: E402

GOLD_PATH = Path("benchmark/gold_dataset.csv")
FIELDS = ["profit_rate", "financing_amount_max", "maturity_months"]
TOLERANCE = {"profit_rate": 0.001, "financing_amount_max": 0.5, "maturity_months": 0.0}


def _to_float(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def value_in_text(field: str, value: float, text: str) -> bool:
    """Üretilen değerin kaynak metinde gerçekten bulunup bulunmadığını denetler."""
    if value is None:
        return True
    digits = re.findall(r"\d[\d.,]*", text)
    from nlp.normalizer import parse_number, parse_word_number

    candidates = set()
    # Yazıyla ifade edilen sayılar da kaynağa dayalıdır (ör. "yedi yüz elli bin")
    for chunk in re.findall(r"(?:[a-zçğıöşüA-ZÇĞİÖŞÜ]+\s+){1,6}(?:bin|milyon|milyar|ay)", text):
        n = parse_word_number(chunk)
        if n:
            candidates.update({n, n * 12})
    for d in digits:
        n = parse_number(d)
        if n is None:
            continue
        candidates.update({n, n * 1_000, n * 1_000_000, n * 12})
    return any(abs(value - c) <= max(0.01, abs(c) * 1e-6) for c in candidates)


def evaluate(verbose: bool = False, split: str | None = None) -> dict:
    rows = list(csv.DictReader(GOLD_PATH.open(encoding="utf-8")))
    if split:
        rows = [r for r in rows if r.get("split") == split]
    stats = {f: {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "exact": 0, "gold_filled": 0}
             for f in FIELDS}
    hallucinations, total_predicted, evidence_ok, evidence_total = 0, 0, 0, 0
    errors: list[dict] = []

    for row in rows:
        text = clean(row["text"])
        ext = extract_entities(text)
        pred_fields = ext["fields"]
        ev_fields = {e.field_name for e in ext["evidence"]}

        for f in FIELDS:
            gold = _to_float(row.get(f))
            pred = _to_float(pred_fields.get(f))
            s = stats[f]

            if gold is not None:
                s["gold_filled"] += 1
            if pred is not None:
                total_predicted += 1
                evidence_total += 1
                if f in ev_fields:
                    evidence_ok += 1
                if not value_in_text(f, pred, row["text"]):
                    hallucinations += 1

            if gold is None and pred is None:
                s["tn"] += 1
            elif gold is None and pred is not None:
                s["fp"] += 1
                errors.append({"id": row["id"], "field": f, "gold": None, "pred": pred,
                               "type": "false_positive"})
            elif gold is not None and pred is None:
                s["fn"] += 1
                errors.append({"id": row["id"], "field": f, "gold": gold, "pred": None,
                               "type": "miss"})
            else:
                if abs(gold - pred) <= TOLERANCE[f]:
                    s["tp"] += 1
                    s["exact"] += 1
                else:
                    s["fp"] += 1
                    s["fn"] += 1
                    errors.append({"id": row["id"], "field": f, "gold": gold, "pred": pred,
                                   "type": "wrong_value"})

    per_field = {}
    f1s = []
    for f, s in stats.items():
        prec = s["tp"] / (s["tp"] + s["fp"]) if (s["tp"] + s["fp"]) else 0.0
        rec = s["tp"] / (s["tp"] + s["fn"]) if (s["tp"] + s["fn"]) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        f1s.append(f1)
        per_field[f] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "exact_match": round(s["exact"] / s["gold_filled"], 4) if s["gold_filled"] else None,
            "support": s["gold_filled"],
        }

    result = {
        "split": split or "all",
        "samples": len(rows),
        "per_field": per_field,
        "entity_extraction_f1": round(sum(f1s) / len(f1s), 4),
        "hallucination_rate": round(hallucinations / total_predicted, 4) if total_predicted else 0.0,
        "evidence_coverage": round(evidence_ok / evidence_total, 4) if evidence_total else 0.0,
        "error_count": len(errors),
    }
    if verbose:
        result["errors"] = errors[:25]
    return result


def _report(res: dict, title: str) -> None:
    print(f"\n{title}  (n={res['samples']})")
    print("=" * 62)
    print(f"{'Alan':<26}{'P':>8}{'R':>8}{'F1':>8}{'Exact':>10}")
    print("-" * 62)
    for f, m in res["per_field"].items():
        ex = f"{m['exact_match']:.1%}" if m["exact_match"] is not None else "-"
        print(f"{f:<26}{m['precision']:>8.3f}{m['recall']:>8.3f}{m['f1']:>8.3f}{ex:>10}")
    print("-" * 62)
    print(f"{'Entity extraction F1':<26}{res['entity_extraction_f1']:>32.4f}")
    print(f"{'Hallucination rate':<26}{res['hallucination_rate']:>31.2%}")
    print(f"{'Evidence coverage':<26}{res['evidence_coverage']:>31.2%}")
    if res.get("errors"):
        print("  Hatalar:")
        for e in res["errors"][:10]:
            print(f"    {e['id']} {e['field']:<22} gold={e['gold']} pred={e['pred']} ({e['type']})")


def main() -> None:
    print("SEZARNEXT Benchmark Suite — Entity Extraction")
    _report(evaluate(verbose=True, split="dev"),
            "DEV kümesi (geliştirmede kullanıldı — optimistik üst sınır)")
    _report(evaluate(verbose=True, split="test"),
            "HELD-OUT TEST kümesi (genelleme göstergesi)")


if __name__ == "__main__":
    main()
