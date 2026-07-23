"""
lock_in_ui.py — Full LOCK IN UI.
Entry points:
  render_lock_in_page(blueprint, user, groq_client, tavily)
"""

from __future__ import annotations
import streamlit as st
import lock_in_db as db
from lock_in_agents import run_lock_in_agents

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════

LOCK_IN_CSS = """
<style>
.lockin-hero {
    background: linear-gradient(135deg,rgba(239,68,68,0.08) 0%,rgba(245,158,11,0.06) 50%,rgba(15,98,254,0.06) 100%);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.lockin-title {
    font-size: 2rem;
    font-weight: 900;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg,#f87171,#fbbf24,#60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.4rem;
}
.lockin-sub {
    font-size: 0.88rem;
    color: #64748b;
    line-height: 1.65;
    max-width: 600px;
}
.month-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.month-header {
    font-size: 1rem;
    font-weight: 800;
    color: #f1f5f9;
    margin-bottom: 0.3rem;
}
.week-block {
    background: rgba(15,98,254,0.04);
    border: 1px solid rgba(15,98,254,0.1);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
}
.week-title {
    font-size: 0.8rem;
    font-weight: 700;
    color: #60a5fa;
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.task-row {
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    padding: 0.4rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.task-row:last-child { border-bottom: none; }
.task-priority-high   { color: #f87171; font-size: 0.65rem; font-weight: 700; background: rgba(239,68,68,0.1); padding: 1px 7px; border-radius: 8px; }
.task-priority-medium { color: #fbbf24; font-size: 0.65rem; font-weight: 700; background: rgba(245,158,11,0.1); padding: 1px 7px; border-radius: 8px; }
.task-priority-low    { color: #34d399; font-size: 0.65rem; font-weight: 700; background: rgba(52,211,153,0.1); padding: 1px 7px; border-radius: 8px; }
.progress-bar-wrap {
    background: rgba(255,255,255,0.05);
    border-radius: 999px;
    height: 10px;
    overflow: hidden;
    margin: 0.5rem 0;
}
.progress-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg,#3b82f6,#8b5cf6);
    transition: width 0.5s ease;
}
.stat-box {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 0.9rem 1rem;
    text-align: center;
}
.stat-val {
    font-size: 1.6rem;
    font-weight: 900;
    background: linear-gradient(135deg,#60a5fa,#a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.stat-label {
    font-size: 0.68rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 700;
    margin-top: 0.2rem;
}
.competitor-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
}
.market-insight {
    background: rgba(15,98,254,0.05);
    border: 1px solid rgba(15,98,254,0.15);
    border-left: 4px solid #3b82f6;
    border-radius: 0 12px 12px 0;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.83rem;
    color: #cbd5e1;
    line-height: 1.6;
}
</style>
"""

# ══════════════════════════════════════════════════════════════════════════════
# FOUNDER FORM
# ══════════════════════════════════════════════════════════════════════════════

def _render_founder_form(blueprint: dict) -> dict | None:
    """Renders the founder info form. Returns form data dict or None if not submitted."""

    st.markdown(
        '<div style="font-size:1.1rem;font-weight:800;color:#f1f5f9;margin-bottom:0.3rem">👤 Tell us about yourself & your startup</div>'
        '<div style="font-size:0.82rem;color:#64748b;margin-bottom:1.5rem">This helps the AI generate a personalized execution roadmap for your specific situation.</div>',
        unsafe_allow_html=True,
    )

    with st.form("lock_in_form"):
        # ── Founder Details ───────────────────────────────────────────────────
        st.markdown("**🧑 Founder Details**")
        c1, c2, c3 = st.columns(3)
        with c1:
            founder_name = st.text_input("Your Name", placeholder="Priya Sharma")
            team_size    = st.selectbox("Team Size", ["1 (Solo)", "2-3", "4-5", "6-10", "10+"])
        with c2:
            tech_bg   = st.selectbox("Technical Background", ["Strong (Developer/Engineer)", "Moderate", "Non-Technical"])
            biz_bg    = st.selectbox("Business Background", ["Strong (MBA/Sales)", "Moderate", "None"])
        with c3:
            experience = st.selectbox("Startup Experience", ["First startup", "1 previous startup", "2+ startups", "Serial entrepreneur"])
            city       = st.text_input("City", placeholder="Mumbai")

        st.markdown("---")

        # ── Startup Stage & Budget ────────────────────────────────────────────
        st.markdown("**🚀 Startup Status**")
        c1, c2, c3 = st.columns(3)
        with c1:
            startup_stage = st.selectbox("Current Stage", [
                "Idea Only", "MVP Planning", "MVP Built",
                "Beta Testing", "Early Customers", "Revenue Started"
            ])
        with c2:
            budget = st.selectbox("Available Budget", [
                "Bootstrapped (< ₹10K)", "₹10K–₹50K", "₹50K–₹2L",
                "₹2L–₹10L", "₹10L+"
            ])
        with c3:
            funding_status = st.selectbox("Funding Status", [
                "Self Funded", "Friends & Family", "Angel Investment",
                "Incubator Support", "Government Grant", "Not Looking Yet"
            ])

        st.markdown("---")

        # ── Goals & Time ─────────────────────────────────────────────────────
        st.markdown("**🎯 Goals & Commitment**")
        c1, c2, c3 = st.columns(3)
        with c1:
            primary_goal = st.selectbox("Primary Goal", [
                "Launch MVP", "Get First 100 Users", "Raise Funding",
                "Validate Idea", "Reach ₹1L MRR", "Build Community", "Get Incubated"
            ])
        with c2:
            time_commitment = st.selectbox("Time Commitment", [
                "Full Time", "Part Time (20-30 hrs/week)",
                "Weekends Only", "10 hrs/week"
            ])
        with c3:
            roadmap_duration = st.selectbox("Roadmap Duration", ["6 Months", "12 Months"])

        weekly_hours = st.select_slider(
            "Weekly Hours Available",
            options=["10 hrs", "15 hrs", "20 hrs", "30 hrs", "40 hrs", "Full Time (50+ hrs)"],
            value="20 hrs"
        )

        st.markdown("---")

        # ── Team & Resources ──────────────────────────────────────────────────
        st.markdown("**🛠️ Team & Existing Resources**")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.5rem">Team Members (select all that apply)</div>', unsafe_allow_html=True)
            team_roles = st.multiselect(
                "Team roles",
                ["Designer", "Frontend Developer", "Backend Developer", "AI/ML Engineer",
                 "Marketing", "Sales", "Legal", "Finance"],
                label_visibility="collapsed"
            )
        with c2:
            st.markdown('<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.5rem">What you already have</div>', unsafe_allow_html=True)
            existing_resources = st.multiselect(
                "Existing resources",
                ["Website", "Domain", "Prototype/MVP", "GitHub Repo",
                 "Registered Company", "Social Media Pages", "Investor Pitch Deck",
                 "Customer Interviews Done", "Letters of Intent"],
                label_visibility="collapsed"
            )

        st.markdown("---")

        # ── Skill Confidence ──────────────────────────────────────────────────
        st.markdown("**⭐ Rate Your Confidence (1-5)**")
        sk1, sk2, sk3 = st.columns(3)
        with sk1:
            skill_programming = st.slider("Programming", 1, 5, 3)
            skill_marketing   = st.slider("Marketing", 1, 5, 2)
        with sk2:
            skill_ai    = st.slider("AI/ML", 1, 5, 2)
            skill_sales = st.slider("Sales", 1, 5, 2)
        with sk3:
            skill_finance = st.slider("Finance", 1, 5, 2)
            skill_product = st.slider("Product Management", 1, 5, 3)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        submitted = st.form_submit_button(
            "🔒 LOCK IN — Generate My Execution Roadmap",
            use_container_width=True,
            type="primary"
        )

    if submitted:
        return {
            "founder_name":      founder_name,
            "team_size":         team_size,
            "tech_background":   tech_bg,
            "business_background": biz_bg,
            "startup_experience": experience,
            "city":              city,
            "startup_stage":     startup_stage,
            "budget":            budget,
            "funding_status":    funding_status,
            "primary_goal":      primary_goal,
            "time_commitment":   time_commitment,
            "roadmap_duration":  roadmap_duration,
            "weekly_hours":      weekly_hours,
            "team_roles":        team_roles,
            "existing_resources": existing_resources,
            "skills": {
                "programming": skill_programming,
                "ai_ml":       skill_ai,
                "marketing":   skill_marketing,
                "sales":       skill_sales,
                "finance":     skill_finance,
                "product":     skill_product,
            },
        }
    return None


# ══════════════════════════════════════════════════════════════════════════════
# MARKET RESEARCH SECTION
# ══════════════════════════════════════════════════════════════════════════════

def _render_market_research(data: dict) -> None:
    st.markdown("### 📊 Market Research")
    if not data:
        st.info("No market research data available.")
        return

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="stat-box"><div class="stat-val">{data.get("market_size","—")}</div><div class="stat-label">Market Size</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-box"><div class="stat-val">{data.get("cagr","—")}</div><div class="stat-label">Growth Rate</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-box"><div class="stat-val">{len(data.get("opportunities",[]))}</div><div class="stat-label">Opportunities Found</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.5rem">📈 Key Trends</div>', unsafe_allow_html=True)
        for t in data.get("key_trends", []):
            st.markdown(f'<div class="market-insight">📌 {t}</div>', unsafe_allow_html=True)

        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin:0.75rem 0 0.5rem">🚦 Demand Signals</div>', unsafe_allow_html=True)
        for s in data.get("demand_signals", []):
            st.markdown(f'<div class="market-insight" style="border-left-color:#34d399">✅ {s}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.5rem">💡 Opportunities</div>', unsafe_allow_html=True)
        for o in data.get("opportunities", []):
            st.markdown(f'<div class="market-insight" style="border-left-color:#a78bfa">🚀 {o}</div>', unsafe_allow_html=True)

        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin:0.75rem 0 0.5rem">⚠️ Market Risks</div>', unsafe_allow_html=True)
        for r in data.get("risks", []):
            st.markdown(f'<div class="market-insight" style="border-left-color:#f87171">⚠️ {r}</div>', unsafe_allow_html=True)

    if data.get("target_customer_profile"):
        st.markdown(
            f'<div style="background:rgba(16,185,129,0.05);border:1px solid rgba(16,185,129,0.15);'
            f'border-radius:12px;padding:0.9rem 1.1rem;margin-top:0.75rem">'
            f'<div style="font-size:0.72rem;font-weight:700;color:#34d399;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem">🎯 Ideal Customer Profile</div>'
            f'<div style="font-size:0.85rem;color:#cbd5e1;line-height:1.7">{data["target_customer_profile"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    if data.get("india_specific"):
        st.markdown(
            f'<div style="background:rgba(245,158,11,0.05);border:1px solid rgba(245,158,11,0.15);'
            f'border-radius:12px;padding:0.9rem 1.1rem;margin-top:0.75rem">'
            f'<div style="font-size:0.72rem;font-weight:700;color:#f59e0b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem">🇮🇳 India Context</div>'
            f'<div style="font-size:0.85rem;color:#cbd5e1;line-height:1.7">{data["india_specific"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# COMPETITOR INTELLIGENCE SECTION
# ══════════════════════════════════════════════════════════════════════════════

def _render_competitor_intel(data: dict) -> None:
    st.markdown("### 🏆 Competitor Intelligence")
    if not data:
        st.info("No competitor data available.")
        return

    for comp in data.get("competitors", []):
        st.markdown(
            f'<div class="competitor-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">'
            f'<div style="font-weight:800;color:#e2e8f0;font-size:0.95rem">{comp.get("name","")}</div>'
            f'<span style="background:rgba(99,102,241,0.1);color:#a78bfa;border:1px solid rgba(99,102,241,0.2);'
            f'padding:2px 10px;border-radius:8px;font-size:0.7rem;font-weight:700">{comp.get("funding","Unknown")}</span>'
            f'</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-bottom:0.5rem">'
            f'<div style="font-size:0.8rem;color:#94a3b8"><span style="color:#34d399">✓</span> {comp.get("usp","")}</div>'
            f'<div style="font-size:0.8rem;color:#94a3b8"><span style="color:#f87171">✗</span> {comp.get("weakness","")}</div>'
            f'</div>'
            f'<div style="background:rgba(245,158,11,0.05);border-radius:8px;padding:0.5rem 0.75rem;'
            f'font-size:0.78rem;color:#fbbf24;margin-top:0.3rem">'
            f'💡 Learn: {comp.get("what_to_learn","")}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    if data.get("differentiation_strategy"):
        st.markdown(
            f'<div style="background:rgba(15,98,254,0.06);border:1px solid rgba(15,98,254,0.15);'
            f'border-radius:12px;padding:0.9rem 1.1rem;margin-top:0.5rem">'
            f'<div style="font-size:0.72rem;font-weight:700;color:#60a5fa;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem">🎯 Your Differentiation Strategy</div>'
            f'<div style="font-size:0.85rem;color:#cbd5e1;line-height:1.7">{data["differentiation_strategy"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    white_space = data.get("white_space", [])
    if white_space:
        st.markdown('<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin:0.75rem 0 0.5rem">🌟 Untapped Opportunities</div>', unsafe_allow_html=True)
        for ws in white_space:
            st.markdown(f'<div class="market-insight" style="border-left-color:#a78bfa">💎 {ws}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROADMAP SECTION
# ══════════════════════════════════════════════════════════════════════════════

def _render_roadmap(roadmap_data: dict, roadmap_id: int) -> None:
    st.markdown("### 🗺️ Your Execution Roadmap")

    if not roadmap_data or not roadmap_data.get("months"):
        st.info("No roadmap data available.")
        return

    # Load task statuses
    task_statuses = db.get_task_statuses(roadmap_id)

    # Progress stats
    all_tasks = []
    for month in roadmap_data.get("months", []):
        for week in month.get("weeks", []):
            for task in week.get("tasks", []):
                all_tasks.append(task["id"])

    total     = len(all_tasks)
    completed = sum(1 for tid in all_tasks if task_statuses.get(tid, {}).get("status") == "completed")
    pct       = int((completed / total * 100)) if total > 0 else 0

    # Stats row
    s1, s2, s3, s4 = st.columns(4)
    s1.markdown(f'<div class="stat-box"><div class="stat-val">{total}</div><div class="stat-label">Total Tasks</div></div>', unsafe_allow_html=True)
    s2.markdown(f'<div class="stat-box"><div class="stat-val">{completed}</div><div class="stat-label">Completed</div></div>', unsafe_allow_html=True)
    s3.markdown(f'<div class="stat-box"><div class="stat-val">{total-completed}</div><div class="stat-label">Remaining</div></div>', unsafe_allow_html=True)
    s4.markdown(f'<div class="stat-box"><div class="stat-val">{pct}%</div><div class="stat-label">Progress</div></div>', unsafe_allow_html=True)

    st.markdown(
        f'<div style="margin:1rem 0 0.3rem;font-size:0.75rem;color:#64748b">Overall Progress</div>'
        f'<div class="progress-bar-wrap"><div class="progress-bar-fill" style="width:{pct}%"></div></div>',
        unsafe_allow_html=True
    )

    # First week focus
    if roadmap_data.get("first_week_focus"):
        st.markdown(
            f'<div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);'
            f'border-radius:12px;padding:0.85rem 1.1rem;margin:0.75rem 0">'
            f'<span style="color:#f87171;font-weight:700;font-size:0.8rem">⚡ START HERE — Week 1 Focus: </span>'
            f'<span style="color:#fca5a5;font-size:0.83rem">{roadmap_data["first_week_focus"]}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # Month tabs
    months = roadmap_data.get("months", [])
    if not months:
        return

    tab_labels = [f"Month {m.get('month',i+1)}" for i, m in enumerate(months)]
    tabs = st.tabs(tab_labels)

    for tab, month in zip(tabs, months):
        with tab:
            st.markdown(
                f'<div style="font-size:1rem;font-weight:800;color:#f1f5f9;margin-bottom:0.2rem">{month.get("title","")}</div>'
                f'<div style="font-size:0.82rem;color:#64748b;margin-bottom:0.75rem">{month.get("objective","")}</div>',
                unsafe_allow_html=True
            )

            for week in month.get("weeks", []):
                with st.expander(f"📅 Week {week.get('week','')} — {week.get('focus','')}", expanded=week.get("week") == 1):
                    for task in week.get("tasks", []):
                        task_id  = task.get("id", "")
                        status   = task_statuses.get(task_id, {}).get("status", "pending")
                        priority = task.get("priority", "Medium")

                        prio_cls = {"High": "task-priority-high", "Medium": "task-priority-medium", "Low": "task-priority-low"}.get(priority, "task-priority-medium")
                        done     = status == "completed"
                        text_style = "text-decoration:line-through;color:#475569;" if done else "color:#e2e8f0;"

                        col_check, col_content = st.columns([1, 9])
                        with col_check:
                            checked = st.checkbox("", value=done, key=f"task_{task_id}_{roadmap_id}")
                            if checked != done:
                                new_status = "completed" if checked else "pending"
                                db.update_task(roadmap_id, task_id, new_status)
                                st.rerun()
                        with col_content:
                            st.markdown(
                                f'<div style="padding:0.3rem 0">'
                                f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem">'
                                f'<span style="{text_style}font-weight:600;font-size:0.88rem">{task.get("title","")}</span>'
                                f'<span class="{prio_cls}">{priority}</span>'
                                f'<span style="color:#475569;font-size:0.72rem">~{task.get("hours",2)} hrs</span>'
                                f'</div>'
                                f'<div style="font-size:0.78rem;color:#64748b;line-height:1.5">{task.get("description","")}</div>'
                                f'<div style="font-size:0.74rem;color:#475569;margin-top:0.2rem;font-style:italic">Why: {task.get("why","")}</div>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

            # Month milestone
            if month.get("milestone"):
                st.markdown(
                    f'<div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.15);'
                    f'border-radius:10px;padding:0.7rem 1rem;margin-top:0.5rem">'
                    f'<span style="color:#34d399;font-weight:700;font-size:0.78rem">🏁 Month Milestone: </span>'
                    f'<span style="color:#6ee7b7;font-size:0.82rem">{month["milestone"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            if month.get("success_metric"):
                st.markdown(
                    f'<div style="font-size:0.75rem;color:#475569;margin-top:0.3rem">'
                    f'📏 Success metric: {month["success_metric"]}</div>',
                    unsafe_allow_html=True
                )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def render_lock_in_page(blueprint: dict, user: dict, groq_client, tavily) -> None:
    """Main LOCK IN page. Called from app.py routing."""
    st.markdown(LOCK_IN_CSS, unsafe_allow_html=True)

    bp_id      = blueprint.get("id")
    user_email = user.get("email", "")

    # ── Back nav ─────────────────────────────────────────────────────────────
    col_back, _ = st.columns([1, 7])
    with col_back:
        if st.button("← History", key="lockin_back", type="secondary",
                     use_container_width=True):
            st.session_state.hist_lockin_id = None
            st.session_state.hist_open = True
            st.rerun()

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="lockin-hero">'
        f'<div class="lockin-title">🔒 LOCK IN</div>'
        f'<div style="font-size:0.85rem;color:#f59e0b;font-weight:600;margin-bottom:0.4rem">'
        f'{blueprint.get("title","Your Startup")}</div>'
        f'<div class="lockin-sub">You\'re committing to building this startup. '
        f'The AI will generate a personalized execution roadmap, analyze your market, '
        f'research competitors, and guide you step by step from idea to launch.</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Check if profile exists ───────────────────────────────────────────────
    existing_profile = db.get_profile(bp_id, user_email)

    if existing_profile:
        # Profile exists — show roadmap
        profile_id = existing_profile["id"]
        existing_roadmap = db.get_roadmap(profile_id)

        if existing_roadmap:
            # Show full dashboard
            _render_dashboard(existing_profile, existing_roadmap, blueprint)

            # Option to regenerate
            st.markdown("---")
            col1, col2 = st.columns([3,1])
            with col2:
                if st.button("🔄 Regenerate Roadmap", key="lockin_regen", type="secondary"):
                    st.session_state.lockin_show_form = True
                    st.rerun()
        else:
            # Profile but no roadmap — generate
            _generate_roadmap(blueprint, existing_profile, profile_id, user_email, groq_client, tavily)
    else:
        # No profile — show form
        founder_data = _render_founder_form(blueprint)
        if founder_data:
            with st.spinner("💾 Saving your profile..."):
                profile_id = db.save_profile(bp_id, user_email, founder_data)
            st.success("✅ Profile saved! Generating your personalized roadmap...")
            st.rerun()


def _generate_roadmap(blueprint, profile, profile_id, user_email, groq_client, tavily):
    """Run agents and save roadmap."""
    founder_data = profile.get("founder_data", {})

    with st.spinner("🤖 3 AI agents are working on your roadmap (30-60 seconds)..."):
        col1, col2, col3 = st.columns(3)
        col1.markdown('<div style="text-align:center;color:#64748b;font-size:0.8rem">🔬 Market Research Agent</div>', unsafe_allow_html=True)
        col2.markdown('<div style="text-align:center;color:#64748b;font-size:0.8rem">🏆 Competitor Intel Agent</div>', unsafe_allow_html=True)
        col3.markdown('<div style="text-align:center;color:#64748b;font-size:0.8rem">🗺️ Roadmap Agent</div>', unsafe_allow_html=True)

        results = run_lock_in_agents(blueprint, founder_data, groq_client, tavily)

    roadmap_id = db.save_roadmap(
        profile_id=profile_id,
        blueprint_id=blueprint.get("id"),
        user_email=user_email,
        market_research=results.get("market_research", {}),
        competitor_intel=results.get("competitor_intel", {}),
        roadmap=results.get("roadmap", {}),
    )
    st.success("✅ Roadmap generated and saved!")
    st.rerun()


def _render_dashboard(profile, roadmap_row, blueprint):
    """Full dashboard with tabs for market, competitors, roadmap."""
    founder = profile.get("founder_data", {})
    roadmap_id = roadmap_row["id"]

    # Quick stats from founder profile
    st.markdown(
        f'<div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1rem">'
        f'<span style="background:rgba(15,98,254,0.1);color:#60a5fa;padding:3px 12px;border-radius:20px;font-size:0.75rem;font-weight:700">👤 {founder.get("founder_name","Founder")}</span>'
        f'<span style="background:rgba(52,211,153,0.1);color:#34d399;padding:3px 12px;border-radius:20px;font-size:0.75rem;font-weight:700">🎯 {founder.get("primary_goal","")}</span>'
        f'<span style="background:rgba(245,158,11,0.1);color:#f59e0b;padding:3px 12px;border-radius:20px;font-size:0.75rem;font-weight:700">📅 {founder.get("roadmap_duration","")}</span>'
        f'<span style="background:rgba(105,41,196,0.1);color:#a78bfa;padding:3px 12px;border-radius:20px;font-size:0.75rem;font-weight:700">💰 {founder.get("budget","")}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    tab1, tab2, tab3 = st.tabs(["🗺️ Execution Roadmap", "📊 Market Research", "🏆 Competitor Intel"])

    with tab1:
        _render_roadmap(roadmap_row.get("roadmap", {}), roadmap_id)
    with tab2:
        _render_market_research(roadmap_row.get("market_research", {}))
    with tab3:
        _render_competitor_intel(roadmap_row.get("competitor_intel", {}))