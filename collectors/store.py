"""
SEZARNEXT — Data Store
======================
İşlenmiş SezarNextCampaign kayıtlarının JSON kalıcılığı.
Üretimde PostgreSQL'e aynı arayüzle geçilebilir.
"""

from __future__ import annotations

import json
from pathlib import Path

from schemas.campaign_schema import SezarNextCampaign

DEFAULT_PATH = Path("data/processed/campaigns.json")


def save_campaigns(campaigns: list[SezarNextCampaign], path: str | Path = DEFAULT_PATH) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps([c.model_dump(mode="json") for c in campaigns], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return p


def load_campaigns(path: str | Path = DEFAULT_PATH) -> list[SezarNextCampaign]:
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return [SezarNextCampaign(**rec) for rec in data]
