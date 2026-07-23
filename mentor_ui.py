"""
mentor_ui.py — AI Startup Mentor UI
Voice input (Web Speech API) + PDF/DOCX upload + structured response cards
"""

from __future__ import annotations
import streamlit as st
import uuid
import re

from mentor.context      import build_mentor_context
from mentor.mentor_agent import ask as mentor_ask, create_session


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
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

_ACCENT_MAP = {
    "MARKET_VALIDATION":   "r-blue",
    "FUNDING":             "r-green",
    "LEGAL":               "r-amber",
    "TECHNOLOGY":          "r-indigo",
    "COMPETITOR":          "r-red",
    "MARKETING":           "r-pink",
    "GTM":                 "r-sky",
    "FINANCIAL":           "r-green",
    "HIRING":              "r-purple",
    "PRODUCT_DEVELOPMENT": "r-orange",
    "GOVT_SCHEMES":        "r-blue",
    "RISK_ANALYSIS":       "r-red",
    "INVESTOR_PREP":       "r-purple",
    "EXECUTION_ROADMAP":   "r-green",
    "GENERAL":             "r-slate",
}

_STARTER_QUESTIONS = [
    ("📊", "Is this startup actually feasible?",            "MARKET_VALIDATION"),
    ("🏆", "What competitors are strongest?",               "COMPETITOR"),
    ("🏛️", "Which government schemes should I apply for?",  "GOVT_SCHEMES"),
    ("🗺️", "Give me a 6-month execution roadmap.",          "EXECUTION_ROADMAP"),
    ("💰", "How should I raise my first funding?",          "FUNDING"),
    ("⚠️", "What risks am I missing?",                     "RISK_ANALYSIS"),
    ("🤝", "How would Y Combinator evaluate this idea?",    "INVESTOR_PREP"),
    ("🛠️", "Suggest an MVP I can build in 30 days.",        "PRODUCT_DEVELOPMENT"),
    ("📈", "Estimate my TAM SAM SOM.",                      "MARKET_VALIDATION"),
    ("💬", "Generate investor questions for my pitch.",     "INVESTOR_PREP"),
    ("📉", "How can I reduce burn rate?",                   "FINANCIAL"),
    ("🚀", "What should I build first?",                    "PRODUCT_DEVELOPMENT"),
]


# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════
_CSS = """
<style>
/* ── Page chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1rem 1.5rem 2rem !important; max-width: 1400px !important; }
section[data-testid="stSidebar"] { display: none; }

/* ── Nav ── */
.m-nav {
  display:flex; align-items:center; justify-content:space-between;
  padding:0.6rem 0 1rem; border-bottom:1px solid rgba(255,255,255,0.07);
  margin-bottom:1.2rem; flex-wrap:wrap; gap:8px;
}
.m-nav-left { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.m-nav-logo { font-size:1rem; font-weight:700; color:#f1f5f9; }
.m-badge { font-size:0.67rem; font-weight:700; padding:3px 10px; border-radius:20px; display:inline-block; white-space:nowrap; }
.mb-ibm  { background:rgba(15,98,254,.13);  border:0.5px solid rgba(15,98,254,.3);  color:#60a5fa; }
.mb-groq { background:rgba(105,41,196,.13); border:0.5px solid rgba(105,41,196,.3); color:#a78bfa; }
.mb-rag  { background:rgba(16,185,129,.1);  border:0.5px solid rgba(16,185,129,.25);color:#34d399; }

/* ── Context banner ── */
.ctx-banner {
  background:rgba(255,255,255,0.02); border:0.5px solid rgba(255,255,255,0.07);
  border-radius:12px; padding:0.85rem 1.2rem; margin-bottom:1.1rem;
  display:flex; align-items:flex-start; gap:1rem; flex-wrap:wrap;
}
.ctx-idea {
  font-size:0.82rem; color:#94a3b8; line-height:1.5;
  border-left:3px solid rgba(15,98,254,0.4); padding-left:0.75rem;
  flex:1; min-width:220px;
}
.ctx-chips { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
.ctx-chip {
  font-size:0.69rem; font-weight:600; padding:3px 10px; border-radius:20px;
  background:rgba(255,255,255,0.04); border:0.5px solid rgba(255,255,255,0.08);
  color:#94a3b8; white-space:nowrap;
}

/* ── Stats row ── */
.stats-row { display:flex; gap:10px; margin-bottom:1.1rem; flex-wrap:wrap; }
.stat-card {
  background:rgba(255,255,255,0.025); border:0.5px solid rgba(255,255,255,0.07);
  border-radius:10px; padding:0.7rem 1rem; flex:1; min-width:100px;
  display:flex; align-items:center; gap:10px;
}
.stat-icon { font-size:1.15rem; flex-shrink:0; }
.stat-val  { font-size:1.05rem; font-weight:700; color:#f1f5f9; line-height:1; }
.stat-lbl  { font-size:0.63rem; color:#475569; margin-top:2px; text-transform:uppercase; letter-spacing:0.06em; }

/* ── Sidebar doc upload section ── */
.doc-section-label {
  font-size:0.67rem; font-weight:700; color:#475569;
  text-transform:uppercase; letter-spacing:0.1em; margin-bottom:8px;
}
.doc-status-card {
  background:rgba(52,211,153,0.05); border:0.5px solid rgba(52,211,153,0.2);
  border-radius:10px; padding:8px 12px; margin-top:6px;
}
.doc-status-name {
  font-size:0.75rem; font-weight:600; color:#f1f5f9;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  max-width:180px; margin-bottom:4px;
}
.doc-status-meta { font-size:0.68rem; color:#475569; margin-bottom:5px; }
.doc-hint { font-size:0.67rem; color:#334155; margin-top:6px; line-height:1.5; }

/* ── Streamlit widget overrides ── */
button[data-testid="stBaseButton-secondary"] {
  background:rgba(255,255,255,0.025) !important;
  border:0.5px solid rgba(255,255,255,0.07) !important;
  border-radius:10px !important; color:#94a3b8 !important;
  font-size:0.78rem !important; text-align:left !important;
  padding:8px 12px !important; line-height:1.4 !important;
  white-space:normal !important; height:auto !important;
  transition:all .15s ease !important;
}
button[data-testid="stBaseButton-secondary"]:hover {
  background:rgba(15,98,254,0.1) !important;
  border-color:rgba(15,98,254,0.3) !important; color:#93c5fd !important;
}
button[data-testid="stBaseButton-primary"] {
  border-radius:10px !important; font-weight:700 !important; font-size:0.85rem !important;
}
div[data-testid="stTextInput"] input {
  background:rgba(255,255,255,0.03) !important;
  border:0.5px solid rgba(255,255,255,0.1) !important;
  border-radius:10px !important; color:#e2e8f0 !important; font-size:0.87rem !important;
}
div[data-testid="stTextInput"] input:focus {
  border-color:rgba(15,98,254,0.5) !important;
  box-shadow:0 0 0 3px rgba(15,98,254,0.1) !important;
}
div[data-testid="stTextInput"] input::placeholder { color:#334155 !important; }
hr { border:none !important; height:0.5px !important; background:rgba(255,255,255,0.07) !important; margin:1rem 0 !important; }
.input-hint { font-size:0.67rem; color:#334155; margin-top:5px; display:flex; gap:1.5rem; }
.session-label { font-size:0.7rem; color:#475569; text-align:center; padding:4px 0; }

/* ── Voice input bar ── */
.voice-bar {
  display:flex; align-items:center; gap:10px;
  padding:8px 12px; margin-bottom:8px;
  background:rgba(255,255,255,0.02); border:0.5px solid rgba(255,255,255,0.07);
  border-radius:10px;
}
.voice-transcript {
  flex:1; font-size:0.82rem; color:#93c5fd;
  background:rgba(15,98,254,0.08); border:0.5px solid rgba(15,98,254,0.2);
  border-radius:8px; padding:5px 10px; display:none;
}
.voice-status { font-size:0.72rem; color:#475569; flex:1; }

/* ══════════════════════════════════════════════════
   RESPONSE CARD SYSTEM
   ══════════════════════════════════════════════════ */
.r-row  { display:flex; gap:12px; margin-bottom:1.5rem; align-items:flex-start; }
.r-avatar {
  width:36px; height:36px; border-radius:50%;
  background:linear-gradient(135deg,#1e3a5f,#4c1d95);
  border:0.5px solid rgba(99,102,241,0.4);
  display:flex; align-items:center; justify-content:center;
  font-size:1.05rem; flex-shrink:0; margin-top:2px;
}
.r-body { flex:1; min-width:0; }
.r-header { display:flex; align-items:center; gap:8px; margin-bottom:10px; flex-wrap:wrap; }
.r-intent { font-size:0.67rem; font-weight:700; padding:3px 11px; border-radius:20px; text-transform:uppercase; letter-spacing:0.06em; }
.r-tool   { font-size:0.65rem; padding:2px 8px; border-radius:8px; background:rgba(255,255,255,0.04); border:0.5px solid rgba(255,255,255,0.08); color:#64748b; }

/* Doc source pill */
.r-doc-pill {
  font-size:0.65rem; padding:2px 8px; border-radius:8px;
  background:rgba(52,211,153,0.08); border:0.5px solid rgba(52,211,153,0.25);
  color:#34d399;
}

/* Summary highlight */
.r-summary {
  background:linear-gradient(135deg,rgba(15,98,254,0.08),rgba(105,41,196,0.06));
  border:0.5px solid rgba(15,98,254,0.2); border-radius:12px;
  padding:0.85rem 1.1rem; margin-bottom:10px;
}
.r-summary-lbl { font-size:0.64rem; font-weight:700; color:#60a5fa; text-transform:uppercase; letter-spacing:0.09em; margin-bottom:5px; }
.r-summary-txt { font-size:0.87rem; color:#e2e8f0; line-height:1.75; }

/* Section card */
.r-card {
  background:rgba(255,255,255,0.022); border:0.5px solid rgba(255,255,255,0.07);
  border-radius:14px; padding:1rem 1.15rem; margin-bottom:10px;
  position:relative; overflow:hidden;
}
.r-card::before { content:''; position:absolute; left:0; top:0; bottom:0; width:3px; border-radius:3px 0 0 3px; }
.r-blue::before   { background:#3b82f6; }
.r-green::before  { background:#10b981; }
.r-amber::before  { background:#f59e0b; }
.r-indigo::before { background:#6366f1; }
.r-red::before    { background:#ef4444; }
.r-pink::before   { background:#ec4899; }
.r-sky::before    { background:#0ea5e9; }
.r-purple::before { background:#8b5cf6; }
.r-orange::before { background:#f97316; }
.r-slate::before  { background:#94a3b8; }

.r-sec-title {
  font-size:0.73rem; font-weight:700; color:#94a3b8;
  text-transform:uppercase; letter-spacing:0.08em;
  margin-bottom:0.7rem; padding-bottom:0.5rem;
  border-bottom:0.5px solid rgba(255,255,255,0.06);
}
.r-sub { font-size:0.83rem; font-weight:700; color:#f1f5f9; margin:0.7rem 0 0.3rem; }

.r-bullet { display:flex; gap:10px; padding:6px 0; border-bottom:0.5px solid rgba(255,255,255,0.04); align-items:flex-start; }
.r-bullet:last-child { border-bottom:none; padding-bottom:0; }
.r-bullet-dot  { color:#60a5fa; font-size:0.62rem; margin-top:5px; flex-shrink:0; }
.r-bullet-text { font-size:0.84rem; color:#cbd5e1; line-height:1.65; }

.r-num { display:flex; gap:12px; padding:7px 0; border-bottom:0.5px solid rgba(255,255,255,0.04); align-items:flex-start; }
.r-num:last-child { border-bottom:none; }
.r-num-badge {
  font-size:0.68rem; font-weight:800; color:#f1f5f9;
  background:rgba(99,102,241,0.18); border:0.5px solid rgba(99,102,241,0.3);
  border-radius:6px; padding:1px 7px; flex-shrink:0; margin-top:2px; line-height:1.6;
}
.r-num-text { font-size:0.84rem; color:#cbd5e1; line-height:1.65; }

.r-kv { display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:0.5px solid rgba(255,255,255,0.04); gap:12px; }
.r-kv:last-child { border-bottom:none; }
.r-kv-key { font-size:0.8rem; color:#94a3b8; flex:1; }
.r-kv-val { font-size:0.84rem; font-weight:600; color:#f1f5f9; text-align:right; }

.r-callout { border-radius:10px; padding:0.7rem 1rem; margin-bottom:8px; display:flex; gap:10px; align-items:flex-start; }
.r-callout-icon { font-size:1rem; flex-shrink:0; margin-top:1px; }
.r-callout-text { font-size:0.83rem; line-height:1.65; }
.r-call-risk    { background:rgba(248,113,113,0.07); border:0.5px solid rgba(248,113,113,0.2); }
.r-call-tip     { background:rgba(52,211,153,0.07);  border:0.5px solid rgba(52,211,153,0.2);  }
.r-call-warning { background:rgba(251,191,36,0.07);  border:0.5px solid rgba(251,191,36,0.2);  }
.r-call-risk    .r-callout-text { color:#fca5a5; }
.r-call-tip     .r-callout-text { color:#6ee7b7; }
.r-call-warning .r-callout-text { color:#fde68a; }

.r-prose { font-size:0.85rem; color:#cbd5e1; line-height:1.8; margin:0.3rem 0; }
.r-prose strong { color:#f1f5f9; font-weight:700; }
.r-prose em     { color:#94a3b8; font-style:italic; }
.r-prose code   { background:rgba(255,255,255,0.06); border:0.5px solid rgba(255,255,255,0.1); border-radius:4px; padding:1px 5px; font-size:0.79rem; font-family:monospace; }

.r-cite-wrap { margin-top:0.9rem; padding-top:0.7rem; border-top:0.5px solid rgba(255,255,255,0.06); }
.r-cite-toggle { font-size:0.7rem; color:#475569; font-weight:600; cursor:pointer; list-style:none; display:flex; align-items:center; gap:5px; padding:0; margin:0; }
.r-cite-toggle:hover { color:#94a3b8; }
.r-cite-item { margin-top:5px; font-size:0.71rem; color:#475569; background:rgba(255,255,255,0.02); border:0.5px solid rgba(255,255,255,0.05); border-radius:6px; padding:4px 9px; line-height:1.5; }

.r-user-row { display:flex; justify-content:flex-end; margin-bottom:1rem; }
.r-user-bubble {
  background:linear-gradient(135deg,rgba(15,98,254,0.18),rgba(105,41,196,0.12));
  border:0.5px solid rgba(15,98,254,0.28); border-radius:18px 18px 4px 18px;
  padding:0.75rem 1.1rem; max-width:76%;
  font-size:0.86rem; color:#e2e8f0; line-height:1.65;
}

/* Voice bubble tag on user message */
.r-voice-tag {
  font-size:0.62rem; color:#a78bfa; margin-top:4px; text-align:right;
}

.welcome-wrap  { text-align:center; padding:2rem 1rem 1.5rem; }
.welcome-icon  { font-size:3rem; margin-bottom:0.75rem; }
.welcome-title { font-size:1.2rem; font-weight:700; color:#f1f5f9; margin-bottom:0.4rem; }
.welcome-sub   { font-size:0.83rem; color:#475569; max-width:460px; margin:0 auto 1.5rem; line-height:1.7; }
.qs-label { font-size:0.66rem; font-weight:700; color:#475569; text-transform:uppercase; letter-spacing:0.1em; margin:1rem 0 0.7rem; }

.thinking-row { display:flex; gap:12px; align-items:center; margin-bottom:1rem; }
.thinking-bubble {
  background:rgba(255,255,255,0.025); border:0.5px solid rgba(255,255,255,0.07);
  border-radius:4px 14px 14px 14px; padding:0.65rem 1rem;
  font-size:0.8rem; color:#475569; display:flex; align-items:center; gap:8px;
}
.dot { width:6px; height:6px; border-radius:50%; background:#475569; display:inline-block; animation:blink 1.2s ease-in-out infinite; }
.dot:nth-child(2) { animation-delay:.2s; }
.dot:nth-child(3) { animation-delay:.4s; }
@keyframes blink { 0%,80%,100%{opacity:.3;transform:scale(.7)} 40%{opacity:1;transform:scale(1)} }

/* ── Mic button pulse ── */
@keyframes pulse-mic {
  0%   { box-shadow: 0 0 0 0   rgba(220,38,38,0.5); }
  70%  { box-shadow: 0 0 0 10px rgba(220,38,38,0);  }
  100% { box-shadow: 0 0 0 0   rgba(220,38,38,0);  }
}
</style>
"""

# ══════════════════════════════════════════════════════════════════════════════
#  VOICE INPUT HTML  (Web Speech API — free, browser-native)
# ══════════════════════════════════════════════════════════════════════════════
_VOICE_HTML = """
<div style="display:flex;align-items:center;gap:10px;
  padding:8px 12px;margin-bottom:8px;
  background:rgba(255,255,255,0.02);border:0.5px solid rgba(255,255,255,0.07);
  border-radius:10px;">

  <button id="mic-btn" onclick="toggleMic()" title="Click to speak"
    style="width:38px;height:38px;border-radius:50%;flex-shrink:0;
    background:linear-gradient(135deg,#1e3a5f,#4c1d95);
    border:0.5px solid rgba(99,102,241,0.5);
    color:white;font-size:1rem;cursor:pointer;
    display:flex;align-items:center;justify-content:center;
    transition:all .2s ease;">🎙️</button>

  <span id="voice-status" style="font-size:0.72rem;color:#475569;flex:1">
    Click 🎙️ to ask by voice
  </span>

  <div id="voice-result"
    style="display:none;font-size:0.8rem;color:#93c5fd;
    background:rgba(15,98,254,0.08);border:0.5px solid rgba(15,98,254,0.2);
    border-radius:8px;padding:4px 10px;max-width:360px;flex:2">
  </div>

  <button id="voice-use-btn" onclick="sendTranscript()"
    style="display:none;font-size:0.72rem;font-weight:700;
    padding:4px 12px;border-radius:8px;white-space:nowrap;
    background:rgba(15,98,254,0.15);border:0.5px solid rgba(15,98,254,0.3);
    color:#60a5fa;cursor:pointer;">Use this ✓</button>

</div>

<script>
(function(){
  if (window._voiceReady) return;
  window._voiceReady = true;

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    document.getElementById('voice-status').textContent = '⚠️ Voice not supported (use Chrome/Edge)';
    document.getElementById('mic-btn').disabled = true;
    return;
  }

  const rec = new SR();
  rec.continuous     = false;
  rec.interimResults = true;
  rec.lang           = 'en-IN';

  let listening = false;
  let finalText = '';

  const btn    = document.getElementById('mic-btn');
  const status = document.getElementById('voice-status');
  const result = document.getElementById('voice-result');
  const useBtn = document.getElementById('voice-use-btn');

  function setOn(on) {
    listening = on;
    if (on) {
      btn.style.background  = 'linear-gradient(135deg,#dc2626,#b91c1c)';
      btn.style.animation   = 'pulse-mic 1s infinite';
      btn.textContent       = '⏹';
      status.textContent    = '🔴 Listening…';
      status.style.color    = '#f87171';
    } else {
      btn.style.background  = 'linear-gradient(135deg,#1e3a5f,#4c1d95)';
      btn.style.animation   = '';
      btn.textContent       = '🎙️';
      status.style.color    = '#475569';
    }
  }

  window.toggleMic = function() {
    if (listening) { rec.stop(); return; }
    finalText = '';
    result.style.display = 'none';
    useBtn.style.display = 'none';
    rec.start();
    setOn(true);
  };

  rec.onresult = function(e) {
    let interim = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      e.results[i].isFinal ? (finalText += t) : (interim += t);
    }
    result.style.display = 'block';
    result.textContent   = finalText + interim;
  };

  rec.onend = function() {
    setOn(false);
    if (finalText.trim()) {
      status.textContent    = '✅ Click "Use this" to send';
      status.style.color    = '#34d399';
      result.style.display  = 'block';
      result.textContent    = finalText.trim();
      useBtn.style.display  = 'inline-block';
    } else {
      status.textContent = 'Nothing heard — try again';
    }
  };

  rec.onerror = function(e) {
    setOn(false);
    status.textContent = '⚠️ ' + e.error;
    status.style.color = '#f87171';
  };

  window.sendTranscript = function() {
    const txt = finalText.trim();
    if (!txt) return;
    // Find the Streamlit text input and fire React synthetic event
    const inputs = parent.document.querySelectorAll('input[type="text"]');
    let inp = null;
    for (const el of inputs) {
      if (el.placeholder && el.placeholder.toLowerCase().includes('ask')) { inp = el; break; }
    }
    if (!inp && inputs.length) inp = inputs[inputs.length - 1];
    if (inp) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
      setter.call(inp, txt);
      inp.dispatchEvent(new Event('input', { bubbles:true }));
      inp.dispatchEvent(new KeyboardEvent('keydown',
        { key:'Enter', code:'Enter', keyCode:13, bubbles:true }));
    }
    status.textContent   = '✅ Sent!';
    result.style.display = 'none';
    useBtn.style.display = 'none';
    finalText = '';
  };
})();
</script>
"""


# ══════════════════════════════════════════════════════════════════════════════
#  DOCUMENT UPLOAD HELPERS  (PyMuPDF + python-docx — free, local)
# ══════════════════════════════════════════════════════════════════════════════
def _extract_pdf(data: bytes) -> str:
    try:
        import fitz
        doc  = fitz.open(stream=data, filetype="pdf")
        text = "\n\n".join(p.get_text("text") for p in doc)
        doc.close()
        return text.strip()
    except ImportError:
        return "[PyMuPDF not installed — pip install PyMuPDF]"
    except Exception as e:
        return f"[PDF error: {e}]"


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document
        import io
        doc  = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()
    except ImportError:
        return "[python-docx not installed — pip install python-docx]"
    except Exception as e:
        return f"[DOCX error: {e}]"


def _extract_txt(data: bytes) -> str:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return data.decode(enc).strip()
        except Exception:
            continue
    return "[Could not decode file]"


def _chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    paras = re.split(r"\n{2,}", text)
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) < max_chars:
            cur += p + "\n\n"
        else:
            if cur.strip(): chunks.append(cur.strip())
            cur = p + "\n\n"
    if cur.strip(): chunks.append(cur.strip())
    return chunks


def get_uploaded_doc_context(max_chars: int = 2500) -> str:
    """Inject into Granite prompt. Call from synthesizer.py."""
    text = st.session_state.get("uploaded_doc_text", "")
    name = st.session_state.get("uploaded_doc_name", "uploaded document")
    if not text or text.startswith("["):
        return ""
    truncated = text[:max_chars] + ("…[truncated]" if len(text) > max_chars else "")
    return f"=== {name} ===\n{truncated}"


def _render_doc_upload_sidebar(embedder=None, collection=None) -> None:
    st.markdown(
        '<hr>'
        '<div class="doc-section-label">📎 Upload a Document</div>',
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "PDF, DOCX or TXT",
        type=["pdf", "docx", "txt"],
        key="mentor_doc_upload",
        label_visibility="collapsed",
        help="Upload pitch deck, report, or any doc — I'll answer questions from it.",
    )

    if uploaded is not None:
        data  = uploaded.read()
        fname = uploaded.name
        ext   = fname.rsplit(".", 1)[-1].lower()

        if st.session_state.get("uploaded_doc_name") != fname:
            with st.spinner(f"Reading {fname}…"):
                text = (
                    _extract_pdf(data)  if ext == "pdf"  else
                    _extract_docx(data) if ext == "docx" else
                    _extract_txt(data)
                )
            st.session_state.uploaded_doc_text     = text
            st.session_state.uploaded_doc_name     = fname
            st.session_state.uploaded_doc_ingested = False

            if embedder and collection and text and not text.startswith("["):
                try:
                    chunks = _chunk_text(text)
                    collection.upsert(
                        ids       = [f"upload__{fname}__{i}" for i in range(len(chunks))],
                        documents = chunks,
                        embeddings= [embedder.encode(c).tolist() for c in chunks],
                        metadatas = [{"source": fname, "chunk": i} for i in range(len(chunks))],
                    )
                    st.session_state.uploaded_doc_ingested = True
                except Exception:
                    pass

        doc_text   = st.session_state.get("uploaded_doc_text", "")
        word_count = len(doc_text.split()) if doc_text else 0
        ingested   = st.session_state.get("uploaded_doc_ingested", False)

        rag_badge = (
            '<span style="font-size:0.67rem;background:rgba(52,211,153,0.1);'
            'border:0.5px solid rgba(52,211,153,0.25);color:#34d399;'
            'padding:2px 7px;border-radius:8px">✓ RAG indexed</span>'
            if ingested else
            '<span style="font-size:0.67rem;background:rgba(251,191,36,0.1);'
            'border:0.5px solid rgba(251,191,36,0.25);color:#fbbf24;'
            'padding:2px 7px;border-radius:8px">📋 Context only</span>'
        )
        st.markdown(f"""
<div class="doc-status-card">
  <div class="doc-status-name" title="{fname}">📄 {fname}</div>
  <div class="doc-status-meta">{word_count:,} words extracted</div>
  {rag_badge}
</div>
""", unsafe_allow_html=True)

        if doc_text and not doc_text.startswith("["):
            if st.button("✕ Remove document", key="remove_doc", use_container_width=True):
                for k in ["uploaded_doc_text","uploaded_doc_name","uploaded_doc_ingested"]:
                    st.session_state.pop(k, None)
                st.rerun()

    elif st.session_state.get("uploaded_doc_name"):
        for k in ["uploaded_doc_text","uploaded_doc_name","uploaded_doc_ingested"]:
            st.session_state.pop(k, None)

    st.markdown(
        '<div class="doc-hint">PDF · DOCX · TXT supported.<br>'
        'Answers will draw from this doc + your blueprint.</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  MARKDOWN PARSER → structured blocks
# ══════════════════════════════════════════════════════════════════════════════
def _inline(text: str) -> str:
    text = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r'<strong>\1</strong>', text)
    text = re.sub(r"\*(.+?)\*",     r'<em>\1</em>', text)
    text = re.sub(r"`(.+?)`",
        r'<code style="background:rgba(255,255,255,0.06);border:0.5px solid'
        r' rgba(255,255,255,0.1);border-radius:4px;padding:1px 5px;'
        r'font-size:0.79rem;font-family:monospace">\1</code>', text)
    return text


def _parse(text: str) -> list[dict]:
    lines = text.strip().split("\n")
    # Normalize: strip excessive blank lines
    lines = [l for i, l in enumerate(lines)
             if l.strip() or (i > 0 and lines[i-1].strip())]
    blocks: list[dict] = []
    section: dict | None = None

    def flush():
        nonlocal section
        if section is not None:
            blocks.append(section)
            section = None

    CALLOUTS = [
        (("⚠️","❗","🚨","⛔"), "risk",    "⚠️"),
        (("✅","💡","🟢","🎯"), "tip",     "💡"),
        (("🔔","📌","⚡","ℹ️"), "warning", "📌"),
    ]

    for raw in lines:
        line = raw.rstrip()

        if re.match(r"^#{1,2}\s+", line):
            flush()
            section = {"type":"section","title":re.sub(r"^#{1,2}\s+","",line).strip(),"items":[]}
            continue

        if re.match(r"^#{3,6}\s+", line):
            txt = re.sub(r"^#{3,6}\s+", "", line).strip()
            b = {"type":"sub","text":_inline(txt)}
            (section["items"] if section else blocks).append(b); continue

        m = re.match(r"^[-*•]\s+(.*)", line)
        if m:
            b = {"type":"bullet","text":_inline(m.group(1).strip())}
            (section["items"] if section else blocks).append(b); continue

        m = re.match(r"^(\d+)[.)]\s+(.*)", line)
        if m:
            b = {"type":"num","num":int(m.group(1)),"text":_inline(m.group(2).strip())}
            (section["items"] if section else blocks).append(b); continue

        m = re.match(r"^\*{0,2}([^*\n]{2,44}?)\*{0,2}:\s+(.+)", line)
        if m and not line.startswith("#") and "://" not in line:
            b = {"type":"kv","key":m.group(1).strip(" *"),"val":_inline(m.group(2).strip())}
            (section["items"] if section else blocks).append(b); continue

        matched = False
        for triggers, variant, icon in CALLOUTS:
            if any(line.startswith(t) for t in triggers):
                body = line
                for t in triggers: body = body.lstrip(t).strip()
                b = {"type":"callout","variant":variant,"icon":icon,"text":_inline(body)}
                (section["items"] if section else blocks).append(b)
                matched = True; break
        if matched: continue

        if re.match(r"^-{3,}$|^={3,}$", line.strip()):
            flush(); continue

        if not line.strip(): continue

        b = {"type":"prose","text":_inline(line.strip())}
        (section["items"] if section else blocks).append(b)

    flush()
    return blocks


def _block_html(b: dict) -> str:
    t = b["type"]
    if t == "bullet":
        return (f'<div class="r-bullet"><span class="r-bullet-dot">▸</span>'
                f'<span class="r-bullet-text">{b["text"]}</span></div>')
    if t == "num":
        return (f'<div class="r-num"><span class="r-num-badge">{b["num"]}</span>'
                f'<span class="r-num-text">{b["text"]}</span></div>')
    if t == "kv":
        return (f'<div class="r-kv"><span class="r-kv-key">{b["key"]}</span>'
                f'<span class="r-kv-val">{b["val"]}</span></div>')
    if t == "prose":
        return f'<p class="r-prose">{b["text"]}</p>'
    if t == "sub":
        return f'<div class="r-sub">{b["text"]}</div>'
    if t == "callout":
        return (f'<div class="r-callout r-call-{b["variant"]}">'
                f'<span class="r-callout-icon">{b["icon"]}</span>'
                f'<span class="r-callout-text">{b["text"]}</span></div>')
    return ""


def _section_html(sec: dict, accent: str) -> str:
    title = f'<div class="r-sec-title">{_inline(sec["title"])}</div>' if sec["title"] else ""
    body  = "\n".join(_block_html(b) for b in sec["items"])
    return f'<div class="r-card {accent}">{title}{body}</div>'


def _blocks_to_html(blocks: list[dict], accent: str) -> str:
    html = ""
    i    = 0
    GROUP = {"bullet","num","kv","sub","callout","prose"}

    # First prose → summary highlight box
    if blocks and blocks[0]["type"] == "prose":
        html += (f'<div class="r-summary">'
                 f'<div class="r-summary-lbl">📋 Summary</div>'
                 f'<div class="r-summary-txt">{blocks[0]["text"]}</div></div>')
        i = 1

    while i < len(blocks):
        b = blocks[i]
        if b["type"] == "section":
            html += _section_html(b, accent); i += 1; continue
        if b["type"] in GROUP:
            inner = ""
            while i < len(blocks) and blocks[i]["type"] in GROUP:
                inner += _block_html(blocks[i]); i += 1
            html += f'<div class="r-card {accent}">{inner}</div>'
            continue
        html += _block_html(b); i += 1

    return html


# ══════════════════════════════════════════════════════════════════════════════
#  MESSAGE RENDERER
# ══════════════════════════════════════════════════════════════════════════════
def _render_message(msg: dict) -> None:
    role       = msg["role"]
    content    = msg["content"]
    intent     = msg.get("intent") or "GENERAL"
    citations  = msg.get("citations") or []
    tools_used = msg.get("tools_used") or []
    via_voice  = msg.get("via_voice", False)
    from_doc   = msg.get("from_doc", False)

    if role == "user":
        safe = content.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        voice_tag = '<div class="r-voice-tag">🎙️ via voice</div>' if via_voice else ""
        st.markdown(
            f'<div class="r-user-row"><div>'
            f'<div class="r-user-bubble">{safe}</div>'
            f'{voice_tag}</div></div>',
            unsafe_allow_html=True)
        return

    icon, color, label = _INTENT_META.get(intent, ("💬","#94a3b8","General"))
    badge = (f'<span class="r-intent" '
             f'style="background:{color}18;border:0.5px solid {color}44;color:{color}">'
             f'{icon} {label}</span>')

    tmap = {"blueprint":"📋 Blueprint","chromadb":"📄 PDF Docs","tavily":"🌐 Web Research"}
    tools_html = " ".join(
        f'<span class="r-tool">{tmap.get(t,t)}</span>'
        for t in tools_used if t in tmap
    )
    doc_pill = '<span class="r-doc-pill">📎 Uploaded doc</span>' if from_doc else ""
    header   = f'<div class="r-header">{badge}{tools_html}{doc_pill}</div>'

    accent = _ACCENT_MAP.get(intent, "r-slate")
    body   = _blocks_to_html(_parse(content), accent)

    cite_html = ""
    if citations:
        items = "".join(f'<div class="r-cite-item">📎 {c}</div>' for c in citations[:8])
        n = len(citations)
        cite_html = (
            f'<div class="r-cite-wrap"><details>'
            f'<summary class="r-cite-toggle">'
            f'📎 {n} source{"s" if n!=1 else ""} cited — click to expand'
            f'</summary><div style="margin-top:4px">{items}</div>'
            f'</details></div>'
        )

    st.markdown(f"""
<div class="r-row">
  <div class="r-avatar">🧠</div>
  <div class="r-body">
    {header}{body}{cite_html}
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  STATE
# ══════════════════════════════════════════════════════════════════════════════
def _init_state(blueprint_id: int | None, user_email: str) -> None:
    defaults = {
        "mentor_session":       None,
        "mentor_session_id":    None,
        "mentor_messages_ui":   [],
        "mentor_input_key":     0,
        "mentor_pending_input": "",
        "_mentor_processing":   False,
        "uploaded_doc_text":    "",
        "uploaded_doc_name":    "",
        "uploaded_doc_ingested":False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
            
    # --- NEW DB LOADING LOGIC ---
    if blueprint_id is not None:
        session_key = f"mentor_messages_{blueprint_id}"
        if session_key not in st.session_state:
            from mentor.mentor_db import load_bp_messages
            st.session_state[session_key] = load_bp_messages(blueprint_id, user_email)
        st.session_state.mentor_messages_ui = st.session_state[session_key]


def _get_or_create_session(ctx: dict):
    if st.session_state.mentor_session is None:
        sid = str(uuid.uuid4())
        st.session_state.mentor_session_id = sid
        st.session_state.mentor_session    = create_session(ctx, session_id=sid)
    return st.session_state.mentor_session


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY
# ══════════════════════════════════════════════════════════════════════════════
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
    _init_state(blueprint_id, user_email)
    st.markdown(_CSS, unsafe_allow_html=True)

    if st.session_state.mentor_session is None:
        ctx = build_mentor_context(
            idea=idea, sector=sector, stage=stage,
            business_model=business_model, market=market,
            crag_result=crag_result, bmc_data=bmc_data,
            budget_data=budget_data, gtm_data=gtm_data,
            investor_data=investor_data, competitor_data=competitor_data,
            risk_data=risk_data,
        )
        _get_or_create_session(ctx)

    session = st.session_state.mentor_session
    ctx     = session.ctx

    _render_nav()
    _render_context_banner(ctx)
    _render_stats(ctx)
    st.markdown('<hr>', unsafe_allow_html=True)

    chat_col, side_col = st.columns([68, 32], gap="large")
    with side_col:
        _render_sidebar(ctx, embedder=embedder, collection=collection)
    with chat_col:
        _render_chat(
            session=session, blueprint_id=blueprint_id, user_email=user_email,
            groq_client=groq_client, granite_client=granite_client,
            embedder=embedder, collection=collection, tavily_client=tavily_client,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  NAV
# ══════════════════════════════════════════════════════════════════════════════
def _render_nav() -> None:
    st.markdown("""
<div class="m-nav">
  <div class="m-nav-left">
    <span style="font-size:1.3rem">🧠</span>
    <span class="m-nav-logo">AI Startup Mentor</span>
    <span class="m-badge mb-ibm">IBM Granite 4.0</span>
    <span class="m-badge mb-groq">Groq Intent Engine</span>
    <span class="m-badge mb-rag">RAG Grounded</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # Adjust the column widths to fit the new button
    _, nc2, nc3, nc4 = st.columns([5, 1, 1, 1])
    
    with nc2:
        if st.button("← Blueprint", key="m_back", type="primary", use_container_width=True):
            st.session_state.page = "dashboard"
            st.session_state.hist_mentor_id = None # Clear mentor state
            st.rerun()
            
    with nc3:
        # --- NEW BACK TO HISTORY BUTTON ---
        if st.button("← History", key="m_back_hist", type="secondary", use_container_width=True):
            st.session_state.hist_mentor_id = None
            st.session_state.hist_open = True
            st.rerun()
            
    with nc4:
        if st.button("Sign out", key="m_signout", use_container_width=True):
            for k in ["logged_in","user","page","blueprints"]:
                st.session_state[k] = {"logged_in":False,"user":None,"page":"login","blueprints":[]}[k]
            st.session_state.mentor_session     = None
            st.session_state.mentor_messages_ui = []
            st.session_state.hist_mentor_id = None # Clear mentor state
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  CONTEXT BANNER + STATS
# ══════════════════════════════════════════════════════════════════════════════
def _render_context_banner(ctx: dict) -> None:
    idea  = ctx.get("idea","")
    short = idea[:110] + ("…" if len(idea)>110 else "")
    chips = "".join(
        f'<span class="ctx-chip">{v}</span>'
        for v in [ctx.get("sector",""), ctx.get("stage",""),
                  ctx.get("business_model",""), ctx.get("market","")]
        if v
    )
    st.markdown(f"""
<div class="ctx-banner">
  <div class="ctx-idea">
    <div style="font-size:0.65rem;font-weight:700;color:#3b82f6;
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px">
    📋 Blueprint loaded — I've read everything</div>
    {short}
  </div>
  <div class="ctx-chips">{chips}</div>
</div>
""", unsafe_allow_html=True)


def _render_stats(ctx: dict) -> None:
    budget       = ctx.get("budget", {}).get("total_12_months", 0)
    comp_count   = len(ctx.get("competitors", {}).get("list", []))
    risk_count   = len(ctx.get("risks", {}).get("all", []))
    scheme_count = len(ctx.get("investors", {}).get("govt_schemes", []))
    mkt_size     = ctx.get("gtm", {}).get("market_size", "—")

    stats = [
        ("📊", mkt_size,                              "Market size"),
        ("💰", f"₹{budget:,.0f}" if budget else "—",  "12-month budget"),
        ("🏆", str(comp_count),                       "Competitors"),
        ("⚠️",  str(risk_count),                       "Risks"),
        ("🏛️",  str(scheme_count),                     "Govt schemes"),
    ]
    html = "".join(
        f'<div class="stat-card">'
        f'<div class="stat-icon">{ic}</div>'
        f'<div><div class="stat-val">{val}</div><div class="stat-lbl">{lbl}</div></div>'
        f'</div>'
        for ic, val, lbl in stats
    )
    st.markdown(f'<div class="stats-row">{html}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def _render_sidebar(ctx: dict, embedder=None, collection=None) -> None:
    st.markdown(
        '<div class="doc-section-label" style="margin-bottom:0.75rem">💡 Ask Me About</div>',
        unsafe_allow_html=True,
    )
    for icon, q, _ in _STARTER_QUESTIONS:
        if st.button(f"{icon}  {q}", key=f"sq_{hash(q)}", use_container_width=True):
            st.session_state.mentor_pending_input = q
            st.rerun()

    turns = len(st.session_state.get("mentor_messages_ui",[])) // 2
    if turns > 0:
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="session-label">💬 {turns} turn{"s" if turns!=1 else ""} this session</div>',
            unsafe_allow_html=True,
        )
        if st.button("🗑 Clear chat", key="m_clear", use_container_width=True):
            st.session_state.mentor_messages_ui = []
            st.session_state.mentor_session = create_session(st.session_state.mentor_session.ctx)
            st.rerun()

    # Document upload section
    _render_doc_upload_sidebar(embedder=embedder, collection=collection)


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT AREA
# ══════════════════════════════════════════════════════════════════════════════
def _render_chat(
    *, session, blueprint_id, user_email,
    groq_client, granite_client, embedder, collection, tavily_client,
) -> None:
    
    msgs = st.session_state.mentor_messages_ui

    if not msgs:
        _render_welcome()
    else:
        for msg in msgs:
            _render_message(msg)

    # ── Voice input bar ───────────────────────────────────────────────────────
    st.components.v1.html(_VOICE_HTML, height=62, scrolling=False)

    # ── Text input + send ─────────────────────────────────────────────────────
    pending = st.session_state.get("mentor_pending_input","")
    ic1, ic2 = st.columns([9,1])
    with ic1:
        question = st.text_input(
            "", value=pending,
            placeholder="Ask anything — 'Is this idea saturated?' or 'Give me a 6-month roadmap'",
            key=f"m_input_{st.session_state.mentor_input_key}",
            label_visibility="collapsed",
        )
    with ic2:
        send = st.button("Send →", key="m_send", type="primary", use_container_width=True)

    st.markdown(
        '<div class="input-hint">'
        '<span>⌨️ Type or use 🎙️ voice above</span>'
        '<span>✦ IBM Granite 4.0 · Evidence-grounded</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    if pending and not send:
        question, send = pending, True

    if send and question.strip():
        st.session_state.mentor_pending_input = ""
        st.session_state.mentor_input_key    += 1
        st.session_state.mentor_messages_ui.append({
            "role":"user","content":question,
            "intent":"","citations":[],"tools_used":[],
            "via_voice": False,   # JS-triggered voice sets this via pending
        })
        
        # --- NEW SAVE LOGIC ---
        if blueprint_id is not None:
            from mentor.mentor_db import save_bp_message
            save_bp_message(
                blueprint_id=blueprint_id, 
                user_email=user_email, 
                role="user", 
                content=question
            )
            
        st.rerun()

    # ── Process last unanswered user message ──────────────────────────────────
    if (msgs and msgs[-1]["role"]=="user"
            and not st.session_state.get("_mentor_processing",False)):
        _process(
            session=session, question=msgs[-1]["content"],
            blueprint_id=blueprint_id, user_email=user_email,
            groq_client=groq_client, granite_client=granite_client,
            embedder=embedder, collection=collection, tavily_client=tavily_client,
        )


def _process(*, session, question, blueprint_id, user_email,
             groq_client, granite_client, embedder, collection, tavily_client) -> None:

    # Inject uploaded doc context into question if doc is loaded but not RAG-indexed
    has_doc  = bool(st.session_state.get("uploaded_doc_text",""))
    ingested = st.session_state.get("uploaded_doc_ingested", False)
    doc_ctx  = get_uploaded_doc_context() if has_doc and not ingested else ""

    augmented_question = question
    if doc_ctx:
        augmented_question = f"{question}\n\n[CONTEXT FROM UPLOADED DOCUMENT]\n{doc_ctx}"

    st.markdown("""
<div class="thinking-row">
  <div class="r-avatar" style="margin-top:0">🧠</div>
  <div class="thinking-bubble">
    <span class="dot"></span><span class="dot"></span><span class="dot"></span>
    Mentor is thinking…
  </div>
</div>
""", unsafe_allow_html=True)

    st.session_state._mentor_processing = True
    try:
        with st.spinner(""):
            result = mentor_ask(
                session=session, question=augmented_question,
                groq_client=groq_client, granite_client=granite_client,
                embedder=embedder, collection=collection,
                tavily_client=tavily_client,
                blueprint_id=blueprint_id, user_email=user_email,
            )
        st.session_state.mentor_messages_ui.append({
            "role":       "assistant",
            "content":    result["answer"],
            "intent":     result["intent"],
            "citations":  result["citations"],
            "tools_used": result["tools_used"],
            "from_doc":   bool(doc_ctx),
        })
        
        # --- NEW SAVE LOGIC ---
        if blueprint_id is not None:
            from mentor.mentor_db import save_bp_message
            save_bp_message(
                blueprint_id=blueprint_id,
                user_email=user_email,
                role="assistant",
                content=result["answer"],
                intent=result.get("intent", ""),
                citations=result.get("citations", []),
                tools_used=result.get("tools_used", [])
            )
            
    except Exception as e:
        st.session_state.mentor_messages_ui.append({
            "role":"assistant",
            "content":f"Something went wrong: {str(e)[:300]}. Please try again.",
            "intent":"GENERAL","citations":[],"tools_used":[],"from_doc":False,
        })
    finally:
        st.session_state._mentor_processing = False
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  WELCOME SCREEN
# ══════════════════════════════════════════════════════════════════════════════
def _render_welcome() -> None:
    st.markdown("""
<div class="welcome-wrap">
  <div class="welcome-icon">🧠</div>
  <div class="welcome-title">Your AI Startup Mentor is ready</div>
  <div class="welcome-sub">
    I've studied your entire blueprint — every section, every number, every scheme.
    Ask by typing or use the 🎙️ voice button. Every answer is evidence-backed.
  </div>
  <div class="qs-label">Popular questions to start with</div>
</div>
""", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    for i, (icon, q, _) in enumerate(_STARTER_QUESTIONS[:6]):
        with (c1 if i % 2 == 0 else c2):
            if st.button(f"{icon}  {q}", key=f"wq_{i}", use_container_width=True):
                st.session_state.mentor_pending_input = q
                st.rerun()