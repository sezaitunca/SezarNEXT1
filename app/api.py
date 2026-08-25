"""
SEZARNEXT API (FastAPI)
=======================
On-premise REST arayüzü.

    uvicorn app.api:app --host 0.0.0.0 --port 8000

Uç noktalar:
    GET  /health
    GET  /stats
    GET  /banks
    GET  /campaigns
    POST /extract       — ham metinden yapılandırılmış bilgi
    POST /inspect       — NLP Inspector adım adım çıktı
    POST /compare       — çok kriterli karşılaştırma + Benefit Engine
    POST /ask           — SEZAR Agent
    GET  /evidence/{i}  — kanıt kartı
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.sezar_agent import SezarAgent
from collectors.store import load_campaigns
from engine.comparison_engine import ComparisonRequest, compare
from knowledge.evidence import build_card, coverage
from nlp.pipeline import inspect as nlp_inspect, run_pipeline

app = FastAPI(
    title="SEZARNEXT",
    description="Explainable AI for Participation Finance Intelligence",
    version="1.1.0",
)

CAMPAIGNS = load_campaigns()
AGENT = SezarAgent(CAMPAIGNS) if CAMPAIGNS else None


# --------------------------------------------------------------------------
class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=5)
    bank: str = "Bilinmeyen"
    source_url: str = "manual://input"
    use_llm: bool = False


class CompareRequest(BaseModel):
    amount: float = Field(..., gt=0)
    months: int = Field(..., ge=1, le=360)
    product_type: str | None = None
    top_k: int = 10


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)


# --------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "campaigns_loaded": len(CAMPAIGNS), "agent": AGENT is not None}


@app.get("/stats")
def stats() -> dict:
    if not AGENT:
        raise HTTPException(503, "Veri yüklenmedi. `python -m demo.build_demo_data` çalıştırın.")
    out = AGENT.stats()
    out["evidence_coverage"] = coverage(CAMPAIGNS)
    out["synthetic_data"] = any(c.is_synthetic for c in CAMPAIGNS)
    return out


@app.get("/banks")
def banks() -> dict:
    from collectors.bddk_collector import get_banks

    return {"registry": [b.__dict__ for b in get_banks()],
            "in_knowledge_base": AGENT.banks if AGENT else []}


@app.get("/campaigns")
def campaigns(product_type: str | None = None, bank: str | None = None, limit: int = 50) -> dict:
    items = CAMPAIGNS
    if product_type:
        items = [c for c in items if c.product_type.value == product_type]
    if bank:
        items = [c for c in items if c.bank.lower() == bank.lower()]
    return {"count": len(items),
            "items": [c.model_dump(mode="json") for c in items[:limit]]}


@app.post("/extract")
def extract(req: ExtractRequest) -> dict:
    res = run_pipeline(req.text, bank=req.bank, source_url=req.source_url, use_llm=req.use_llm)
    return res.model_dump(mode="json")


@app.post("/inspect")
def inspect_endpoint(req: ExtractRequest) -> dict:
    return nlp_inspect(req.text)


@app.post("/compare")
def compare_endpoint(req: CompareRequest) -> dict:
    if not CAMPAIGNS:
        raise HTTPException(503, "Veri yüklenmedi.")
    result = compare(CAMPAIGNS, ComparisonRequest(**req.model_dump()))
    return {
        "banks_checked": result.banks_checked,
        "products_found": result.products_found,
        "products_eligible": result.products_eligible,
        "results": result.table(),
        "best_reasons": result.best.reasons if result.best else [],
    }


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    if not AGENT:
        raise HTTPException(503, "Veri yüklenmedi.")
    return AGENT.ask(req.question).to_dict()


@app.get("/evidence/{index}")
def evidence(index: int, field: str = "profit_rate") -> dict:
    if not 0 <= index < len(CAMPAIGNS):
        raise HTTPException(404, "Kayıt bulunamadı")
    return build_card(CAMPAIGNS[index], field).__dict__
