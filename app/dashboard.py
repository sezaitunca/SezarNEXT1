"""
SEZARNEXT Intelligence Dashboard (Streamlit)
============================================
    streamlit run app/dashboard.py

Modüller: Overview / Campaign Explorer / Finance Comparison / Benefit Analysis /
Bank Intelligence / SEZAR Agent / NLP Inspector / Model Performance / System Status
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from agent.sezar_agent import SezarAgent
from collectors.store import load_campaigns
from engine.comparison_engine import ComparisonRequest, compare
from engine.financial_math import build_payment_plan, format_pct, format_try
from knowledge.evidence import build_card, coverage
from nlp.pipeline import inspect as nlp_inspect

st.set_page_config(page_title="SEZARNEXT", page_icon="◆", layout="wide")


@st.cache_data
def _load():
    return load_campaigns()


CAMPAIGNS = _load()

st.sidebar.markdown("## SEZARNEXT")
st.sidebar.caption("Participation Finance Intelligence")
PAGE = st.sidebar.radio(
    "Modül",
    ["Overview", "Campaign Explorer", "Finance Comparison", "Benefit Analysis",
     "Bank Intelligence", "SEZAR Agent", "NLP Inspector", "Model Performance",
     "System Status"],
    label_visibility="collapsed",
)

if not CAMPAIGNS:
    st.error("Veri bulunamadı. Terminalde çalıştırın: `python -m demo.build_demo_data`")
    st.stop()

AGENT = SezarAgent(CAMPAIGNS)
if any(c.is_synthetic for c in CAMPAIGNS):
    st.sidebar.warning("Sentetik demo verisi kullanılıyor.")

st.title("SEZARNEXT")
st.caption("AI-Powered Participation Finance Intelligence")


def df_of(items):
    return pd.DataFrame([{
        "Banka": c.bank, "Ürün": c.product_name, "Tip": c.product_type.value,
        "Kampanya": c.campaign_type.value,
        "Kâr Payı %": c.profit_rate, "Azami TL": c.financing_amount_max,
        "Vade": c.maturity_months, "Confidence": c.confidence_score,
    } for c in items])


# ---------------------------------------------------------------- Overview
if PAGE == "Overview":
    s = AGENT.stats()
    cols = st.columns(5)
    cols[0].metric("Aktif Bankalar", s["banks"])
    cols[1].metric("Aktif Kayıtlar", s["campaigns"])
    cols[2].metric("Finansman Ürünleri",
                   sum(v for k, v in s["by_product"].items() if "finansman" in k))
    cols[3].metric("Kart Kampanyaları", s["by_product"].get("kredi_kartı", 0))
    cols[4].metric("Evidence Coverage", f"{coverage(CAMPAIGNS):.0%}")
    st.divider()
    c1, c2 = st.columns(2)
    c1.subheader("Ürün Dağılımı")
    c1.bar_chart(pd.Series(s["by_product"]))
    c2.subheader("Kampanya Tipi Dağılımı")
    c2.bar_chart(pd.Series(s["by_campaign_type"]))
    st.caption(f"Son güncelleme: {max(c.scraped_at for c in CAMPAIGNS):%d.%m.%Y %H:%M}")

# -------------------------------------------------------- Campaign Explorer
elif PAGE == "Campaign Explorer":
    c1, c2 = st.columns(2)
    ptype = c1.selectbox("Ürün tipi", ["hepsi"] + sorted({c.product_type.value for c in CAMPAIGNS}))
    bank = c2.selectbox("Banka", ["hepsi"] + AGENT.banks)
    items = CAMPAIGNS
    if ptype != "hepsi":
        items = [c for c in items if c.product_type.value == ptype]
    if bank != "hepsi":
        items = [c for c in items if c.bank == bank]
    st.dataframe(df_of(items), use_container_width=True, hide_index=True)
    if items:
        sel = st.selectbox("Kanıt görüntüle", range(len(items)),
                           format_func=lambda i: f"{items[i].bank} — {items[i].product_name}")
        st.code(build_card(items[sel], "profit_rate").render(), language="text")

# ------------------------------------------------------- Finance Comparison
elif PAGE == "Finance Comparison":
    c1, c2, c3 = st.columns(3)
    amount = c1.number_input("Tutar (TL)", 10_000, 50_000_000, 500_000, step=50_000)
    months = c2.number_input("Vade (ay)", 1, 360, 24)
    ptype = c3.selectbox("Ürün", sorted({c.product_type.value for c in CAMPAIGNS}))
    result = compare(CAMPAIGNS, ComparisonRequest(amount=amount, months=months,
                                                  product_type=ptype))
    m = st.columns(3)
    m[0].metric("Taranan banka", result.banks_checked)
    m[1].metric("Uygun ürün", result.products_eligible)
    m[2].metric("En düşük net maliyet",
                format_try(result.best.net_economic_cost) if result.best else "-")
    if result.breakdowns:
        st.dataframe(pd.DataFrame(result.table()), use_container_width=True, hide_index=True)
        st.subheader("Ödeme Planı — " + result.best.bank)
        plan = build_payment_plan(amount, result.best.profit_rate, months, with_schedule=True)
        st.dataframe(pd.DataFrame(plan.schedule), use_container_width=True, hide_index=True)
    else:
        st.info("Kriterlere uyan ürün yok.")

# --------------------------------------------------------- Benefit Analysis
elif PAGE == "Benefit Analysis":
    c1, c2 = st.columns(2)
    amount = c1.number_input("Tutar (TL)", 10_000, 50_000_000, 500_000, step=50_000)
    months = c2.number_input("Vade (ay)", 1, 360, 24)
    result = compare(CAMPAIGNS, ComparisonRequest(amount=amount, months=months,
                                                  product_type="taşıt_finansmanı"))
    for b in result.breakdowns[:5]:
        with st.expander(f"{b.bank} — net {format_try(b.net_economic_cost)} "
                         f"(skor {b.benefit_score:.1f})"):
            st.write(pd.DataFrame([
                ("Kâr payı yükü", b.profit_share_cost),
                ("+ Tahsis ücreti", b.allocation_fee),
                ("+ Ekspertiz/sigorta", b.expertise_fee + b.insurance_fee),
                ("- Nakit iade", -b.reward_amount),
                ("- Para puan", -b.shopping_points),
                ("- İndirim/muafiyet", -(b.discount_gain + b.waiver_gain)),
                ("= NET EKONOMİK MALİYET", b.net_economic_cost),
            ], columns=["Kalem", "Tutar (TL)"]))
            for r in b.reasons:
                st.write("• " + r)

# --------------------------------------------------------- Bank Intelligence
elif PAGE == "Bank Intelligence":
    bank = st.selectbox("Banka", AGENT.banks)
    items = [c for c in CAMPAIGNS if c.bank == bank]
    rates = [c.profit_rate for c in items if c.profit_rate]
    c = st.columns(3)
    c[0].metric("Kayıt", len(items))
    c[1].metric("Ortalama kâr payı", format_pct(sum(rates) / len(rates)) if rates else "-")
    c[2].metric("Ortalama confidence",
                f"{sum(i.confidence_score for i in items)/len(items):.2f}")
    st.dataframe(df_of(items), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- SEZAR Agent
elif PAGE == "SEZAR Agent":
    st.subheader("SEZAR")
    st.caption("AI Financial Agent")
    q = st.text_input("Size nasıl yardımcı olabilirim?",
                      "500.000 TL için 24 ay vadeli en avantajlı taşıt finansmanını bul.")
    if st.button("Sor", type="primary"):
        r = AGENT.ask(q)
        st.code(r.text, language="text")
        with st.expander("Karar izi (trace)"):
            for t in r.trace:
                st.write("• " + t)
        with st.expander("Kanıt kartları"):
            for e in r.evidence:
                st.json(e)

# -------------------------------------------------------------- NLP Inspector
elif PAGE == "NLP Inspector":
    text = st.text_area(
        "Ham finansal metin", height=130,
        value="750.000 TL'ye kadar 36 ay vadeli, aylık %2,05 kâr payı oranıyla "
              "taşıt finansmanı fırsatı. Tahsis ücreti alınmaz.",
    )
    if st.button("Analiz et", type="primary"):
        out = nlp_inspect(text)
        for label, key in [("1 — Original Text", "1_original_text"),
                           ("2 — Cleaned Text", "2_cleaned_text"),
                           ("3 — Normalized Text", "3_normalized_text")]:
            st.markdown(f"**{label}**")
            st.code(out[key], language="text")
        st.markdown("**4 — Ontology Hits**")
        st.write([h["label"] for h in out["4_ontology_hits"]] or "—")
        st.markdown("**5 — Detected Entities (Structured JSON)**")
        st.json({k: str(v) for k, v in out["5_detected_entities"].items()})
        st.markdown("**6 — Classification**")
        st.json(out["6_classification"])
        st.markdown("**7 — Validation**")
        st.json(out["7_validation"])
        st.markdown("**8 — Evidence**")
        st.json(out["8_evidence"])

# ----------------------------------------------------------- Model Performance
elif PAGE == "Model Performance":
    p = Path("benchmark/benchmark_results.json")
    if not p.exists():
        st.info("Önce çalıştırın: `python -m benchmark.run_benchmark`")
    else:
        res = json.loads(p.read_text(encoding="utf-8"))
        st.caption(f"Sürüm {res['version']} — {res['generated_at']}")
        rows = [{"Metrik": k, "Sonuç": v, "Hedef": res["targets"][k],
                 "Durum": res["target_status"].get(k, "-")}
                for k, v in res["headline_metrics"].items() if v is not None]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.warning(res["dataset"]["note"])
        with st.expander("Ayrıntılı sonuçlar"):
            st.json(res)

# --------------------------------------------------------------- System Status
else:
    from nlp.semantic_validator import LLM_ENABLED, llm_available

    st.write(pd.DataFrame([
        ("NLP Core", "aktif"), ("Benefit Engine", "aktif"),
        ("Knowledge Layer (BM25)", "aktif"),
        ("Local LLM", "aktif" if llm_available() else
         ("kapalı (SEZARNEXT_LLM_ENABLED=0)" if not LLM_ENABLED else "erişilemiyor")),
        ("Veri kaynağı", "sentetik demo" if any(c.is_synthetic for c in CAMPAIGNS) else "canlı"),
        ("Kayıt sayısı", str(len(CAMPAIGNS))),
    ], columns=["Bileşen", "Durum"]), use_container_width=True, hide_index=True)
