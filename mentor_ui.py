"""
mentor_ui.py
─────────────
Streamlit UI for the AI Startup Mentor panel.
Renders as a full-page experience after blueprint generation.

Entry point: render_mentor_page(...)
Called from app.py when st.session_state.page == "mentor"
"""

from __future__ import annotations
import streamlit as st
import uuid

from mentor.context       import build_mentor_context
from mentor.mentor_agent  import ask as mentor_ask, create_session


# ── Intent badge config ────────────────────────────────────────────────────────
_INTENT_META = {
    "MARKET_VALIDATION":   ("📊", "#3b82f6", "Market Validation"),
    "FUNDING":             ("💰", "#10b981", "Funding"),
    "LEGAL":               ("⚖️",  "#f59e0b", "Legal"),
    "TECHNOLOGY":          ("⚙️",  "#6366f1", "Technology"),
    "COMPETITOR":          ("🏆", "#ef4444", "Competitor"),
    "MARKETING":           ("📣", "#ec4899", "Marketing"),
    "GTM":                 ("🚀", "#0ea5e9", "GTM Strategy"),
    "FINANCIAL":           ("📈", "#10b981", "Financial"),
    "HIRING":              ("👥", "#8b5cf6", "Hiring"),
    "PRODUCT_DEVELOPMENT": ("🛠️",  "#f97316", "Product Dev"),
    "GOVT_SCHEMES":        ("🏛️",  "#60a5fa", "Govt Schemes"),
    "RISK_ANALYSIS":       ("⚠️",  "#f87171", "Risk Analysis"),
    "INVESTOR_PREP":       ("🤝", "#a78bfa", "Investor Prep"),
    "EXECUTION_ROADMAP":   ("🗺️",  "#34d399", "Execution Roadmap"),
    "GENERAL":             ("💬", "#94a3b8", "General"),
}

_STARTER_QUESTIONS = [
    "Is this startup actually feasible?",
    "What competitors are strongest?",
    "Which government schemes should I apply for?",
    "Give me a 6-month execution roadmap.",
    "How should I raise my first funding?",
    "What risks am I missing?",
    "How would Y Combinator evaluate this idea?",
    "Suggest an MVP I can build in 30 days.",
    "Estimate my TAM SAM SOM.",
    "Generate investor questions for my pitch.",
    "How can I reduce burn rate?",
    "What should I build first?",
    "Should I pivot?",
    "Generate customer interview questions.",
    "Critique my business model.",
]


# ── State helpers ─────────────────────────────────────────────────────────────

def _init_mentor_state() -> None:
    defaults = {
        "mentor_session":       None,
        "mentor_session_id":    None,
        "mentor_messages_ui":   [],   # list of {role, content, intent, citations, tools_used}
        "mentor_input_key":     0,    # increment to clear text input
        "mentor_pending_input": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _get_or_create_session(ctx: dict) -> object:
    """Return existing MentorSession or create a new one."""
    if st.session_state.mentor_session is None:
        sid = str(uuid.uuid4())
        st.session_state.mentor_session_id = sid
        st.session_state.mentor_session    = create_session(ctx, session_id=sid)
    return st.session_state.mentor_session


# ── Main render function ───────────────────────────────────────────────────────

def render_mentor_page(
    *,
    idea: str,
    sector: str,
    stage: str,
    business_model: str,
    market: str,
    crag_result: dict,
    bmc_data: dict,
    budget_data: dict,
    gtm_data: dict,
    investor_data: dict,
    competitor_data: dict,
    risk_data: dict,
    blueprint_id: int | None,
    user_email: str,
    groq_client,
    granite_client,
    embedder,
    collection,
    tavily_client,
) -> None:
    """
    Full-page mentor UI. Called from app.py routing.
    All blueprint data is passed in directly (no re-generation).
    """
    _init_mentor_state()

    # ── Build MentorContext once and store it ──────────────────────────────────
    if st.session_state.mentor_session is None:
        ctx = build_mentor_context(
            idea=idea,
            sector=sector,
            stage=stage,
            business_model=business_model,
            market=market,
            crag_result=crag_result,
            bmc_data=bmc_data,
            budget_data=budget_data,
            gtm_data=gtm_data,
            investor_data=investor_data,
            competitor_data=competitor_data,
            risk_data=risk_data,
        )
        _get_or_create_session(ctx)

    session = st.session_state.mentor_session
    ctx     = session.ctx

    # ── Top navigation bar ────────────────────────────────────────────────────
    _render_mentor_topbar(idea, sector, stage)

    # ── Mentor hero banner ────────────────────────────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,rgba(15,98,254,0.08) 0%,rgba(105,41,196,0.07) 100%);
border:1px solid rgba(15,98,254,0.18);border-radius:20px;padding:1.6rem 2rem;margin-bottom:1.6rem;
display:flex;align-items:flex-start;gap:1.5rem">
  <div style="font-size:2.5rem;flex-shrink:0">🧠</div>
  <div>
    <div style="font-size:1.25rem;font-weight:900;color:#f1f5f9;letter-spacing:-0.025em;margin-bottom:0.3rem">
      AI Startup Mentor
    </div>
    <div style="font-size:0.84rem;color:#64748b;line-height:1.65;max-width:640px">
      I have read your complete startup blueprint for <b style="color:#93c5fd">{idea[:80]}{'…' if len(idea)>80 else ''}</b>. 
      Ask me anything — I'll answer using your blueprint data, official policy documents, and live web research.
      Every answer is evidence-backed. I never hallucinate.
    </div>
    <div style="margin-top:0.75rem">
      <span style="background:rgba(15,98,254,0.1);border:1px solid rgba(15,98,254,0.2);
      color:#60a5fa;padding:3px 12px;border-radius:20px;font-size:0.72rem;font-weight:700;margin-right:6px">
      IBM Granite 4.0</span>
      <span style="background:rgba(105,41,196,0.1);border:1px solid rgba(105,41,196,0.2);
      color:#a78bfa;padding:3px 12px;border-radius:20px;font-size:0.72rem;font-weight:700;margin-right:6px">
      Groq Intent Engine</span>
      <span style="background:rgba(52,211,153,0.1);border:1px solid rgba(52,211,153,0.2);
      color:#34d399;padding:3px 12px;border-radius:20px;font-size:0.72rem;font-weight:700">
      ChromaDB + Tavily RAG</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Main layout: chat (left) + sidebar (right) ────────────────────────────
    chat_col, side_col = st.columns([7, 3], gap="large")

    with side_col:
        _render_sidebar(ctx, idea, sector, stage, business_model, market)

    with chat_col:
        _render_chat_area(
            session=session,
            blueprint_id=blueprint_id,
            user_email=user_email,
            groq_client=groq_client,
            granite_client=granite_client,
            embedder=embedder,
            collection=collection,
            tavily_client=tavily_client,
        )


# ── Top navigation bar ─────────────────────────────────────────────────────────

def _render_mentor_topbar(idea: str, sector: str, stage: str) -> None:
    t1, t2, t3, t4 = st.columns([4, 4, 1, 1])
    with t1:
        st.markdown(
            '<div class="nav-logo">'
            '<span class="nav-logo-icon">🧠</span>'
            'AI Startup Mentor'
            '</div>',
            unsafe_allow_html=True,
        )
    with t2:
        st.markdown(
            f'<div style="padding-top:0.35rem">'
            f'<span class="badge badge-ibm">IBM Granite 4.0</span>'
            f'<span class="badge badge-groq">Groq Intent Engine</span>'
            f'<span class="badge badge-rag">RAG Grounded</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with t3:
        if st.button("← Blueprint", key="mentor_back_bp", type="primary"):
            st.session_state.page = "dashboard"
            st.rerun()
    with t4:
        if st.button("Sign Out", key="mentor_signout", type="secondary"):
            for k in ["logged_in", "user", "page", "blueprints"]:
                st.session_state[k] = {
                    "logged_in": False, "user": None,
                    "page": "login", "blueprints": [],
                }[k]
            # clear mentor state too
            st.session_state.mentor_session     = None
            st.session_state.mentor_messages_ui = []
            st.rerun()
    st.markdown('<hr>', unsafe_allow_html=True)


# ── Sidebar ─────────────────────────────────────────────────────────────────────

def _render_sidebar(ctx: dict, idea: str, sector: str, stage: str,
                    business_model: str, market: str) -> None:

    # Blueprint identity card
    st.markdown("""
<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);
border-radius:16px;padding:1.1rem 1.2rem;margin-bottom:1rem">
<div style="font-size:0.65rem;font-weight:700;color:#475569;text-transform:uppercase;
letter-spacing:0.1em;margin-bottom:0.7rem">📋 Blueprint Context</div>
""", unsafe_allow_html=True)

    chips = [
        ("🏭", sector),
        ("📊", stage),
        ("💼", business_model),
        ("🗺️", market),
    ]
    for icon, val in chips:
        if val:
            st.markdown(
                f'<div style="font-size:0.8rem;color:#94a3b8;padding:4px 0;'
                f'border-bottom:1px solid rgba(255,255,255,0.04);display:flex;gap:0.5rem">'
                f'<span style="color:#60a5fa">{icon}</span> {val}</div>',
                unsafe_allow_html=True,
            )

    budget = ctx.get("budget", {}).get("total_12_months", 0)
    if budget:
        st.markdown(
            f'<div style="font-size:0.8rem;color:#34d399;padding:4px 0;font-weight:600">'
            f'💰 Budget: ₹{budget:,.0f}</div>',
            unsafe_allow_html=True,
        )

    comp_count = len(ctx.get("competitors", {}).get("list", []))
    risk_count = len(ctx.get("risks", {}).get("all", []))
    scheme_count = len(ctx.get("investors", {}).get("govt_schemes", []))
    st.markdown(
        f'<div style="margin-top:0.5rem;font-size:0.75rem;color:#475569;line-height:1.9">'
        f'🏆 {comp_count} competitors mapped<br>'
        f'⚠️ {risk_count} risks identified<br>'
        f'🏛️ {scheme_count} govt schemes found'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Starter questions
    st.markdown(
        '<div style="font-size:0.68rem;font-weight:700;color:#475569;text-transform:uppercase;'
        'letter-spacing:0.1em;margin-bottom:0.6rem">💡 Ask Me About</div>',
        unsafe_allow_html=True,
    )
    for q in _STARTER_QUESTIONS[:10]:
        if st.button(q, key=f"sq_{hash(q)}", use_container_width=True):
            st.session_state.mentor_pending_input = q
            st.rerun()

    # Session stats
    msg_count = len(st.session_state.get("mentor_messages_ui", []))
    if msg_count > 0:
        turns = msg_count // 2
        st.markdown(
            f'<div style="margin-top:1rem;font-size:0.73rem;color:#475569;'
            f'border-top:1px solid rgba(255,255,255,0.05);padding-top:0.75rem">'
            f'💬 {turns} conversation turn{"s" if turns!=1 else ""} this session</div>',
            unsafe_allow_html=True,
        )

    # Clear chat button
    if msg_count > 0:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        if st.button("🗑 Clear Chat", key="mentor_clear", use_container_width=True):
            st.session_state.mentor_messages_ui = []
            # Reset session but keep ctx
            old_ctx = st.session_state.mentor_session.ctx
            st.session_state.mentor_session = create_session(old_ctx)
            st.rerun()


# ── Chat area ──────────────────────────────────────────────────────────────────

def _render_chat_area(
    *, session, blueprint_id, user_email,
    groq_client, granite_client, embedder, collection, tavily_client,
) -> None:

    messages_ui = st.session_state.mentor_messages_ui

    # ── Welcome screen ────────────────────────────────────────────────────────
    if not messages_ui:
        _render_welcome_screen()

    # ── Chat messages ─────────────────────────────────────────────────────────
    for msg in messages_ui:
        _render_message(msg)

    # ── Input area ────────────────────────────────────────────────────────────
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # Check for pending input from sidebar quick-questions
    pending = st.session_state.get("mentor_pending_input", "")

    inp_col, btn_col = st.columns([9, 1])
    with inp_col:
        question = st.text_input(
            "",
            value=pending,
            placeholder="Ask anything about your startup… e.g. 'Is this idea saturated?' or 'Give me a 3-month roadmap'",
            key=f"mentor_input_{st.session_state.mentor_input_key}",
            label_visibility="collapsed",
        )
    with btn_col:
        send = st.button("Send →", key="mentor_send", type="primary", use_container_width=True)

    # Also send on Enter (submit via pending)
    if pending and not send:
        question = pending
        send     = True

    if send and question.strip():
        # Clear pending and bump input key
        st.session_state.mentor_pending_input = ""
        st.session_state.mentor_input_key    += 1

        # Add user bubble immediately
        st.session_state.mentor_messages_ui.append({
            "role":       "user",
            "content":    question,
            "intent":     "",
            "citations":  [],
            "tools_used": [],
        })
        st.rerun()

    # ── Process last user message if not yet responded ────────────────────────
    if (
        messages_ui
        and messages_ui[-1]["role"] == "user"
        and not st.session_state.get("_mentor_processing", False)
    ):
        last_question = messages_ui[-1]["content"]
        with st.status("🧠 Mentor thinking…", expanded=True) as status:
            st.write("🎯 Classifying your question…")
            st.write("🔍 Retrieving grounded evidence…")
            st.write("✍️ IBM Granite 4.0 synthesizing answer…")

            st.session_state._mentor_processing = True
            try:
                result = mentor_ask(
                    session=session,
                    question=last_question,
                    groq_client=groq_client,
                    granite_client=granite_client,
                    embedder=embedder,
                    collection=collection,
                    tavily_client=tavily_client,
                    blueprint_id=blueprint_id,
                    user_email=user_email,
                )
                status.update(
                    label=f"✅ Answer ready — Intent: {result['intent']}",
                    state="complete",
                )
                st.session_state.mentor_messages_ui.append({
                    "role":       "assistant",
                    "content":    result["answer"],
                    "intent":     result["intent"],
                    "citations":  result["citations"],
                    "tools_used": result["tools_used"],
                })
            except Exception as e:
                status.update(label="⚠️ Error generating answer", state="error")
                st.session_state.mentor_messages_ui.append({
                    "role":       "assistant",
                    "content":    f"I encountered an error: {str(e)[:300]}. Please try again.",
                    "intent":     "GENERAL",
                    "citations":  [],
                    "tools_used": [],
                })
            finally:
                st.session_state._mentor_processing = False

        st.rerun()


# ── Welcome screen ─────────────────────────────────────────────────────────────

def _render_welcome_screen() -> None:
    st.markdown("""
<div style="text-align:center;padding:2rem 1rem 1.5rem">
  <div style="font-size:3rem;margin-bottom:0.75rem">🧠</div>
  <div style="font-size:1.2rem;font-weight:800;color:#f1f5f9;letter-spacing:-0.025em;margin-bottom:0.5rem">
    Your AI Startup Mentor is Ready
  </div>
  <div style="font-size:0.85rem;color:#475569;max-width:460px;margin:0 auto;line-height:1.65">
    I've studied your entire blueprint. Ask me anything — market validation, 
    funding, competitors, legal, execution roadmap, investor prep, and more.
    Every answer is grounded in your data and cited from real sources.
  </div>
</div>
""", unsafe_allow_html=True)

    # Quick-action grid
    st.markdown(
        '<div style="font-size:0.72rem;font-weight:700;color:#475569;text-transform:uppercase;'
        'letter-spacing:0.1em;margin-bottom:0.75rem;text-align:center">Popular Questions</div>',
        unsafe_allow_html=True,
    )
    grid_questions = _STARTER_QUESTIONS[:6]
    g_cols = st.columns(3)
    for i, q in enumerate(grid_questions):
        with g_cols[i % 3]:
            icon, color, _ = _INTENT_META.get(
                _quick_intent_guess(q), ("💬", "#94a3b8", "")
            )
            if st.button(
                f"{icon} {q}",
                key=f"wq_{i}",
                use_container_width=True,
            ):
                st.session_state.mentor_pending_input = q
                st.rerun()

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)


def _quick_intent_guess(q: str) -> str:
    q_lower = q.lower()
    if any(w in q_lower for w in ["feasib", "market", "saturated", "tam", "som"]): return "MARKET_VALIDATION"
    if any(w in q_lower for w in ["fund", "raise", "investor", "seed"]): return "FUNDING"
    if any(w in q_lower for w in ["competitor", "rival", "strongest"]): return "COMPETITOR"
    if any(w in q_lower for w in ["scheme", "government", "dpiit", "msme"]): return "GOVT_SCHEMES"
    if any(w in q_lower for w in ["roadmap", "month", "execute", "plan"]): return "EXECUTION_ROADMAP"
    if any(w in q_lower for w in ["risk", "pivot", "challenge"]): return "RISK_ANALYSIS"
    if any(w in q_lower for w in ["investor", "ycombinator", "y combinator", "pitch"]): return "INVESTOR_PREP"
    if any(w in q_lower for w in ["mvp", "build", "product"]): return "PRODUCT_DEVELOPMENT"
    if any(w in q_lower for w in ["burn", "revenue", "pricing", "financial"]): return "FINANCIAL"
    return "GENERAL"


# ── Message renderer ───────────────────────────────────────────────────────────

def _render_message(msg: dict) -> None:
    role       = msg["role"]
    content    = msg["content"]
    intent     = msg.get("intent", "")
    citations  = msg.get("citations", [])
    tools_used = msg.get("tools_used", [])

    if role == "user":
        st.markdown(f"""
<div style="display:flex;justify-content:flex-end;margin-bottom:0.8rem">
  <div style="background:linear-gradient(135deg,rgba(15,98,254,0.14),rgba(105,41,196,0.1));
  border:1px solid rgba(15,98,254,0.22);border-radius:18px 18px 4px 18px;
  padding:0.9rem 1.2rem;max-width:75%;font-size:0.88rem;color:#e2e8f0;line-height:1.65">
    {content}
  </div>
</div>
""", unsafe_allow_html=True)
        return

    # Assistant message
    # Intent badge
    badge_html = ""
    if intent:
        icon, color, label = _INTENT_META.get(intent, ("💬", "#94a3b8", intent))
        badge_html = (
            f'<span style="background:{color}18;border:1px solid {color}44;color:{color};'
            f'padding:2px 10px;border-radius:12px;font-size:0.68rem;font-weight:700;'
            f'margin-right:6px">{icon} {label}</span>'
        )

    # Tool badges
    tool_badges = ""
    tool_icons = {"blueprint": "📋 Blueprint", "chromadb": "📄 PDF Docs", "tavily": "🌐 Live Web"}
    for t in tools_used:
        if t in tool_icons:
            tool_badges += (
                f'<span style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);'
                f'color:#64748b;padding:2px 9px;border-radius:10px;font-size:0.65rem;margin-right:4px">'
                f'{tool_icons[t]}</span>'
            )

    header_html = ""
    if badge_html or tool_badges:
        header_html = f'<div style="margin-bottom:0.65rem">{badge_html}{tool_badges}</div>'

    # Citations
    citations_html = ""
    if citations:
        cite_items = "".join(
            f'<div style="font-size:0.72rem;color:#475569;padding:2px 0;line-height:1.5">{c}</div>'
            for c in citations[:8]
        )
        citations_html = f"""
<details style="margin-top:0.75rem">
  <summary style="font-size:0.72rem;color:#475569;cursor:pointer;font-weight:600;
  list-style:none;padding:4px 0">
    📎 {len(citations)} source{"s" if len(citations)!=1 else ""} cited
  </summary>
  <div style="margin-top:0.4rem;padding:0.6rem;background:rgba(255,255,255,0.025);
  border-radius:10px;border:1px solid rgba(255,255,255,0.05)">
    {cite_items}
  </div>
</details>
"""

    st.markdown(f"""
<div style="display:flex;gap:0.75rem;margin-bottom:1rem;align-items:flex-start">
  <div style="font-size:1.5rem;flex-shrink:0;margin-top:2px">🧠</div>
  <div style="flex:1;background:rgba(255,255,255,0.022);border:1px solid rgba(255,255,255,0.06);
  border-radius:4px 18px 18px 18px;padding:1rem 1.25rem">
    {header_html}
    <div style="font-size:0.87rem;color:#cbd5e1;line-height:1.8;white-space:pre-wrap">{content}</div>
    {citations_html}
  </div>
</div>
""", unsafe_allow_html=True)
