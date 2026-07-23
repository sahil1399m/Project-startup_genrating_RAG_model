"""
history_ui.py  — Streamlit UI for Blueprint History.

Two entry points called from app.py:
  render_history_page()  — full-page list of saved blueprints
  render_history_view()  — read-only blueprint detail page
"""

from __future__ import annotations
import streamlit as st
import history as hist


# ── Session-state initialiser ─────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
    "hist_open":        False,
    "hist_view_id":     None,
    "hist_search":      "",
    "hist_confirm_del": None,
    "hist_confirm_all": False,
    "hist_mentor_id":   None,
    "hist_lockin_id":   None,
    }
    if "hist_deep_research_id" not in st.session_state:
        st.session_state.hist_deep_research_id = None
    if "hist_lockin_id" not in st.session_state:
        st.session_state.hist_lockin_id = None
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ═════════════════════════════════════════════════════════════════════════════
# HISTORY LIST PAGE
# ═════════════════════════════════════════════════════════════════════════════

def render_history_page(user_email=None) -> None:
    """Full-page history list. Called when hist_open=True."""
    _init_state()

    # ── Header row ────────────────────────────────────────────────────────────
    h1, h2 = st.columns([1, 7])
    with h1:
        if st.button("← Dashboard", key="hp_back", type="primary",
                     use_container_width=True):
            st.session_state.hist_open = False
            st.session_state.hist_view_id = None
            st.session_state.hist_lockin_id = None
            st.rerun()
    with h2:
        st.markdown(
            '<span style="font-size:1.4rem;font-weight:800;color:#f1f5f9;'
            'letter-spacing:-0.03em">📚 Blueprint History</span>'
            '<span style="font-size:0.78rem;color:#475569;margin-left:1rem">'
            'Your previously generated blueprints — replayed without any AI calls</span>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Search + Clear-all row ────────────────────────────────────────────────
    sb1, sb2 = st.columns([5, 1])
    with sb1:
        search_val = st.text_input(
            "", value=st.session_state.hist_search,
            placeholder="🔍  Search by title or idea…",
            key="hp_search", label_visibility="collapsed",
        )
        if search_val != st.session_state.hist_search:
            st.session_state.hist_search = search_val
            st.rerun()
    with sb2:
        if st.button("🗑 Clear All", key="hp_clearall",
                     use_container_width=True, type="secondary"):
            st.session_state.hist_confirm_all = True
            st.rerun()

    # Delete-all confirm
    if st.session_state.hist_confirm_all:
        st.warning("⚠️ **Delete all history?** This cannot be undone.")
        cy, cn, _ = st.columns([1, 1, 5])
        with cy:
            if st.button("Yes, delete all", key="hp_ca_yes",
                         type="primary", use_container_width=True):
                hist.delete_all_blueprints(user_email=user_email)
                st.session_state.hist_confirm_all = False
                st.session_state.hist_view_id = None
                st.rerun()
        with cn:
            if st.button("Cancel", key="hp_ca_no", use_container_width=True):
                st.session_state.hist_confirm_all = False
                st.rerun()

    # ── Load items ────────────────────────────────────────────────────────────
    q = st.session_state.hist_search.strip()
    items = (hist.search_blueprints(q, user_email=user_email)
             if q else hist.list_blueprints(user_email=user_email))

    n = len(items)
    st.markdown(
        f'<div style="font-size:0.75rem;color:#475569;font-weight:600;'
        f'margin-bottom:1.1rem">{n} blueprint{"s" if n != 1 else ""} saved</div>',
        unsafe_allow_html=True,
    )

    # ── Empty state ───────────────────────────────────────────────────────────
    if not items:
        st.markdown(
            '<div style="text-align:center;padding:4rem 1rem;color:#475569">'
            '<div style="font-size:2.8rem;margin-bottom:0.75rem">📭</div>'
            '<div style="font-size:1rem;font-weight:700;color:#64748b;margin-bottom:0.3rem">'
            'No blueprints yet</div>'
            '<div style="font-size:0.84rem">Generate a blueprint from the dashboard — it will appear here automatically.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Blueprint cards ───────────────────────────────────────────────────────
    for bp in items:
        _render_list_card(bp)

def _render_list_card(bp: dict) -> None:
    bp_id = bp["id"]
    fav   = bool(bp.get("is_favorite", 0))
    conf  = bp.get("confidence", "")
    ts    = (bp.get("timestamp") or "")[:16] or "—"

    CONF_COLOR = {"CORRECT": "#10b981", "AMBIGUOUS": "#f59e0b", "INCORRECT": "#ef4444"}
    CONF_BG    = {"CORRECT": "rgba(16,185,129,0.08)", "AMBIGUOUS": "rgba(245,158,11,0.08)", "INCORRECT": "rgba(239,68,68,0.08)"}
    cc = CONF_COLOR.get(conf, "#64748b")
    cb = CONF_BG.get(conf, "rgba(255,255,255,0.04)")
    fav_border = "border-color:rgba(251,191,36,0.35);background:rgba(251,191,36,0.025);" if fav else ""
    
    left, right = st.columns([7, 3])

    with left:
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.025);border:1px solid '
            f'rgba(255,255,255,0.07);border-radius:14px;padding:1rem 1.25rem;{fav_border}">'
            f'<div style="font-size:0.93rem;font-weight:700;color:#e2e8f0;'
            f'margin-bottom:0.5rem;line-height:1.4">{"⭐ " if fav else ""}{bp["title"]}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:0.45rem">'
            f'<span style="background:rgba(15,98,254,0.1);border:1px solid rgba(15,98,254,0.2);'
            f'color:#60a5fa;padding:2px 10px;border-radius:8px;font-size:0.67rem;font-weight:700">'
            f'{bp.get("sector","—")}</span>'
            f'<span style="background:{cb};border:1px solid {cc}44;color:{cc};'
            f'padding:2px 10px;border-radius:8px;font-size:0.67rem;font-weight:700">'
            f'CRAG: {conf or "—"}</span>'
            f'<span style="background:rgba(255,255,255,0.04);color:#64748b;'
            f'padding:2px 10px;border-radius:8px;font-size:0.67rem">'
            f'{bp.get("stage","")}'
            f'{" · " + bp.get("business_model","") if bp.get("business_model") else ""}'
            f'{" · " + bp.get("market","") if bp.get("market") else ""}'
            f'</span></div>'
            f'<div style="font-size:0.7rem;color:#475569">🕐 {ts}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("<div style='height:0.2rem'></div>", unsafe_allow_html=True)

        # 1. View button
        if st.button("👁  View Blueprint", key=f"hp_view_{bp_id}",
                    use_container_width=True, type="primary"):
            st.session_state.hist_view_id = bp_id
            st.session_state.hist_open = False
            st.rerun()
            
        # 2. AI Mentor button (NEW)
        if st.button("🧠 AI Mentor", key=f"hp_mentor_{bp_id}",
                    use_container_width=True, type="secondary"):
            st.session_state.hist_mentor_id = bp_id
            st.session_state.hist_open = False
            st.session_state.hist_view_id = None
            st.rerun()
        
        # 3. Deep Research button  ← ADD ONLY HERE
        if st.button("🔍 Deep Research", key=f"hp_dr_{bp_id}",
                     use_container_width=True, type="secondary"):
            st.session_state.hist_deep_research_id = bp_id
            st.session_state.hist_open = False
            st.rerun()

        # 4. Save + Delete (single fc, dc — no duplicate)
        # 4. LOCK IN button
        if st.button("🔒 LOCK IN", key=f"hp_lockin_{bp_id}",
                     use_container_width=True, type="secondary"):
            st.session_state.hist_lockin_id = bp_id
            st.session_state.hist_open = False
            st.session_state.hist_view_id = None
            st.rerun()

        # 5. Save + Delete (single fc, dc — no duplicate)
        fc, dc = st.columns(2)
        with fc:
            fl = "⭐ Saved" if fav else "☆ Save"
            if st.button(fl, key=f"hp_fav_{bp_id}", use_container_width=True):
                hist.toggle_favorite(bp_id)
                st.rerun()
        with dc:
            if st.session_state.hist_confirm_del == bp_id:
                if st.button("✓ Sure?", key=f"hp_delok_{bp_id}",
                             use_container_width=True, type="primary"):
                    hist.delete_blueprint(bp_id)
                    st.session_state.hist_confirm_del = None
                    if st.session_state.hist_view_id == bp_id:
                        st.session_state.hist_view_id = None
                    st.rerun()
            else:
                if st.button("🗑 Delete", key=f"hp_del_{bp_id}",
                             use_container_width=True):
                    st.session_state.hist_confirm_del = bp_id
                    st.rerun()

    st.markdown("<div style='height:0.35rem'></div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# READ-ONLY BLUEPRINT VIEW
# ═════════════════════════════════════════════════════════════════════════════

def render_history_view(
    blueprint_id: int,
    render_rewrite_card_fn,
    render_policy_brief_fn,
    render_score_bars_fn,
    render_explore_section_fn,
    render_keyword_chips_fn,
    chart_budget_fn,
    chart_budget_donut_fn,
    chart_channels_fn,
    chart_timeline_fn,
    chart_competitors_fn,
    chart_risk_fn,
) -> None:
    _init_state()

    bp = hist.load_blueprint_for_display(blueprint_id)
    if bp is None:
        st.error("Blueprint not found — it may have been deleted.")
        if st.button("← Back to History", key="hv_back_404"):
            st.session_state.hist_view_id = None
            st.session_state.hist_open = True
            st.rerun()
        return

    # ── Navigation bar ────────────────────────────────────────────────────────
    n1, n2, n3 = st.columns([1, 1, 7])
    with n1:
        if st.button("🏠 Dashboard", key="hv_dash", type="primary",
                     use_container_width=True):
            st.session_state.hist_view_id = None
            st.session_state.hist_open = False
            st.rerun()
    with n2:
        if st.button("📚 History", key="hv_list", type="secondary",
                     use_container_width=True):
            st.session_state.hist_view_id = None
            st.session_state.hist_open = True
            st.rerun()
    with n3:
        fav_star = "⭐ " if bp["is_favorite"] else ""
        st.markdown(
            f'<div style="padding-top:0.4rem">'
            f'<span style="font-size:1.05rem;font-weight:800;color:#f1f5f9">'
            f'{fav_star}{bp["title"]}</span>'
            f'<span style="font-size:0.72rem;color:#475569;margin-left:0.9rem">'
            f'Saved {bp["timestamp"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Read-only banner ──────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,rgba(15,98,254,0.08),rgba(105,41,196,0.06));'
        'border:1px solid rgba(15,98,254,0.2);border-left:4px solid #3b82f6;'
        'border-radius:12px;padding:0.72rem 1.1rem;display:flex;align-items:center;'
        'gap:0.75rem;margin:0.7rem 0 1.1rem">'
        '<span style="font-size:1.15rem">🔒</span>'
        '<div><div style="font-size:0.83rem;font-weight:700;color:#93c5fd">'
        'Viewing Saved Blueprint — Read Only</div>'
        '<div style="font-size:0.7rem;color:#475569;margin-top:0.1rem">'
        'No AI models are called. All data is loaded from local storage.</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Metadata chips ────────────────────────────────────────────────────────
    conf = bp.get("confidence", "")
    badge_conf = {
        "CORRECT":   "badge-crag-correct",
        "AMBIGUOUS": "badge-crag-ambiguous",
        "INCORRECT": "badge-crag-incorrect",
    }.get(conf, "")
    st.markdown(
        f'<span class="badge badge-ibm">{bp.get("sector","")}</span>'
        f'<span class="badge badge-groq">{bp.get("stage","")}</span>'
        f'<span class="badge badge-gemini">{bp.get("business_model","")}</span>'
        f'<span class="badge badge-rag">{bp.get("market","")}</span>'
        f'<span class="badge {badge_conf}">CRAG: {conf}</span>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Original idea ─────────────────────────────────────────────────────────
    with st.expander("💡 Original Startup Idea", expanded=False):
        st.markdown(
            f'<div class="card" style="white-space:pre-wrap;font-size:0.86rem;'
            f'color:#cbd5e1;line-height:1.75">{bp["original_query"]}</div>',
            unsafe_allow_html=True,
        )

    if bp.get("rewritten_query"):
        render_rewrite_card_fn(bp["rewritten_query"])

    if bp.get("keywords"):
        st.markdown('<div class="section-label">🔑 Extracted Keywords</div>',
                    unsafe_allow_html=True)
        render_keyword_chips_fn(bp["keywords"])
        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    if bp.get("summary"):
        render_policy_brief_fn(bp["summary"])

    # ── Overview metrics ──────────────────────────────────────────────────────
    gtm_data        = bp.get("gtm_data", {})
    bmc_data        = bp.get("bmc_data", {})
    budget_data     = bp.get("budget_data", {})
    investor_data   = bp.get("investor_data", {})
    competitor_data = bp.get("competitor_data", {})
    risk_data       = bp.get("risk_data", {})
    explore_results = bp.get("explore_results", [])
    sources         = bp.get("sources", [])

    st.markdown('<div class="section-header">📊 Blueprint Overview</div>',
                unsafe_allow_html=True)
    m1, m2, m3, m4, m5 = st.columns(5)
    for col, (val, label, sub) in zip(
        [m1, m2, m3, m4, m5],
        [
            (gtm_data.get("market_size", "—"),                 "Est. Market Size", ""),
            (len(bmc_data.get("revenue_streams", [])),          "Revenue Streams",  ""),
            (f'₹{budget_data.get("total_12_months",0):,.0f}',  "12-Month Budget",  ""),
            (len(investor_data.get("government_schemes", [])),  "Govt Schemes",     "via CRAG RAG"),
            (conf,                                              "CRAG Confidence",  ""),
        ],
    ):
        with col:
            sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value" style="font-size:{"1.4rem" if len(str(val))>6 else "1.85rem"}">'
                f'{val}</div><div class="metric-label">{label}</div>{sub_html}</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        f'<div style="margin:0.6rem 0">'
        f'<span class="badge badge-ibm">IBM Granite 4.0</span>'
        f'<span class="badge badge-groq">Groq Llama 3.3</span>'
        f'<span class="badge badge-gemini">✨ Gemini Flash</span>'
        f'<span class="badge {badge_conf}">CRAG: {conf}</span>'
        f'&nbsp;<span style="color:#475569;font-size:0.72rem">'
        f'Sources: {", ".join(sources[:6])}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr>', unsafe_allow_html=True)

    # ── 7 Tabs ────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📋  Business Model", "💰  Budget", "📣  GTM",
        "🤝  Investors", "🏆  Competitors", "⚠️  Risks", "🔬  CRAG Pipeline",
    ])
    with tab1:
        _tab_bmc(bmc_data)
    with tab2:
        _tab_budget(budget_data, chart_budget_fn, chart_budget_donut_fn)
    with tab3:
        _tab_gtm(gtm_data, explore_results, conf,
                 chart_channels_fn, chart_timeline_fn, render_explore_section_fn)
    with tab4:
        _tab_investors(investor_data, conf)
    with tab5:
        _tab_competitors(competitor_data, chart_competitors_fn)
    with tab6:
        _tab_risks(risk_data, chart_risk_fn)
    with tab7:
        _tab_crag(bp, render_score_bars_fn)

    # ── Bottom nav ────────────────────────────────────────────────────────────
    st.markdown('<hr>', unsafe_allow_html=True)
    b1, _, b2 = st.columns([2, 5, 2])
    with b1:
        if st.button("🏠 Back to Dashboard", key="hv_bot_dash",
                     type="primary", use_container_width=True):
            st.session_state.hist_view_id = None
            st.session_state.hist_open = False
            st.rerun()
    with b2:
        if st.button("📚 Back to History", key="hv_bot_list",
                     type="secondary", use_container_width=True):
            st.session_state.hist_view_id = None
            st.session_state.hist_open = True
            st.rerun()


# ── Tab renderers ─────────────────────────────────────────────────────────────

def _tab_bmc(bmc_data: dict) -> None:
    st.markdown('<div class="section-header">Business Model Canvas — 9 Building Blocks</div>',
                unsafe_allow_html=True)
    bmc_map = [
        ("customer_segments",      "👥", "Customer Segments",      "#3b82f6"),
        ("value_propositions",     "💡", "Value Propositions",     "#8b5cf6"),
        ("channels",               "📢", "Channels",               "#10b981"),
        ("customer_relationships", "🤝", "Customer Relationships", "#3b82f6"),
        ("revenue_streams",        "💰", "Revenue Streams",        "#8b5cf6"),
        ("key_resources",          "🔑", "Key Resources",          "#10b981"),
        ("key_activities",         "⚙️", "Key Activities",         "#3b82f6"),
        ("key_partners",           "🤲", "Key Partners",           "#8b5cf6"),
        ("cost_structure",         "💸", "Cost Structure",         "#10b981"),
    ]
    for row in [bmc_map[:3], bmc_map[3:6], bmc_map[6:]]:
        cols = st.columns(3)
        for col, (key, icon, label, color) in zip(cols, row):
            with col:
                items = bmc_data.get(key, [])
                rows_html = "".join(
                    f'<div class="bmc-item"><span class="bmc-bullet">▸</span><span>{i}</span></div>'
                    for i in items
                ) or '<div class="bmc-item"><span style="color:#475569;font-style:italic;font-size:0.76rem">No data</span></div>'
                st.markdown(
                    f'<div class="bmc-block"><div class="bmc-icon">{icon}</div>'
                    f'<div class="bmc-label" style="color:{color}">{label}</div>'
                    f'{rows_html}</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)


def _tab_budget(budget_data: dict, chart_budget_fn, chart_donut_fn) -> None:
    st.markdown('<div class="section-header">Phase-wise Budget Estimate</div>',
                unsafe_allow_html=True)
    if not budget_data.get("phases"):
        st.info("No budget data saved for this blueprint.")
        return
    bc1, bc2 = st.columns([3, 2])
    with bc1:
        st.plotly_chart(chart_budget_fn(budget_data), use_container_width=True)
    with bc2:
        st.plotly_chart(chart_donut_fn(budget_data), use_container_width=True)
    ph_cols = st.columns(len(budget_data["phases"]) or 1)
    for col, phase in zip(ph_cols, budget_data["phases"]):
        with col:
            items_html = "".join(
                f'<div style="font-size:0.8rem;color:#94a3b8;padding:5px 0;'
                f'border-bottom:1px solid rgba(255,255,255,0.04);'
                f'display:flex;justify-content:space-between;align-items:center">'
                f'<span>▸ {i["item"]}</span>'
                f'<span style="color:#60a5fa;font-weight:600;font-family:\'JetBrains Mono\',monospace;'
                f'font-size:0.77rem">₹{i["amount"]:,.0f}</span></div>'
                for i in phase.get("items", [])
            )
            st.markdown(
                f'<div class="card">'
                f'<div style="font-weight:800;color:#60a5fa;margin-bottom:0.2rem;font-size:0.95rem">{phase["name"]}</div>'
                f'<div style="font-size:0.71rem;color:#475569;margin-bottom:0.7rem;text-transform:uppercase;letter-spacing:0.05em;font-weight:600">{phase["duration"]}</div>'
                f'{items_html}'
                f'<div style="font-weight:800;color:#34d399;margin-top:0.7rem;font-size:0.92rem;font-family:\'JetBrains Mono\',monospace">₹{phase["total"]:,.0f}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.info(f"💡 **Funding suggestion:** {budget_data.get('funding_suggestion','')}")
    st.success(f"**Total 12-Month Investment: ₹{budget_data.get('total_12_months',0):,.0f}**")


def _tab_gtm(gtm_data, explore_results, conf,
             chart_channels_fn, chart_timeline_fn, render_explore_fn) -> None:
    st.markdown('<div class="section-header">Go-to-Market Strategy</div>',
                unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    with g1:
        st.markdown(
            f'<div class="card-blue">'
            f'<div style="font-size:0.7rem;font-weight:700;color:#3b82f6;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:0.6rem">🎯 Target Market</div>'
            f'<div style="color:#cbd5e1;font-size:0.87rem;line-height:1.75">{gtm_data.get("target_market","—")}</div>'
            f'<div style="margin-top:0.75rem;padding-top:0.65rem;border-top:1px solid rgba(15,98,254,0.15);font-size:0.7rem;font-weight:700;color:#3b82f6;text-transform:uppercase;letter-spacing:0.07em">📈 Est. Market Size</div>'
            f'<div style="font-size:1.3rem;font-weight:900;color:#60a5fa;margin-top:0.25rem;letter-spacing:-0.02em">{gtm_data.get("market_size","—")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.6rem">📊 Key Metrics to Track</div>', unsafe_allow_html=True)
        for m in gtm_data.get("key_metrics", []):
            st.markdown(f'<div style="font-size:0.83rem;color:#94a3b8;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);display:flex;align-items:center;gap:7px"><span style="color:#3b82f6;font-size:0.7rem">◆</span> {m}</div>', unsafe_allow_html=True)
    with g2:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.7rem">🚀 Launch Strategy</div>', unsafe_allow_html=True)
        for i, step in enumerate(gtm_data.get("launch_strategy", []), 1):
            st.markdown(
                f'<div class="card" style="padding:0.7rem 1rem;margin-bottom:0.5rem;border-left:3px solid #3b82f6">'
                f'<span style="color:#3b82f6;font-weight:800;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em">Step {i}</span>'
                f'<div style="font-size:0.85rem;color:#cbd5e1;margin-top:0.3rem;line-height:1.5">{step}</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    if gtm_data.get("growth_channels"):
        st.plotly_chart(chart_channels_fn(gtm_data["growth_channels"]), use_container_width=True)
        st.caption("Each bar shows channel priority — longer = higher priority.")
    if gtm_data.get("milestones"):
        st.plotly_chart(chart_timeline_fn(gtm_data["milestones"]), use_container_width=True)
        st.caption("Hover any milestone dot to see the full goal description.")
    render_explore_fn(explore_results, conf)


def _tab_investors(investor_data: dict, conf: str) -> None:
    st.markdown('<div class="section-header">Investors & Government Schemes</div>', unsafe_allow_html=True)
    schemes = investor_data.get("government_schemes", [])
    st.markdown(f'<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.8rem">🏛️ Government Schemes — via CRAG <span style="color:#60a5fa">({conf.lower()} confidence)</span></div>', unsafe_allow_html=True)
    sc_cols = st.columns(min(len(schemes), 3) or 1)
    for i, s in enumerate(schemes):
        with sc_cols[i % len(sc_cols)]:
            st.markdown(
                f'<div class="card"><div style="font-weight:700;color:#60a5fa;margin-bottom:0.55rem;font-size:0.9rem">📜 {s.get("name","")}</div>'
                f'<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.4rem;line-height:1.55"><span style="color:#e2e8f0;font-weight:600">Benefit:</span> {s.get("benefit","")}</div>'
                f'<div style="font-size:0.8rem;color:#94a3b8;line-height:1.55"><span style="color:#e2e8f0;font-weight:600">Eligibility:</span> {s.get("eligibility","")}</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown('<hr>', unsafe_allow_html=True)
    i1, i2 = st.columns(2)
    with i1:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.7rem">💼 Investor Types</div>', unsafe_allow_html=True)
        for inv in investor_data.get("investor_types", []):
            st.markdown(
                f'<div class="card" style="padding:0.7rem 1rem">'
                f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.3rem">'
                f'<span style="color:#a78bfa;font-weight:700">{inv.get("type","")}</span>'
                f'<span style="font-size:0.7rem;background:rgba(105,41,196,0.1);color:#a78bfa;padding:2px 9px;border-radius:8px;border:1px solid rgba(105,41,196,0.2)">{inv.get("stage","")}</span></div>'
                f'<div style="font-size:0.77rem;color:#64748b">{", ".join(inv.get("examples",[]))}</div></div>',
                unsafe_allow_html=True,
            )
    with i2:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.7rem">🏢 Incubators & Accelerators</div>', unsafe_allow_html=True)
        for inc in investor_data.get("incubators", []):
            st.markdown(
                f'<div class="card" style="padding:0.7rem 1rem">'
                f'<div style="font-weight:700;color:#34d399;margin-bottom:0.2rem">{inc.get("name","")}</div>'
                f'<div style="font-size:0.76rem;color:#64748b">📍 {inc.get("location","")} &nbsp;·&nbsp; 🎯 {inc.get("focus","")}</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.9rem">🗺️ Funding Roadmap</div>', unsafe_allow_html=True)
    roadmap = investor_data.get("funding_roadmap", [])
    rm_cols = st.columns(len(roadmap) or 1)
    for i, stg in enumerate(roadmap):
        with rm_cols[i]:
            st.markdown(
                f'<div class="funding-stage"><div class="funding-stage-name">{stg.get("stage","")}</div>'
                f'<div class="funding-stage-amount">{stg.get("amount","")}</div>'
                f'<div class="funding-stage-time">{stg.get("timeline","")}</div>'
                f'<div class="funding-stage-src">{stg.get("source","")}</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.6rem">💬 Pitch Tips</div>', unsafe_allow_html=True)
    for tip in investor_data.get("pitch_tips", []):
        st.success(f"💡 {tip}")


def _tab_competitors(competitor_data: dict, chart_fn) -> None:
    st.markdown('<div class="section-header">Competitive Landscape</div>', unsafe_allow_html=True)
    cc1, cc2 = st.columns([2, 3])
    with cc1:
        if competitor_data.get("competitors"):
            st.plotly_chart(chart_fn(competitor_data), use_container_width=True)
    with cc2:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.7rem">⚔️ Competitor Breakdown</div>', unsafe_allow_html=True)
        for comp in competitor_data.get("competitors", []):
            is_us    = comp.get("name","") == "Our Startup"
            border   = "border-left:3px solid #3b82f6" if is_us else ""
            nc       = "#60a5fa" if is_us else "#e2e8f0"
            badge_bg = "rgba(15,98,254,0.12)" if is_us else "rgba(255,255,255,0.06)"
            badge_c  = "#93c5fd" if is_us else "#94a3b8"
            st.markdown(
                f'<div class="card" style="{border}">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.45rem">'
                f'<span style="font-weight:700;color:{nc};font-size:0.92rem">{comp.get("name","")}</span>'
                f'<span style="background:{badge_bg};color:{badge_c};padding:3px 10px;border-radius:10px;font-size:0.71rem;font-weight:700">{comp.get("market_share",0)}% share</span></div>'
                f'<div style="font-size:0.8rem;color:#94a3b8;display:flex;align-items:flex-start;gap:5px"><span style="color:#34d399">✓</span> {comp.get("strength","")}</div>'
                f'<div style="font-size:0.8rem;color:#94a3b8;margin-top:0.2rem;display:flex;align-items:flex-start;gap:5px"><span style="color:#f87171">✗</span> {comp.get("weakness","")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.markdown('<hr>', unsafe_allow_html=True)
    dc, gc = st.columns(2)
    with dc:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.7rem">🌟 Our Differentiators</div>', unsafe_allow_html=True)
        for d in competitor_data.get("our_differentiators", []):
            st.markdown(f'<div class="card-green" style="padding:0.65rem 1rem;margin-bottom:0.5rem"><span style="color:#34d399;font-weight:600;font-size:0.84rem">⭐ {d}</span></div>', unsafe_allow_html=True)
    with gc:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.7rem">🔍 Market Gaps to Exploit</div>', unsafe_allow_html=True)
        for g in competitor_data.get("market_gaps", []):
            st.markdown(f'<div class="card-blue" style="padding:0.65rem 1rem;margin-bottom:0.5rem"><span style="color:#60a5fa;font-weight:600;font-size:0.84rem">💎 {g}</span></div>', unsafe_allow_html=True)


def _tab_risks(risk_data: dict, chart_fn) -> None:
    st.markdown('<div class="section-header">Risk Assessment Matrix</div>', unsafe_allow_html=True)
    if risk_data.get("risks"):
        st.plotly_chart(chart_fn(risk_data), use_container_width=True)
        st.caption("Each bubble = a risk — X axis: probability, Y axis: severity.")
    rc1, rc2 = st.columns(2)
    for i, risk in enumerate(risk_data.get("risks", [])):
        sev = risk.get("severity","Medium")
        emoji = {"High":"🔴","Medium":"🟡","Low":"🟢"}.get(sev,"🟡")
        with (rc1 if i % 2 == 0 else rc2):
            st.markdown(
                f'<div class="card">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">'
                f'<span style="font-weight:700;color:#e2e8f0;font-size:0.9rem">{emoji} {risk.get("category","")}</span>'
                f'<span class="risk-{sev.lower()}">{sev}</span></div>'
                f'<div style="font-size:0.83rem;color:#94a3b8;margin-bottom:0.5rem;line-height:1.55">{risk.get("risk","")}</div>'
                f'<div style="font-size:0.78rem;background:rgba(52,211,153,0.05);border:1px solid rgba(52,211,153,0.13);border-radius:10px;padding:0.5rem 0.7rem;color:#34d399;line-height:1.55">🛡️ {risk.get("mitigation","")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _tab_crag(bp: dict, render_score_bars_fn) -> None:
    conf   = bp.get("confidence","")
    action = bp.get("action","")
    logits = bp.get("raw_logits",[])

    st.markdown('<div class="section-header">CRAG — Pipeline Trace (Saved)</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.8rem;color:#475569;margin-bottom:1.4rem;font-style:italic">Reproduced from saved snapshot — no models re-run.</div>', unsafe_allow_html=True)

    badge_cls = {"CORRECT":"crag-action-correct","AMBIGUOUS":"crag-action-ambiguous","INCORRECT":"crag-action-incorrect"}.get(conf,"")
    st.markdown(
        f'<div class="crag-action-box {badge_cls}">Action triggered: <b>{conf}</b><br>'
        f'<span style="font-weight:400;font-size:0.83rem">{action}</span></div>',
        unsafe_allow_html=True,
    )
    if logits:
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        render_score_bars_fn(logits)

    rq = bp.get("retrieval_queries", [])
    if rq:
        st.markdown('<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin:1rem 0 0.5rem">Retrieval queries → Tavily</div>', unsafe_allow_html=True)
        for q in rq[:3]:
            st.markdown(f'<div style="font-size:0.77rem;color:#64748b;background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:0.4rem 0.65rem;margin-bottom:4px;line-height:1.5">{q}</div>', unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)
    pc1, pc2 = st.columns(2)
    with pc1:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.6rem">📄 Internal Knowledge (PDF)</div>', unsafe_allow_html=True)
        internal = bp.get("internal_context","")
        if internal:
            st.markdown(f'<div class="card"><p style="color:#94a3b8;font-size:0.8rem;line-height:1.7;margin:0">{internal[:1000]}…</p></div>', unsafe_allow_html=True)
        else:
            st.info("Not used — INCORRECT confidence; internal docs discarded.")
    with pc2:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.6rem">🌐 External Knowledge (Tavily)</div>', unsafe_allow_html=True)
        external = bp.get("external_context","")
        if external:
            st.markdown(f'<div class="card"><p style="color:#94a3b8;font-size:0.8rem;line-height:1.7;margin:0">{external[:1000]}…</p></div>', unsafe_allow_html=True)
        else:
            st.info("Not used — CORRECT confidence; PDF-only was sufficient.")

    source_links = bp.get("source_links", [])
    if source_links:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin:1rem 0 0.5rem">Sources</div>', unsafe_allow_html=True)
        for src in source_links:
            name = src.get("name",""); url = src.get("url","")
            icon = "🌐" if url else "📄"
            link = f'<a href="{url}" target="_blank" style="color:#60a5fa">{name}</a>' if url else name
            st.markdown(f'<div style="font-size:0.8rem;color:#94a3b8;padding:3px 0">{icon} {link}</div>', unsafe_allow_html=True)
