"""
SEZAR Agent
===========
SEZARNEXT'in kullanıcıya bakan yapay zekâ ajanı.

Akış:
    Kullanıcı sorgusu
      → Query Router (intent + parametre)
      → Knowledge Layer (retrieval)
      → Comparison Engine (uygunluk + karşılaştırma)
      → Benefit Engine (net ekonomik maliyet)
      → Ranking Engine (öncelik profili)
      → Response Generator (+ Evidence)

Ajan bir chatbot değildir: her cümlesi bir motor çıktısına ve bir kanıt
kaydına dayanır.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent import response_generator as rg
from agent.query_router import Query, route
from engine.comparison_engine import ComparisonRequest, ComparisonResult, compare
from engine.ranking_engine import rank
from knowledge.evidence import build_card
from knowledge.retriever import Retriever
from schemas.campaign_schema import SezarNextCampaign


@dataclass
class AgentResponse:
    text: str
    intent: str
    query: Query
    result: ComparisonResult | None = None
    trace: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.text,
            "intent": self.intent,
            "parsed_query": self.query.summary(),
            "trace": self.trace,
            "evidence": self.evidence,
            "comparison": self.result.table() if self.result else [],
        }


class SezarAgent:
    """SEZARNEXT'in ana ajanı."""

    NAME = "SEZAR"
    TAGLINE = "AI Financial Agent — Participation Finance Intelligence"

    def __init__(self, campaigns: list[SezarNextCampaign]) -> None:
        self.campaigns = campaigns
        self.retriever = Retriever(campaigns)
        self.banks = sorted({c.bank for c in campaigns})
        self._last: ComparisonResult | None = None

    # ------------------------------------------------------------------
    def ask(self, question: str, top_k: int = 8) -> AgentResponse:
        trace: list[str] = []
        q = route(question, known_banks=self.banks)
        trace.append(f"Intent: {q.intent} (conf={q.confidence})")
        trace.append(
            f"Parametreler: tutar={q.amount}, vade={q.months}, "
            f"ürün={q.product_type}, banka={q.bank}, öncelik={q.priority}"
        )

        if q.intent == "EXPLAIN_EVIDENCE":
            return self._answer_evidence(q, trace)
        if q.intent == "BANK_INTELLIGENCE" and q.bank:
            return self._answer_bank(q, trace)
        if q.intent == "PRODUCT_LOOKUP" and not (q.amount and q.months):
            return self._answer_lookup(q, trace)

        missing = [k for k, v in (("amount", q.amount), ("months", q.months)) if not v]
        if missing:
            return AgentResponse(
                text=rg.render_clarification(missing), intent=q.intent, query=q, trace=trace
            )

        return self._answer_comparison(q, trace, top_k)

    # ------------------------------------------------------------------
    def _answer_comparison(self, q: Query, trace: list[str], top_k: int) -> AgentResponse:
        req = ComparisonRequest(
            amount=q.amount, months=q.months, product_type=q.product_type, top_k=top_k
        )
        result = compare(self.campaigns, req)
        self._last = result
        trace.append(
            f"Retrieval: {result.banks_checked} banka, {result.products_found} ürün tarandı, "
            f"{result.products_eligible} uygun"
        )

        if q.priority != "net_cost" and result.breakdowns:
            ranked = rank(result.breakdowns, profile=q.priority)
            result.breakdowns = [b for b, _ in ranked]
            trace.append(f"Ranking profili uygulandı: {q.priority}")

        trace.append("Benefit Engine: net ekonomik maliyet hesaplandı")

        text = rg.render_answer(result)
        alts = rg.render_alternatives(result)
        if alts:
            text += "\n\n" + alts

        evidence = []
        if result.best and result.best.campaign:
            for f in ("profit_rate", "financing_amount_max", "maturity_months"):
                if getattr(result.best.campaign, f, None) is not None:
                    evidence.append(build_card(result.best.campaign, f).__dict__)

        return AgentResponse(
            text=text, intent=q.intent, query=q, result=result, trace=trace, evidence=evidence
        )

    def _answer_lookup(self, q: Query, trace: list[str]) -> AgentResponse:
        hits = self.retriever.search(q.raw, top_k=5, product_type=q.product_type, bank=q.bank)
        trace.append(f"BM25 retrieval: {len(hits)} sonuç")
        if not hits:
            return AgentResponse(
                text="Bu sorguya uyan bir ürün kaydı bulamadım.", intent=q.intent, query=q, trace=trace
            )
        lines = ["İlgili ürünler:", ""]
        evidence = []
        for c, score in hits:
            rate = f"%{c.profit_rate}".replace(".", ",") if c.profit_rate else "belirtilmemiş"
            lim = f"{c.financing_amount_max:,.0f}".replace(",", ".") if c.financing_amount_max else "-"
            lines.append(
                f"  • {c.bank} — {c.product_name}\n"
                f"      kâr payı {rate} | azami {lim} TL | "
                f"{c.maturity_months or '-'} ay | ilgi {score}"
            )
            evidence.append(build_card(c, "profit_rate").__dict__)
        return AgentResponse(
            text="\n".join(lines), intent=q.intent, query=q, trace=trace, evidence=evidence
        )

    def _answer_bank(self, q: Query, trace: list[str]) -> AgentResponse:
        items = self.retriever.by_bank(q.bank)
        trace.append(f"Bank intelligence: {q.bank} → {len(items)} kayıt")
        lines = [f"{q.bank} — aktif kayıtlar ({len(items)})", ""]
        for c in items:
            lines.append(
                f"  • [{c.product_type.value}] {c.product_name} "
                f"({c.campaign_type.value}, conf={c.confidence_score:.2f})"
            )
        return AgentResponse(text="\n".join(lines), intent=q.intent, query=q, trace=trace)

    def _answer_evidence(self, q: Query, trace: list[str]) -> AgentResponse:
        trace.append("Evidence talebi: son karşılaştırmanın kaynağı getiriliyor")
        if not self._last or not self._last.best or not self._last.best.campaign:
            return AgentResponse(
                text="Henüz kanıt gösterebileceğim bir karşılaştırma yapmadım.",
                intent=q.intent, query=q, trace=trace,
            )
        c = self._last.best.campaign
        cards = [build_card(c, f) for f in ("profit_rate", "financing_amount_max", "maturity_months")
                 if getattr(c, f, None) is not None]
        text = "\n\n".join(card.render() for card in cards)
        return AgentResponse(
            text=text, intent=q.intent, query=q, result=self._last, trace=trace,
            evidence=[card.__dict__ for card in cards],
        )

    # ------------------------------------------------------------------
    def payment_plan(self, rows: int = 6) -> str:
        if not self._last:
            return "Önce bir karşılaştırma sorusu sorun."
        return rg.render_payment_plan(self._last, rows=rows)

    def stats(self) -> dict:
        from collections import Counter

        return {
            "banks": len(self.banks),
            "campaigns": len(self.campaigns),
            "by_product": dict(Counter(c.product_type.value for c in self.campaigns)),
            "by_campaign_type": dict(Counter(c.campaign_type.value for c in self.campaigns)),
            "avg_confidence": round(
                sum(c.confidence_score for c in self.campaigns) / max(1, len(self.campaigns)), 3
            ),
        }
