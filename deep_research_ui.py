"""
deep_research_ui.py — Streamlit UI for the Startup Intelligence Report.
Call render_deep_research_page() from history_ui.py or app.py.
"""

from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
# REPLACE with
from deep_research import run_deep_research
from deep_research_db import save_deep_research, load_deep_research


# ══════════════════════════════════════════════════════════════════════════════
# SENTIMENT BADGE
# ══════════════════════════════════════════════════════════════════════════════

_SENTIMENT_STYLE = {
    "Hot":     ("🟢", "#16a34a", "#dcfce7"),
    "Neutral": ("🟡", "#ca8a04", "#fef9c3"),
    "Cold":    ("🔴", "#dc2626", "#fee2e2"),
}


def _sentiment_badge(sentiment: str) -> str:
    icon, color, bg = _SENTIMENT_STYLE.get(sentiment, ("⚪", "#64748b", "#f1f5f9"))
    return (
        f'<span style="background:{bg};color:{color};font-weight:700;'
        f'padding:0.25rem 0.75rem;border-radius:999px;font-size:0.8rem">'
        f'{icon} {sentiment}</span>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: COMPETITOR LANDSCAPE
# ══════════════════════════════════════════════════════════════════════════════

def _render_competitors(data: dict) -> None:
    st.markdown("### 🏆 Competitor Landscape")
    
    # Try multiple possible key names
    competitors = (
        data.get("competitors") or
        data.get("competitor_list") or
        data.get("competitive_landscape") or
        []
    )
    positioning = data.get("positioning") or data.get("market_positioning", "")

    if not competitors:
        st.info("No competitor data available.")
        return

    # Table
    cols = st.columns([2, 3, 3, 2, 2])
    headers = ["Company", "USP", "Weakness", "Funding", "Stage"]
    for col, h in zip(cols, headers):
        col.markdown(f"**{h}**")
    st.markdown('<hr style="margin:0.3rem 0">', unsafe_allow_html=True)

    for c in competitors:
        cols = st.columns([2, 3, 3, 2, 2])
        cols[0].markdown(f"**{c.get('name', '')}**")
        cols[1].markdown(c.get("usp", ""))
        cols[2].markdown(c.get("weakness", ""))
        cols[3].markdown(c.get("funding", ""))
        stage = c.get("stage", "")
        stage_color = {"Early": "#3b82f6", "Growth": "#f59e0b", "Mature": "#10b981"}.get(stage, "#64748b")
        cols[4].markdown(
            f'<span style="color:{stage_color};font-weight:600">{stage}</span>',
            unsafe_allow_html=True,
        )

    if positioning:
        st.markdown(
            f'<div style="background:#1e293b;border-left:4px solid #3b82f6;'
            f'padding:0.75rem 1rem;border-radius:0 8px 8px 0;margin-top:1rem;'
            f'color:#cbd5e1;font-size:0.88rem">'
            f'<strong style="color:#93c5fd">📍 Your Positioning:</strong> {positioning}</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: NEWS PULSE
# ══════════════════════════════════════════════════════════════════════════════

def _render_news_pulse(data: dict) -> None:
    sentiment = data.get("sentiment", "Neutral")
    reason    = data.get("sentiment_reason", "")
    signal    = data.get("market_signal", "")
    headlines = data.get("headlines", [])

    st.markdown(
        f'### 📰 Live Market Pulse &nbsp; {_sentiment_badge(sentiment)}',
        unsafe_allow_html=True,
    )

    if reason:
        st.markdown(
            f'<div style="color:#94a3b8;font-size:0.85rem;margin-bottom:0.75rem">{reason}</div>',
            unsafe_allow_html=True,
        )

    for h in headlines:
        url   = h.get("url", "")
        title = h.get("title", "")
        summ  = h.get("summary", "")
        link  = f'[{title}]({url})' if url else f'**{title}**'
        st.markdown(
            f'<div style="background:#0f172a;border:1px solid #1e293b;'
            f'border-radius:8px;padding:0.65rem 1rem;margin-bottom:0.5rem">'
            f'<div style="font-size:0.88rem;color:#e2e8f0;font-weight:600">{title}</div>'
            f'<div style="font-size:0.8rem;color:#94a3b8;margin-top:0.25rem">{summ}</div>'
            + (f'<div style="margin-top:0.3rem"><a href="{url}" target="_blank" '
               f'style="font-size:0.75rem;color:#3b82f6">Read more →</a></div>' if url else "")
            + '</div>',
            unsafe_allow_html=True,
        )

    if signal:
        st.markdown(
            f'<div style="background:#1e293b;border-left:4px solid #f59e0b;'
            f'padding:0.75rem 1rem;border-radius:0 8px 8px 0;margin-top:0.5rem;'
            f'color:#fde68a;font-size:0.85rem">'
            f'<strong>⚡ Market Signal:</strong> {signal}</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: SWOT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def _render_swot(data: dict) -> None:
    st.markdown("### ⚖️ SWOT Analysis")

    quadrants = [
        ("💪 Strengths",     data.get("strengths", []),     "#16a34a", "#052e16"),
        ("⚠️ Weaknesses",    data.get("weaknesses", []),    "#dc2626", "#2d0a0a"),
        ("🚀 Opportunities", data.get("opportunities", []), "#2563eb", "#0c1a3d"),
        ("☠️ Threats",       data.get("threats", []),       "#d97706", "#2d1a00"),
    ]

    col1, col2 = st.columns(2)
    for i, (label, items, color, bg) in enumerate(quadrants):
        col = col1 if i % 2 == 0 else col2
        bullets = "".join(f"<li>{item}</li>" for item in items)
        col.markdown(
            f'<div style="background:{bg};border:1px solid {color}33;'
            f'border-radius:10px;padding:1rem;margin-bottom:0.75rem;min-height:140px">'
            f'<div style="color:{color};font-weight:700;margin-bottom:0.5rem">{label}</div>'
            f'<ul style="color:#cbd5e1;font-size:0.83rem;margin:0;padding-left:1.2rem">{bullets}</ul>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Sector risks
    risks = data.get("sector_risks", [])
    if risks:
        st.markdown("#### 🔴 Sector-Specific Risks")
        for r in risks:
            sev = r.get("severity", "Medium")
            sev_color = {"High": "#dc2626", "Medium": "#d97706", "Low": "#16a34a"}.get(sev, "#64748b")
            st.markdown(
                f'<div style="background:#0f172a;border:1px solid #1e293b;'
                f'border-radius:8px;padding:0.65rem 1rem;margin-bottom:0.4rem;'
                f'display:flex;align-items:flex-start;gap:0.75rem">'
                f'<span style="color:{sev_color};font-weight:700;font-size:0.75rem;'
                f'background:{sev_color}22;padding:0.15rem 0.5rem;border-radius:999px;'
                f'white-space:nowrap;margin-top:0.1rem">{sev}</span>'
                f'<div><div style="color:#e2e8f0;font-size:0.85rem;font-weight:600">'
                f'{r.get("risk","")}</div>'
                f'<div style="color:#64748b;font-size:0.8rem;margin-top:0.2rem">'
                f'💡 {r.get("mitigation","")}</div></div></div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: MARKET SIZING
# ══════════════════════════════════════════════════════════════════════════════

def _render_market_sizing(data: dict) -> None:
    st.markdown("### 📈 Market Sizing (TAM / SAM / SOM)")

    tam = data.get("tam", {})
    sam = data.get("sam", {})
    som = data.get("som", {})

    # Funnel chart using Plotly
    labels = [
        f"TAM — {tam.get('value','?')}",
        f"SAM — {sam.get('value','?')}",
        f"SOM — {som.get('value','?')}",
    ]
    fig = go.Figure(go.Funnel(
        y=labels,
        x=[100, 40, 10],
        textinfo="label",
        marker=dict(color=["#3b82f6", "#8b5cf6", "#10b981"]),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", size=13),
        margin=dict(l=10, r=10, t=10, b=10),
        height=260,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Description cards
    c1, c2, c3 = st.columns(3)
    for col, label, d, color in [
        (c1, "TAM", tam, "#3b82f6"),
        (c2, "SAM", sam, "#8b5cf6"),
        (c3, "SOM", som, "#10b981"),
    ]:
        col.markdown(
            f'<div style="background:#0f172a;border:1px solid {color}44;'
            f'border-radius:10px;padding:0.75rem;text-align:center">'
            f'<div style="color:{color};font-weight:800;font-size:1.1rem">{d.get("value","?")}</div>'
            f'<div style="color:#94a3b8;font-size:0.78rem;margin-top:0.3rem">{d.get("description","")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    cagr      = data.get("cagr", "")
    narrative = data.get("narrative", "")
    assumptions = data.get("key_assumptions", [])

    if cagr:
        st.markdown(
            f'<div style="text-align:center;color:#f59e0b;font-weight:700;'
            f'font-size:0.9rem;margin-top:0.75rem">📊 {cagr}</div>',
            unsafe_allow_html=True,
        )
    if narrative:
        st.markdown(
            f'<div style="color:#94a3b8;font-size:0.85rem;margin-top:0.75rem">{narrative}</div>',
            unsafe_allow_html=True,
        )
    if assumptions:
        with st.expander("Key assumptions"):
            for a in assumptions:
                st.markdown(f"- {a}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: FUNDING PATHWAY
# ══════════════════════════════════════════════════════════════════════════════

def _render_funding(data: dict) -> None:
    st.markdown("### 💰 Funding Pathway")

    advice = data.get("current_stage_advice", "")
    if advice:
        st.markdown(
            f'<div style="background:#1e293b;border-left:4px solid #10b981;'
            f'padding:0.75rem 1rem;border-radius:0 8px 8px 0;color:#a7f3d0;'
            f'font-size:0.88rem;margin-bottom:1rem">{advice}</div>',
            unsafe_allow_html=True,
        )

    # Pitch readiness score
    score = data.get("pitch_readiness_score", 0)
    score_color = "#16a34a" if score >= 70 else "#d97706" if score >= 40 else "#dc2626"
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem">'
        f'<div style="font-size:0.85rem;color:#94a3b8;font-weight:600">Pitch Readiness</div>'
        f'<div style="flex:1;background:#1e293b;border-radius:999px;height:10px">'
        f'<div style="width:{score}%;background:{score_color};height:10px;border-radius:999px"></div>'
        f'</div>'
        f'<div style="color:{score_color};font-weight:800;font-size:1rem">{score}/100</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    tips = data.get("pitch_readiness_tips", [])
    if tips:
        with st.expander("📋 Tips to improve pitch readiness"):
            for t in tips:
                st.markdown(f"- {t}")

    # Schemes
    schemes = data.get("schemes", [])
    if schemes:
        st.markdown("#### 🏛️ Recommended Schemes & Investors")
        for s in schemes:
            stype = s.get("type", "")
            type_color = {
                "Grant": "#16a34a", "Equity": "#2563eb",
                "Debt": "#d97706", "Accelerator": "#8b5cf6",
            }.get(stype, "#64748b")
            url = s.get("url", "")
            name_html = (
                f'<a href="{url}" target="_blank" style="color:#e2e8f0;text-decoration:none">'
                f'{s.get("name","")}</a>'
                if url else s.get("name", "")
            )
            st.markdown(
                f'<div style="background:#0f172a;border:1px solid #1e293b;'
                f'border-radius:8px;padding:0.65rem 1rem;margin-bottom:0.4rem">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<div style="font-weight:600;font-size:0.88rem;color:#e2e8f0">{name_html}</div>'
                f'<span style="color:{type_color};background:{type_color}22;font-size:0.72rem;'
                f'font-weight:700;padding:0.15rem 0.5rem;border-radius:999px">{stype}</span>'
                f'</div>'
                f'<div style="color:#f59e0b;font-size:0.82rem;margin-top:0.2rem">{s.get("amount","")}</div>'
                f'<div style="color:#64748b;font-size:0.78rem">{s.get("eligibility","")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Roadmap
    roadmap = data.get("roadmap", [])
    if roadmap:
        st.markdown("#### 🗺️ Funding Roadmap")
        colors = ["#3b82f6", "#8b5cf6", "#10b981"]
        for i, phase in enumerate(roadmap):
            color = colors[i % len(colors)]
            st.markdown(
                f'<div style="display:flex;gap:0.75rem;margin-bottom:0.5rem;align-items:flex-start">'
                f'<div style="background:{color};color:white;border-radius:999px;'
                f'width:24px;height:24px;display:flex;align-items:center;justify-content:center;'
                f'font-size:0.72rem;font-weight:800;flex-shrink:0;margin-top:0.1rem">{i+1}</div>'
                f'<div><div style="color:{color};font-weight:700;font-size:0.85rem">'
                f'{phase.get("phase","")} '
                f'<span style="color:#64748b;font-weight:400">· {phase.get("timeline","")}</span>'
                f'</div>'
                f'<div style="color:#94a3b8;font-size:0.82rem">{phase.get("action","")}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def render_deep_research_page(blueprint, groq_client, tavily, user_email):
    """
    Full deep research page. Call this from history_ui.py when user
    clicks the Deep Research button on a saved blueprint.

    blueprint: the dict returned by hist.load_blueprint_for_display(id)
    """
    bp_id = blueprint.get("id")
    title = blueprint.get("title", "Startup")

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="margin-bottom:1rem">'
        f'<div style="font-size:1.4rem;font-weight:800;color:#f1f5f9">🔍 Startup Intelligence Report</div>'
        f'<div style="color:#64748b;font-size:0.85rem">{title}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Check cache first ─────────────────────────────────────────────────────
    cached = load_deep_research(bp_id)

    if cached:
        st.success("✅ Loaded from cache — instant results!")
        data = cached
        # Option to re-run
        if st.button("🔄 Refresh Research", key="dr_refresh"):
            with st.spinner("Running fresh deep research... (30-60 seconds)"):
                data = run_deep_research(blueprint, groq_client, tavily)
                save_deep_research(bp_id, user_email, data)
            st.rerun()
    else:
        st.info("🔬 Running deep research for the first time — this takes 30-60 seconds...")
        with st.spinner("Launching 5 research agents in parallel..."):
            data = run_deep_research(blueprint, groq_client, tavily)
            save_deep_research(bp_id, user_email, data)
        st.success("✅ Research complete! Results saved for instant access next time.")

    st.markdown("---")

    # ── Tabs for each section ─────────────────────────────────────────────────
    tabs = st.tabs([
        "🏆 Competitors",
        "📰 News Pulse",
        "⚖️ SWOT & Risks",
        "📈 Market Size",
        "💰 Funding",
    ])

    with tabs[0]:
        _render_competitors(data.get("competitors", {}))
    with tabs[1]:
        _render_news_pulse(data.get("news_pulse", {}))
    with tabs[2]:
        _render_swot(data.get("swot", {}))
    with tabs[3]:
        _render_market_sizing(data.get("market_sizing", {}))
    with tabs[4]:
        _render_funding(data.get("funding", {}))