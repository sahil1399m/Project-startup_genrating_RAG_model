import os

# Must be before ALL other imports
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/st_cache"
import streamlit as st
st.set_page_config(
    page_title="Startup Blueprint Generator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)
try:
    hf = st.secrets.get("HF_TOKEN", "") or os.getenv("HF_TOKEN", "")
except Exception:
    hf = os.getenv("HF_TOKEN", "")
if hf:
    os.environ["HF_TOKEN"] = hf
    os.environ["HUGGINGFACE_HUB_TOKEN"] = hf

if not os.path.exists("chroma_db"):
    import subprocess
    subprocess.run(["python", "data_ingestion.py"])

from auth import show_auth_ui, is_authenticated, logout, increment_blueprint_count, get_blueprint_count
import requests
import jwt
from urllib.parse import urlencode
from dotenv import load_dotenv
load_dotenv()
import json
from datetime import datetime
from sentence_transformers import CrossEncoder
import chromadb
from ibm_watsonx_ai.foundation_models import ModelInference
from groq import Groq
from tavily import TavilyClient
import plotly.graph_objects as go
import google.generativeai as genai
from news_feed import get_startup_news
from crag import run_crag
import history as hist
from history_ui import render_history_page, render_history_view
from mentor_ui import render_mentor_page

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM — Professional Dark Theme
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;0,14..32,800;0,14..32,900;1,14..32,400&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }

/* ── App Background — deep navy with subtle radial glow ── */
.stApp {
    background: #04040f;
    color: #e2e8f0;
    min-height: 100vh;
}
.stApp::before {
    content: '';
    position: fixed;
    top: -20%;
    left: -10%;
    width: 60%;
    height: 60%;
    background: radial-gradient(ellipse, rgba(15,98,254,0.07) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}
.stApp::after {
    content: '';
    position: fixed;
    bottom: -20%;
    right: -10%;
    width: 55%;
    height: 55%;
    background: radial-gradient(ellipse, rgba(105,41,196,0.06) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}

/* ── Layout ── */
.main .block-container {
    padding: 0 2rem 4rem;
    max-width: 1380px;
    position: relative;
    z-index: 1;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(96,165,250,0.2); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(96,165,250,0.4); }

/* ────────────────────────────────
   GLASS CARDS
──────────────────────────────── */
.card {
    background: rgba(255,255,255,0.026);
    border: 1px solid rgba(255,255,255,0.065);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.8rem;
    transition: border-color 0.25s ease, background 0.25s ease, transform 0.2s ease;
    backdrop-filter: blur(6px);
}
.card:hover {
    border-color: rgba(96,165,250,0.22);
    background: rgba(96,165,250,0.025);
    transform: translateY(-1px);
}

.card-blue {
    background: linear-gradient(135deg, rgba(15,98,254,0.06) 0%, rgba(99,102,241,0.04) 100%);
    border: 1px solid rgba(15,98,254,0.16);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.8rem;
    backdrop-filter: blur(6px);
}

.card-green {
    background: linear-gradient(135deg, rgba(16,185,129,0.06) 0%, rgba(5,150,105,0.03) 100%);
    border: 1px solid rgba(16,185,129,0.16);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.8rem;
}

.card-amber {
    background: linear-gradient(135deg, rgba(245,158,11,0.06) 0%, rgba(217,119,6,0.03) 100%);
    border: 1px solid rgba(245,158,11,0.16);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.8rem;
}

/* ────────────────────────────────
   TOPBAR / NAV
──────────────────────────────── */
.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 0 0.75rem;
    border-bottom: 1px solid rgba(255,255,255,0.055);
    margin-bottom: 1.75rem;
    position: sticky;
    top: 0;
    background: rgba(4,4,15,0.88);
    backdrop-filter: blur(16px);
    z-index: 100;
}
.nav-logo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: -0.025em;
    background: linear-gradient(90deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.nav-logo-icon { font-size: 1.3rem; }
.user-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(15,98,254,0.09);
    border: 1px solid rgba(15,98,254,0.2);
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 0.78rem;
    color: #93c5fd;
    font-weight: 500;
}

/* ────────────────────────────────
   METRIC CARDS
──────────────────────────────── */
.metric-card {
    background: linear-gradient(145deg, rgba(15,98,254,0.08) 0%, rgba(105,41,196,0.08) 100%);
    border: 1px solid rgba(255,255,255,0.075);
    border-radius: 16px;
    padding: 1.3rem 1rem;
    text-align: center;
    height: 100%;
    transition: border-color 0.25s ease, transform 0.2s ease;
    backdrop-filter: blur(6px);
}
.metric-card:hover {
    border-color: rgba(96,165,250,0.28);
    transform: translateY(-2px);
}
.metric-value {
    font-size: 1.85rem;
    font-weight: 900;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
    letter-spacing: -0.03em;
}
.metric-label {
    font-size: 0.67rem;
    color: #64748b;
    margin-top: 0.45rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700;
}
.metric-sub { font-size: 0.68rem; color: #34d399; margin-top: 0.3rem; font-weight: 600; }

/* ────────────────────────────────
   HERO / LANDING TYPOGRAPHY
──────────────────────────────── */
.hero-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(15,98,254,0.1);
    border: 1px solid rgba(15,98,254,0.22);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.72rem;
    font-weight: 700;
    color: #93c5fd;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 1.1rem;
}
.main-header {
    font-size: 3.2rem;
    font-weight: 900;
    letter-spacing: -0.04em;
    line-height: 1.08;
    background: linear-gradient(135deg, #ffffff 0%, #93c5fd 40%, #a78bfa 70%, #34d399 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.5rem;
}
.hero-sub {
    font-size: 1rem;
    color: #64748b;
    line-height: 1.65;
    max-width: 520px;
    margin-bottom: 1.4rem;
    font-weight: 400;
}
.section-label {
    font-size: 0.67rem;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.6rem;
}
.section-header {
    font-size: 0.97rem;
    font-weight: 700;
    color: #93c5fd;
    border-left: 3px solid #3b82f6;
    padding-left: 0.7rem;
    margin: 1.6rem 0 1rem;
    letter-spacing: 0.005em;
}
.page-sub { color: #475569; font-size: 0.85rem; margin-bottom: 1rem; }

/* ────────────────────────────────
   BADGES
──────────────────────────────── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.69rem;
    font-weight: 700;
    margin-right: 5px;
    margin-bottom: 5px;
    line-height: 1.6;
    letter-spacing: 0.02em;
}
.badge-ibm    { background: rgba(15,98,254,0.1);   color: #60a5fa;  border: 1px solid rgba(15,98,254,0.25); }
.badge-groq   { background: rgba(105,41,196,0.1);  color: #a78bfa;  border: 1px solid rgba(105,41,196,0.25); }
.badge-gemini { background: rgba(234,179,8,0.1);   color: #fbbf24;  border: 1px solid rgba(234,179,8,0.25); }
.badge-rag    { background: rgba(52,211,153,0.1);  color: #34d399;  border: 1px solid rgba(52,211,153,0.25); }
.badge-live   { background: rgba(239,68,68,0.1);   color: #f87171;  border: 1px solid rgba(239,68,68,0.25); }
.badge-crag-correct   { background: rgba(16,185,129,0.12); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
.badge-crag-ambiguous { background: rgba(245,158,11,0.12); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
.badge-crag-incorrect { background: rgba(239,68,68,0.12);  color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }

/* ────────────────────────────────
   NEWS CARDS
──────────────────────────────── */
.news-card {
    background: rgba(255,255,255,0.018);
    border: 1px solid rgba(255,255,255,0.055);
    border-radius: 14px;
    padding: 1rem 1.15rem;
    margin-bottom: 0.7rem;
    border-left: 3px solid #1d4ed8;
    transition: background 0.2s ease, border-left-color 0.2s ease, transform 0.2s ease;
}
.news-card:hover {
    background: rgba(15,98,254,0.05);
    border-left-color: #60a5fa;
    transform: translateX(3px);
}
.news-title   { font-size: 0.86rem; font-weight: 600; color: #e2e8f0; margin: 0.35rem 0 0.3rem; line-height: 1.45; }
.news-snippet { font-size: 0.76rem; color: #94a3b8; line-height: 1.6; margin-bottom: 0.4rem; }
.news-meta    { font-size: 0.68rem; color: #475569; }
.news-cat-chip { display:inline-block; padding: 2px 10px; border-radius: 8px; font-size: 0.65rem; font-weight: 700; }

/* ────────────────────────────────
   EXPLORE CARDS
──────────────────────────────── */
.explore-card {
    background: rgba(15,98,254,0.03);
    border: 1px solid rgba(15,98,254,0.1);
    border-radius: 14px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.6rem;
    border-left: 3px solid rgba(59,130,246,0.3);
    transition: all 0.2s ease;
}
.explore-card:hover { border-left-color: #60a5fa; background: rgba(15,98,254,0.07); }
.explore-title   { font-size: 0.87rem; font-weight: 600; color: #93c5fd; margin-bottom: 0.35rem; line-height: 1.4; }
.explore-snippet { font-size: 0.77rem; color: #94a3b8; line-height: 1.6; margin-bottom: 0.4rem; }
.explore-url     { font-size: 0.69rem; color: #475569; }

/* ────────────────────────────────
   REWRITE / UNDERSTANDING CARD
──────────────────────────────── */
.rewrite-card {
    background: linear-gradient(135deg, rgba(234,179,8,0.04) 0%, rgba(15,98,254,0.05) 100%);
    border: 1px solid rgba(234,179,8,0.16);
    border-radius: 18px;
    padding: 1.6rem 1.8rem;
    margin: 1.2rem 0 1.6rem;
    backdrop-filter: blur(8px);
}
.rewrite-header {
    font-size: 0.68rem;
    font-weight: 700;
    color: #fbbf24;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: 7px;
}
.rewrite-row {
    display: grid;
    grid-template-columns: 170px 1fr;
    gap: 0.5rem 1.2rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    align-items: flex-start;
}
.rewrite-row:last-child { border-bottom: none; }
.rewrite-key { font-size: 0.75rem; font-weight: 600; color: #60a5fa; padding-top: 0.05rem; }
.rewrite-val { font-size: 0.83rem; color: #cbd5e1; line-height: 1.7; }

/* ────────────────────────────────
   CRAG PIPELINE
──────────────────────────────── */
.crag-node {
    background: rgba(255,255,255,0.016);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    transition: border-color 0.2s ease;
}
.crag-node.done {
    border-color: rgba(16,185,129,0.2);
    background: rgba(16,185,129,0.025);
}
.crag-node.done:hover { border-color: rgba(16,185,129,0.38); }
.crag-icon  { font-size: 1.1rem; margin-top: 0.1rem; flex-shrink: 0; width: 26px; text-align: center; }
.crag-body  {}
.crag-title { font-size: 0.83rem; font-weight: 700; color: #e2e8f0; margin-bottom: 0.2rem; }
.crag-desc  { font-size: 0.75rem; color: #64748b; line-height: 1.6; }
.crag-node.done .crag-title { color: #34d399; }

.crag-connector {
    width: 2px;
    height: 18px;
    background: linear-gradient(to bottom, rgba(16,185,129,0.3), rgba(96,165,250,0.2));
    margin: 0 0 0 12px;
}

.crag-action-box {
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    margin: 1rem 0;
    font-size: 0.88rem;
    font-weight: 600;
    line-height: 1.55;
}
.crag-action-correct   { background: rgba(16,185,129,0.07);  border: 1px solid rgba(16,185,129,0.26); color: #10b981; }
.crag-action-ambiguous { background: rgba(245,158,11,0.07);  border: 1px solid rgba(245,158,11,0.26); color: #f59e0b; }
.crag-action-incorrect { background: rgba(239,68,68,0.07);   border: 1px solid rgba(239,68,68,0.26);  color: #ef4444; }

/* ────────────────────────────────
   SCORE BARS
──────────────────────────────── */
.score-row { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.45rem; }
.score-label { font-family: 'JetBrains Mono', monospace; font-size: 0.73rem; color: #94a3b8; width: 62px; flex-shrink: 0; }
.score-track { flex: 1; height: 7px; background: rgba(255,255,255,0.05); border-radius: 99px; overflow: hidden; }
.score-fill  { height: 100%; border-radius: 99px; transition: width 0.6s ease; }
.score-val   { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #64748b; width: 50px; text-align: right; flex-shrink: 0; }

/* ────────────────────────────────
   BUSINESS MODEL CANVAS
──────────────────────────────── */
.bmc-block {
    background: rgba(15,98,254,0.04);
    border: 1px solid rgba(15,98,254,0.11);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    height: 100%;
    transition: border-color 0.2s, background 0.2s;
}
.bmc-block:hover { border-color: rgba(15,98,254,0.25); background: rgba(15,98,254,0.07); }
.bmc-icon  { font-size: 1.4rem; margin-bottom: 0.3rem; }
.bmc-label { font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.6rem; }
.bmc-item  {
    font-size: 0.8rem;
    color: #cbd5e1;
    padding: 4px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    line-height: 1.45;
    display: flex;
    align-items: flex-start;
    gap: 5px;
}
.bmc-item:last-child { border-bottom: none; }
.bmc-bullet { color: #3b82f6; flex-shrink: 0; margin-top: 1px; font-size: 0.7rem; }

/* ────────────────────────────────
   RISK LEVELS
──────────────────────────────── */
.risk-high   { color: #f87171; font-weight: 800; font-size: 0.76rem; background: rgba(239,68,68,0.1); padding: 2px 9px; border-radius: 8px; }
.risk-medium { color: #fbbf24; font-weight: 800; font-size: 0.76rem; background: rgba(245,158,11,0.1); padding: 2px 9px; border-radius: 8px; }
.risk-low    { color: #34d399; font-weight: 800; font-size: 0.76rem; background: rgba(52,211,153,0.1); padding: 2px 9px; border-radius: 8px; }

/* ────────────────────────────────
   AUTH CARD
──────────────────────────────── */
.auth-panel {
    background: rgba(255,255,255,0.022);
    border: 1px solid rgba(255,255,255,0.065);
    border-radius: 22px;
    padding: 2.2rem 2rem;
    max-width: 440px;
    margin: 0 auto;
    backdrop-filter: blur(12px);
    box-shadow: 0 24px 80px rgba(0,0,0,0.4);
}
.auth-logo  {
    width: 52px; height: 52px;
    background: linear-gradient(135deg, #1d4ed8, #7c3aed);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.6rem;
    margin: 0 auto 1rem;
}
.auth-title { font-size: 1.5rem; font-weight: 800; text-align: center; color: #f1f5f9; margin-bottom: 0.3rem; letter-spacing: -0.025em; }
.auth-sub   { font-size: 0.82rem; color: #475569; text-align: center; margin-bottom: 1.6rem; }

/* ────────────────────────────────
   TREND PILLS
──────────────────────────────── */
.trend-pill {
    display: inline-block;
    background: rgba(15,98,254,0.08);
    border: 1px solid rgba(15,98,254,0.16);
    border-radius: 20px;
    padding: 3px 13px;
    font-size: 0.73rem;
    color: #93c5fd;
    margin: 2px 3px;
    transition: background 0.15s, border-color 0.15s;
}
.trend-pill:hover { background: rgba(15,98,254,0.16); border-color: rgba(15,98,254,0.3); }

/* ────────────────────────────────
   DIVIDERS & SEPARATORS
──────────────────────────────── */
.section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.07) 20%, rgba(255,255,255,0.07) 80%, transparent);
    margin: 1.8rem 0;
    border: none;
}

/* ────────────────────────────────
   FUNDING STAGE CARD
──────────────────────────────── */
.funding-stage {
    background: linear-gradient(135deg, rgba(15,98,254,0.07) 0%, rgba(99,102,241,0.05) 100%);
    border: 1px solid rgba(99,102,241,0.18);
    border-radius: 16px;
    padding: 1.1rem 1rem;
    text-align: center;
    transition: transform 0.2s, border-color 0.2s;
}
.funding-stage:hover { transform: translateY(-3px); border-color: rgba(99,102,241,0.35); }
.funding-stage-name   { font-size: 0.72rem; font-weight: 700; color: #60a5fa; text-transform: uppercase; letter-spacing: 0.06em; }
.funding-stage-amount { font-size: 1.2rem; font-weight: 900; color: #f1f5f9; margin: 0.3rem 0; letter-spacing: -0.02em; }
.funding-stage-time   { font-size: 0.68rem; color: #475569; }
.funding-stage-src    { font-size: 0.7rem; color: #34d399; margin-top: 0.25rem; font-weight: 600; }

/* ────────────────────────────────
   POLICY BRIEF CARD
──────────────────────────────── */
.policy-brief {
    background: linear-gradient(135deg, rgba(15,98,254,0.05) 0%, rgba(105,41,196,0.04) 100%);
    border: 1px solid rgba(15,98,254,0.14);
    border-radius: 18px;
    padding: 1.6rem 1.8rem;
    margin-bottom: 1.4rem;
    line-height: 1.85;
    font-size: 0.9rem;
    color: #cbd5e1;
}
.policy-brief-header {
    font-size: 0.7rem;
    font-weight: 700;
    color: #60a5fa;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 7px;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid rgba(15,98,254,0.14);
}

/* ────────────────────────────────
   IDEA INPUT AREA
──────────────────────────────── */
.idea-input-wrapper {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    padding: 1.4rem 1.6rem 1rem;
    margin-bottom: 1.2rem;
    transition: border-color 0.25s;
}
.idea-input-wrapper:focus-within {
    border-color: rgba(59,130,246,0.4);
    background: rgba(59,130,246,0.025);
}

/* ────────────────────────────────
   STREAMLIT OVERRIDES
──────────────────────────────── */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 700 !important;
    transition: all 0.22s ease !important;
    font-size: 0.86rem !important;
    letter-spacing: 0.01em !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1d4ed8 0%, #6d28d9 100%) !important;
    border: none !important;
    color: #fff !important;
    box-shadow: 0 4px 24px rgba(15,98,254,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(15,98,254,0.35) !important;
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0px) !important;
    box-shadow: 0 2px 12px rgba(15,98,254,0.2) !important;
}
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #94a3b8 !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.07) !important;
    border-color: rgba(255,255,255,0.18) !important;
    color: #e2e8f0 !important;
}

/* Text inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-size: 0.88rem !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(59,130,246,0.45) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
    background: rgba(59,130,246,0.03) !important;
}
.stTextInput > label, .stTextArea > label, .stSelectbox > label {
    color: #64748b !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 3px;
    border-bottom: 1px solid rgba(255,255,255,0.07) !important;
    background: transparent !important;
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    border-radius: 10px 10px 0 0 !important;
    padding: 9px 18px !important;
    color: #475569 !important;
    background: transparent !important;
    transition: color 0.2s, background 0.2s !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #94a3b8 !important;
    background: rgba(255,255,255,0.03) !important;
}
.stTabs [aria-selected="true"] {
    color: #60a5fa !important;
    background: rgba(15,98,254,0.09) !important;
    border-bottom: 2px solid #3b82f6 !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.4rem !important; }

/* Expander */
.stExpander {
    border: 1px solid rgba(255,255,255,0.065) !important;
    border-radius: 14px !important;
    background: rgba(255,255,255,0.016) !important;
}
.stExpander summary {
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    color: #94a3b8 !important;
}

/* Toggle */
.stToggle label { font-size: 0.85rem !important; color: #94a3b8 !important; }

/* Alerts */
div[data-testid="stAlert"] {
    border-radius: 12px !important;
    font-size: 0.84rem !important;
    border: 1px solid !important;
}
div[data-testid="stAlert"][data-baseweb*="positive"] {
    background: rgba(16,185,129,0.07) !important;
    border-color: rgba(16,185,129,0.2) !important;
    color: #6ee7b7 !important;
}
div[data-testid="stAlert"][data-baseweb*="warning"] {
    background: rgba(245,158,11,0.07) !important;
    border-color: rgba(245,158,11,0.2) !important;
}
div[data-testid="stAlert"][data-baseweb*="error"] {
    background: rgba(239,68,68,0.07) !important;
    border-color: rgba(239,68,68,0.2) !important;
}
div[data-testid="stAlert"][data-baseweb*="info"] {
    background: rgba(15,98,254,0.07) !important;
    border-color: rgba(15,98,254,0.2) !important;
    color: #93c5fd !important;
}

/* Status widget */
div[data-testid="stStatusWidget"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 14px !important;
}

/* Radio */
.stRadio > div { gap: 1rem !important; }
.stRadio label { font-size: 0.84rem !important; color: #94a3b8 !important; }

/* Selectbox dropdown */
[data-baseweb="select"] > div { background: rgba(255,255,255,0.04) !important; }

/* Divider */
hr { border: none !important; height: 1px !important;
     background: linear-gradient(90deg, transparent, rgba(255,255,255,0.07) 20%, rgba(255,255,255,0.07) 80%, transparent) !important;
     margin: 1.6rem 0 !important; }

/* Caption */
.stCaption { color: #475569 !important; font-size: 0.76rem !important; }

/* Success / info inline */
.stSuccess { background: rgba(16,185,129,0.07) !important; }
.stInfo    { background: rgba(15,98,254,0.07)  !important; }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
for k, v in {
    "logged_in": False, "authenticated": False, "user": None, "user_email": None,
    "user_name": None, "user_profile": None, "page": "login", "blueprints": [],
    "hist_open": False, "hist_view_id": None, "hist_search": "",
    "hist_confirm_del": None, "hist_confirm_all": False,
    # Mentor state
    "mentor_session":       None,
    "mentor_session_id":    None,
    "mentor_messages_ui":   [],
    "mentor_input_key":     0,
    "mentor_pending_input": "",
    "_mentor_processing":   False,
    # Single source of truth for the most recently generated blueprint.
    # Persists across reruns (e.g. clicking "Explore with AI Mentor") until
    # a new blueprint is generated, the user logs out, or clears the session.
    "current_blueprint": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# CACHED AI RESOURCES
# ══════════════════════════════════════════════════════════════════════════════
import os
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/st_models"
os.environ["HF_HOME"] = "/tmp/hf_cache"


@st.cache_resource
def load_reranker():
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def get_secret(key):
    """Works both locally (.env) and on Streamlit Cloud (secrets.toml)"""
    try:
        val = st.secrets.get(key)
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key)


@st.cache_resource(show_spinner="Loading Granite model... (first load may take 3-5 mins)")
def load_granite():
    return ModelInference(
        model_id="ibm/granite-4-h-small",
        credentials={
            "apikey": get_secret("IBM_API_KEY"),
            "url":    get_secret("IBM_URL")
        },
        project_id=get_secret("IBM_PROJECT_ID")
    )

@st.cache_resource(show_spinner="Loading Chroma collection... (first load may take 3-5 mins)")
def load_collection():
    client = chromadb.PersistentClient(path="chroma_db")
    return client.get_collection("startup_docs")

@st.cache_resource(show_spinner="Loading Groq client... (first load may take 3-5 mins)")
def load_groq():
    return Groq(api_key=get_secret("GROQ_API_KEY"))

@st.cache_resource(show_spinner="Loading Tavily client... (first load may take 3-5 mins)")
def load_tavily():
    return TavilyClient(api_key=get_secret("TAVILY_API_KEY"))

@st.cache_resource(show_spinner="Loading Gemini client... (first load may take 3-5 mins)")
def load_gemini():
    genai.configure(api_key=get_secret("GOOGLE_API_KEY"))
    return genai


embedder    = None  # Using Google Gemini embeddings now
reranker    = load_reranker()
granite     = load_granite()
collection  = load_collection()
groq_client = load_groq()
tavily      = load_tavily()
gemini      = load_gemini()
NEWS_KEY    = get_secret("NEWS_API_KEY")

# Shared Plotly layout
LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e2e8f0", family="Inter, sans-serif"),
    margin=dict(l=20, r=20, t=52, b=20)
)


# ══════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def render_rewrite_card(rewritten_query: str):
    SECTION_KEYS = [
        ("PROBLEM STATEMENT",          "🔍", "Problem Statement"),
        ("TARGET USERS",               "👥", "Target Users"),
        ("CORE SOLUTION",              "💡", "Core Solution"),
        ("KEY FEATURES",               "⚡", "Key Features"),
        ("TECHNOLOGIES",               "⚙️", "Technologies"),
        ("INDUSTRY",                   "🏭", "Industry"),
        ("GEOGRAPHY",                  "🗺️", "Geography"),
        ("BUSINESS MODEL",             "💰", "Business Model"),
        ("REQUESTED BUSINESS ANALYSIS","📊", "Analysis Requested"),
        ("SEARCH CONTEXT",             "🔎", "Search Context"),
    ]
    parsed = {}
    current_key = None
    for line in rewritten_query.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        matched = False
        for (key, icon, label) in SECTION_KEYS:
            test = stripped.upper()
            if test.startswith(key + ":") or test == key:
                current_key = key
                val = stripped[len(key):].lstrip(":").strip()
                parsed[key] = val
                matched = True
                break
            if test.startswith("KEYWORDS:") or test.startswith("RETRIEVAL QUERIES:"):
                current_key = None
                matched = True
                break
        if not matched and current_key and stripped:
            parsed[current_key] = (parsed.get(current_key, "") + "\n" + stripped).strip()

    if not parsed:
        st.markdown(f"""<div class="rewrite-card">
<div class="rewrite-header">✨ Gemini Flash — How We Understood Your Idea</div>
<div style="font-size:0.84rem;color:#cbd5e1;line-height:1.8;white-space:pre-line">{rewritten_query[:900]}</div>
</div>""", unsafe_allow_html=True)
        return

    rows_html = ""
    for (key, icon, label) in SECTION_KEYS:
        val = parsed.get(key, "").strip()
        if not val:
            continue
        val_display = val.replace("\n-", "<br>•").replace("\n•", "<br>•")
        rows_html += f"""<div class="rewrite-row">
<div class="rewrite-key">{icon}&nbsp; {label}</div>
<div class="rewrite-val">{val_display}</div>
</div>"""

    st.markdown(f"""<div class="rewrite-card">
<div class="rewrite-header">✨ Gemini Flash — Structured Understanding of Your Idea</div>
{rows_html}
</div>""", unsafe_allow_html=True)


def render_score_bars(raw_logits: list, upper: float = -3.0, lower: float = -6.5):
    if not raw_logits:
        return
    st.markdown('<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin-bottom:0.75rem">CrossEncoder Relevance Logits</div>', unsafe_allow_html=True)
    for i, logit in enumerate(raw_logits[:8]):
        pct = max(0.0, min(1.0, (logit + 10) / 10))
        if logit >= upper:
            color = "#10b981"
        elif logit >= lower:
            color = "#f59e0b"
        else:
            color = "#ef4444"
        bar_w = int(pct * 100)
        st.markdown(f"""<div class="score-row">
<div class="score-label">Doc {i+1}</div>
<div class="score-track"><div class="score-fill" style="width:{bar_w}%;background:{color}"></div></div>
<div class="score-val">{logit:.2f}</div>
</div>""", unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.69rem;color:#475569;margin-top:0.6rem">'
        f'<span style="color:#10b981">■</span> CORRECT ≥ {upper} &nbsp;·&nbsp; '
        f'<span style="color:#f59e0b">■</span> AMBIGUOUS (between) &nbsp;·&nbsp; '
        f'<span style="color:#ef4444">■</span> INCORRECT &lt; {lower}</div>',
        unsafe_allow_html=True
    )


def render_explore_section(explore_results: list, confidence: str):
    if not explore_results:
        return
    cfg = {
        "CORRECT":   ("🌐 Live Web Insights — Explore Further",      "#60a5fa", "rgba(15,98,254,0.07)"),
        "AMBIGUOUS": ("🌐 Web Context + Explore Further",            "#f59e0b", "rgba(245,158,11,0.07)"),
        "INCORRECT": ("🌐 What the Web Found on This Topic",         "#94a3b8", "rgba(255,255,255,0.03)"),
    }
    title_txt, color, bg = cfg.get(confidence, cfg["CORRECT"])
    st.markdown(f"""<div style="background:{bg};border:1px solid {color}22;
border-radius:18px;padding:1.4rem 1.6rem;margin:1.4rem 0">
<div style="font-size:0.78rem;font-weight:700;color:{color};margin-bottom:1.1rem;
letter-spacing:0.05em;text-transform:uppercase">{title_txt}</div>""",
        unsafe_allow_html=True)
    for r in explore_results:
        title_t = r.get("title", "Untitled")
        snippet = r.get("content", "")[:240]
        url     = r.get("url", "#")
        domain  = url.split("/")[2] if url.startswith("http") else url
        st.markdown(f"""<div class="explore-card">
<div class="explore-title">{title_t}</div>
<div class="explore-snippet">{snippet}…</div>
<div class="explore-url">🔗 <a href="{url}" target="_blank" style="color:#60a5fa">{domain}</a></div>
</div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_keyword_chips(keywords: list):
    if not keywords:
        return
    chips = "".join([f'<span class="trend-pill">{k}</span>' for k in keywords[:14]])
    st.markdown(f'<div style="margin-bottom:0.6rem">{chips}</div>', unsafe_allow_html=True)


def render_policy_brief(summary: str):
    """Render the IBM Granite policy brief in a beautiful, readable card."""
    if not summary:
        return
    st.markdown(f"""<div class="policy-brief">
<div class="policy-brief-header">🤖 IBM Granite 4.0 — Startup Policy Brief</div>
{summary}
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# AUTH PAGE
# ══════════════════════════════════════════════════════════════════════════════
def page_auth():
    left, right = st.columns([11, 9], gap="large")

    # ── Left: Hero + News ─────────────────────────────────────────────────────
    with left:
        st.markdown("<div style='padding-top:2.5rem'>", unsafe_allow_html=True)
        st.markdown('<div class="hero-eyebrow">🚀 AI-Powered Startup Intelligence</div>', unsafe_allow_html=True)
        st.markdown('<div class="main-header">Build Your Startup<br>Blueprint in Minutes</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="hero-sub">Powered by IBM Granite 4.0, Groq Llama 3.3 & Gemini Flash. '
            'Get a full Business Model Canvas, budget plan, GTM strategy, '
            'investor map & risk matrix — grounded in live Indian policy data.</p>',
            unsafe_allow_html=True
        )

        # Tech stack badges
        st.markdown(
            '<span class="badge badge-ibm">IBM Granite 4.0</span>'
            '<span class="badge badge-groq">Groq Llama 3.3</span>'
            '<span class="badge badge-gemini">✨ Gemini Flash</span>'
            '<span class="badge badge-rag">CRAG Self-Correcting RAG</span>'
            '<span class="badge badge-live">🔴 LIVE Web Search</span>',
            unsafe_allow_html=True
        )
        st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)

        # Stats row
        s1, s2, s3, s4 = st.columns(4)
        stats = [
            ("₹12T",  "Market Size"),
            ("112",   "Unicorns"),
            ("1.5L+", "DPIIT Startups"),
            ("6",     "AI Models"),
        ]
        for col, (val, label) in zip([s1, s2, s3, s4], stats):
            with col:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-value">{val}</div>'
                    f'<div class="metric-label">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)

        # Trending pills
        st.markdown('<div class="section-label">🔥 Trending in Indian Startup Ecosystem</div>', unsafe_allow_html=True)
        trends = ["AI & ML", "Fintech Unicorns", "Agritech", "EV Ecosystem",
                  "D2C Brands", "SaaS for SMBs", "HealthTech", "EdTech 2.0",
                  "Climate Tech", "Deep Tech", "B2B Commerce", "ONDC",
                  "Web3", "Logistics Tech"]
        render_keyword_chips(trends)

        st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">📰 Latest Startup News</div>', unsafe_allow_html=True)

        articles = []
        if NEWS_KEY:
            queries = [
                ("India startup funding 2025", "Funding"),
                ("Indian unicorn startup news", "Unicorns"),
                ("government startup scheme MSME India", "Policy"),
            ]
            for q, cat in queries:
                for a in get_startup_news(NEWS_KEY, query=q, page_size=3):
                    a["_cat"] = cat
                    articles.append(a)
        else:
            articles = [{
                "title": "Add NEWS_API_KEY to .env for live startup news",
                "description": "Real-time startup news from across India will appear here once configured.",
                "source": {"name": "System"}, "publishedAt": datetime.now().isoformat(),
                "url": "#", "_cat": "Info"
            }]

        cat_colors = {"Funding": "#34d399", "Unicorns": "#a78bfa", "Policy": "#60a5fa", "Info": "#94a3b8"}
        seen, count = set(), 0
        for a in articles:
            t = a.get("title", "")
            if t in seen or not t or t == "[Removed]":
                continue
            seen.add(t); count += 1
            if count > 9: break
            cat   = a.get("_cat", "News")
            color = cat_colors.get(cat, "#60a5fa")
            src   = a.get("source", {}).get("name", "")
            snip  = (a.get("description") or "")[:150]
            date  = a.get("publishedAt", "")[:10]
            url   = a.get("url", "#")
            st.markdown(f"""<div class="news-card">
<span class="news-cat-chip" style="background:{color}18;color:{color};border:1px solid {color}30">{cat}</span>
<div class="news-title">{t}</div>
<div class="news-snippet">{snip}</div>
<div class="news-meta">
  <span style="color:{color};font-weight:600">{src}</span>&nbsp;·&nbsp;{date}&nbsp;·&nbsp;
  <a href="{url}" target="_blank" style="color:#60a5fa;font-weight:500">Read →</a>
</div>
</div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Right: Auth Form ──────────────────────────────────────────────────────
    with right:
        st.markdown("<div style='padding-top:2.5rem'>", unsafe_allow_html=True)
        st.markdown("""<div class="auth-panel">
<div class="auth-logo">🚀</div>
<div class="auth-title">Welcome Back</div>
<div class="auth-sub">Sign in to generate your startup blueprint</div>
</div>""", unsafe_allow_html=True)

        tab_sign, tab_reg = st.tabs(["🔑  Sign In", "📝  Register"])

        with tab_sign:
            em = st.text_input("Email Address", key="li_em", placeholder="you@example.com")
            pw = st.text_input("Password", type="password", key="li_pw", placeholder="••••••••")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

            if st.button("Sign In →", use_container_width=True, type="primary", key="btn_li"):
                if em and pw:
                    from auth import login_with_password, set_session
                    ok, profile, msg = login_with_password(em, pw)
                    if ok:
                        set_session(profile)
                        st.session_state.logged_in = True
                        st.session_state.user = {
                            "name":                 profile.get("name", profile.get("email", "User")),
                            "email":                profile.get("email", ""),
                            "blueprints_generated": get_blueprint_count(),
                            "created_at":           "",
                        }
                        st.session_state.page = "dashboard"
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please fill all fields.")

            st.divider()
            from auth import get_google_login_url
            google_url = get_google_login_url()
            st.markdown(
                f'<a href="{google_url}" target="_self">'
                f'<button style="width:100%;padding:0.6rem;border-radius:12px;'
                f'background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);'
                f'color:#e2e8f0;font-size:0.86rem;font-weight:700;cursor:pointer">'
                f'🔵 Continue with Google</button></a>',
                unsafe_allow_html=True
            )

        with tab_reg:
            name = st.text_input("Full Name",        key="rg_nm", placeholder="Priya Sharma")
            em2  = st.text_input("Email Address",    key="rg_em", placeholder="you@example.com")
            pw2  = st.text_input("Password",         type="password", key="rg_pw", placeholder="Minimum 6 characters")
            pw3  = st.text_input("Confirm Password", type="password", key="rg_cf", placeholder="Re-enter password")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Create Account →", use_container_width=True, type="primary", key="btn_rg"):
                if not all([name, em2, pw2, pw3]): st.warning("Please fill all fields.")
                elif len(pw2) < 6:                 st.warning("Password must be at least 6 characters.")
                elif pw2 != pw3:                   st.error("Passwords don't match.")
                else:
                    from auth import register_user as _register
                    ok, msg = _register(name, em2, pw2)
                    if ok: st.success("Account created! Please sign in.")
                    else:  st.error(msg)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # Feature list
        st.markdown("""<div style="background:rgba(15,98,254,0.04);border:1px solid rgba(15,98,254,0.1);
border-radius:16px;padding:1.2rem 1.3rem">
<div style="font-size:0.68rem;font-weight:700;color:#475569;text-transform:uppercase;
letter-spacing:0.08em;margin-bottom:0.9rem">What's inside your blueprint</div>
<div style="display:flex;flex-direction:column;gap:0.55rem">
  <div style="font-size:0.81rem;color:#94a3b8;display:flex;align-items:flex-start;gap:0.6rem">
    <span style="color:#fbbf24;flex-shrink:0">✨</span>
    <span><b style="color:#e2e8f0">Gemini Flash</b> — structured 10-field query rewriting</span>
  </div>
  <div style="font-size:0.81rem;color:#94a3b8;display:flex;align-items:flex-start;gap:0.6rem">
    <span style="color:#34d399;flex-shrink:0">🔁</span>
    <span><b style="color:#e2e8f0">CRAG</b> — self-correcting RAG (Correct / Ambiguous / Incorrect)</span>
  </div>
  <div style="font-size:0.81rem;color:#94a3b8;display:flex;align-items:flex-start;gap:0.6rem">
    <span style="color:#60a5fa;flex-shrink:0">📋</span>
    <span><b style="color:#e2e8f0">Business Model Canvas</b> — all 9 building blocks</span>
  </div>
  <div style="font-size:0.81rem;color:#94a3b8;display:flex;align-items:flex-start;gap:0.6rem">
    <span style="color:#a78bfa;flex-shrink:0">💰</span>
    <span><b style="color:#e2e8f0">Phase-wise Budget</b> — visual charts with funding advice</span>
  </div>
  <div style="font-size:0.81rem;color:#94a3b8;display:flex;align-items:flex-start;gap:0.6rem">
    <span style="color:#f87171;flex-shrink:0">📣</span>
    <span><b style="color:#e2e8f0">Go-to-Market Strategy</b> + 12-month milestone timeline</span>
  </div>
  <div style="font-size:0.81rem;color:#94a3b8;display:flex;align-items:flex-start;gap:0.6rem">
    <span style="color:#34d399;flex-shrink:0">🏛️</span>
    <span><b style="color:#e2e8f0">Govt Scheme Matcher</b> — DPIIT, MSME, Startup India</span>
  </div>
  <div style="font-size:0.81rem;color:#94a3b8;display:flex;align-items:flex-start;gap:0.6rem">
    <span style="color:#fbbf24;flex-shrink:0">🏆</span>
    <span><b style="color:#e2e8f0">Competitor Landscape</b> + differentiator analysis</span>
  </div>
  <div style="font-size:0.81rem;color:#94a3b8;display:flex;align-items:flex-start;gap:0.6rem">
    <span style="color:#f87171;flex-shrink:0">⚠️</span>
    <span><b style="color:#e2e8f0">Risk Matrix</b> — probability × severity with mitigations</span>
  </div>
</div>
</div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GROQ GENERATION FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def ask_groq(sys_msg: str, usr_msg: str, json_mode: bool = False) -> str:
    kw = {"response_format": {"type": "json_object"}} if json_mode else {}
    r  = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": usr_msg}],
        temperature=0.5, max_tokens=2000, **kw
    )
    return r.choices[0].message.content


def gen_bmc(idea, sector, model_type, ctx):
    s = f"Expert {sector} {model_type} startup strategist for India. Return only valid JSON."
    u = (f"Startup brief:\n{idea}\n\nPolicy context:\n{ctx}\n\n"
         'Return ONLY JSON: {"customer_segments":[],"value_propositions":[],"channels":[],'
         '"customer_relationships":[],"revenue_streams":[],"key_resources":[],'
         '"key_activities":[],"key_partners":[],"cost_structure":[]}')
    return json.loads(ask_groq(s, u, json_mode=True))


def gen_budget(idea, sector, ctx):
    s = f"Startup financial advisor for {sector} in India. Return only valid JSON."
    u = (f"Startup brief:\n{idea}\n\nPolicy context:\n{ctx}\n\n"
         'Return ONLY this JSON: {"phases":['
         '{"name":"MVP","duration":"Month 1-3","items":[{"item":"Tech Development","amount":120000}],"total":120000},'
         '{"name":"Launch","duration":"Month 4-6","items":[{"item":"Marketing","amount":80000}],"total":80000},'
         '{"name":"Growth","duration":"Month 7-12","items":[{"item":"Scaling","amount":180000}],"total":180000}'
         '],"total_12_months":380000,"funding_suggestion":"Bootstrap + Startup India Seed Fund"}')
    d = json.loads(ask_groq(s, u, json_mode=True))
    if "phases" not in d:
        for k in ["budget_phases", "phase", "plan", "budget", "breakdown"]:
            if k in d: d["phases"] = d[k]; break
        else:
            d["phases"] = [
                {"name": "MVP",    "duration": "Month 1-3",  "items": [{"item": "Setup",     "amount": 150000}], "total": 150000},
                {"name": "Launch", "duration": "Month 4-6",  "items": [{"item": "Marketing", "amount": 200000}], "total": 200000},
                {"name": "Growth", "duration": "Month 7-12", "items": [{"item": "Scaling",   "amount": 350000}], "total": 350000},
            ]
    if "total_12_months" not in d: d["total_12_months"] = sum(p.get("total", 0) for p in d["phases"])
    if "funding_suggestion" not in d: d["funding_suggestion"] = "Bootstrap + Startup India Grant"
    return d


def gen_gtm(idea, sector, model_type, ctx):
    s = f"GTM strategist for {sector} {model_type} startups in India. Return only valid JSON."
    u = (f"Startup brief:\n{idea}\n\nPolicy context:\n{ctx}\n\n"
         'Return ONLY JSON: {"target_market":"desc","market_size":"₹X,000 Crore",'
         '"launch_strategy":["step1","step2","step3"],'
         '"growth_channels":[{"channel":"name","priority":"High","cost":"Free"}],'
         '"milestones":[{"month":1,"goal":"goal"},{"month":3,"goal":"goal"},{"month":6,"goal":"goal"},{"month":9,"goal":"goal"},{"month":12,"goal":"goal"}],'
         '"key_metrics":["metric1","metric2","metric3"]}')
    return json.loads(ask_groq(s, u, json_mode=True))


def gen_investors(idea, sector, ctx):
    s = "Startup funding advisor for India. Return only valid JSON."
    u = (f"Startup brief:\n{idea}\n\nPolicy context:\n{ctx}\n\n"
         'Return ONLY JSON: {"government_schemes":[{"name":"scheme","benefit":"desc","eligibility":"who"}],'
         '"investor_types":[{"type":"Angel","stage":"Pre-seed","examples":["name"]}],'
         '"incubators":[{"name":"name","location":"city","focus":"sector"}],'
         '"funding_roadmap":[{"stage":"Pre-seed","amount":"₹10-50L","timeline":"Month 1-6","source":"Bootstrap"}],'
         '"pitch_tips":["tip1","tip2"]}')
    return json.loads(ask_groq(s, u, json_mode=True))


def gen_competitors(idea, sector):
    s = "Competitive intelligence analyst for Indian markets. Return only valid JSON."
    u = (f"{sector} startup brief:\n{idea}\n\n"
         'Return ONLY JSON: {"competitors":['
         '{"name":"Co1","strength":"s","weakness":"w","market_share":30},'
         '{"name":"Co2","strength":"s","weakness":"w","market_share":25},'
         '{"name":"Co3","strength":"s","weakness":"w","market_share":20},'
         '{"name":"Our Startup","strength":"advantage","weakness":"gap","market_share":5}],'
         '"our_differentiators":["d1","d2","d3"],"market_gaps":["g1","g2"]}')
    return json.loads(ask_groq(s, u, json_mode=True))


def gen_risks(idea, sector):
    s = "Risk analyst for Indian startups. Return only valid JSON."
    u = (f"{sector} startup brief:\n{idea}\n\n"
         'Return ONLY JSON: {"risks":['
         '{"category":"Market","risk":"desc","severity":"High","probability":"Medium","mitigation":"strategy"},'
         '{"category":"Technical","risk":"desc","severity":"Medium","probability":"Low","mitigation":"strategy"},'
         '{"category":"Financial","risk":"desc","severity":"High","probability":"High","mitigation":"strategy"},'
         '{"category":"Regulatory","risk":"desc","severity":"Medium","probability":"Medium","mitigation":"strategy"},'
         '{"category":"Competition","risk":"desc","severity":"Medium","probability":"High","mitigation":"strategy"}]}')
    return json.loads(ask_groq(s, u, json_mode=True))


# ══════════════════════════════════════════════════════════════════════════════
# CHART BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def chart_budget(data):
    phases = [p["name"] for p in data["phases"]]
    totals = [p["total"] for p in data["phases"]]
    colors = ["#3b82f6", "#8b5cf6", "#10b981"]
    fig = go.Figure(go.Bar(
        x=phases, y=totals,
        marker=dict(
            color=colors[:len(phases)],
            line=dict(color=["#2563eb","#7c3aed","#059669"][:len(phases)], width=1.5),
            opacity=0.9
        ),
        text=[f"₹{t/100000:.1f}L" for t in totals],
        textposition="outside",
        textfont=dict(size=13, color="#e2e8f0", family="Inter"),
        hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}<extra></extra>",
        width=0.45
    ))
    fig.update_layout(**LAYOUT,
        title=dict(text="Phase-wise Budget Allocation", font=dict(size=14, color="#94a3b8"), x=0),
        height=320, showlegend=False,
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickfont=dict(size=13, color="#cbd5e1")),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickprefix="₹", tickformat=",", tickfont=dict(size=11, color="#94a3b8")),
        bargap=0.5
    )
    return fig


def chart_budget_donut(data):
    phases = [p["name"] for p in data["phases"]]
    totals = [p["total"] for p in data["phases"]]
    total  = sum(totals) or 1
    fig = go.Figure(go.Pie(
        labels=phases, values=totals, hole=0.70,
        marker=dict(colors=["#3b82f6","#8b5cf6","#10b981"][:len(phases)], line=dict(color="#04040f", width=4)),
        textinfo="label+percent",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="<b>%{label}</b><br>₹%{value:,.0f} · %{percent}<extra></extra>",
        pull=[0.05] * len(phases)
    ))
    fig.add_annotation(
        text=f"<b>₹{total/100000:.1f}L</b><br><span style='font-size:10px;color:#64748b'>Total</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=15, color="#60a5fa")
    )
    fig.update_layout(**LAYOUT,
        title=dict(text="Budget Split", font=dict(size=14, color="#94a3b8"), x=0),
        height=320,
        legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=11, color="#94a3b8"))
    )
    return fig


def chart_channels(channels):
    if not channels: return go.Figure()
    p_map = {"High": 3, "Medium": 2, "Low": 1}
    c_map = {"High": "#3b82f6", "Medium": "#8b5cf6", "Low": "#475569"}
    names  = [c["channel"] for c in channels]
    prios  = [p_map.get(c.get("priority","Medium"), 2) for c in channels]
    colors = [c_map.get(c.get("priority","Medium"), "#475569") for c in channels]
    labels = [f'{c.get("priority","")}  ·  {c.get("cost","")}' for c in channels]
    fig = go.Figure(go.Bar(
        x=prios, y=names, orientation="h",
        marker=dict(color=colors, opacity=0.85),
        text=labels, textposition="inside",
        textfont=dict(size=11, color="white"),
        hovertemplate="<b>%{y}</b><br>Priority: %{x}/3<extra></extra>",
        width=0.6
    ))
    for xv in [1.5, 2.5]:
        fig.add_vline(x=xv, line_dash="dot", line_color="rgba(255,255,255,0.07)", line_width=1)
    fig.update_layout(**LAYOUT,
        title=dict(text="Growth Channels — ranked by priority", font=dict(size=14, color="#94a3b8"), x=0),
        height=max(80 + len(channels) * 56, 280),
        showlegend=False,
        xaxis=dict(tickvals=[1,2,3], ticktext=["Low","Medium","High"],
            tickfont=dict(size=11, color="#64748b"), gridcolor="rgba(255,255,255,0.04)", range=[0,3.9]),
        yaxis=dict(tickfont=dict(size=12, color="#cbd5e1"), gridcolor="rgba(255,255,255,0.03)"),
        bargap=0.3
    )
    return fig


def chart_timeline(milestones):
    if not milestones: return go.Figure()
    months = [m["month"] for m in milestones]
    goals  = [m["goal"]  for m in milestones]
    cols   = ["#3b82f6","#6366f1","#8b5cf6","#a855f7","#0ea5e9"]
    fig = go.Figure()
    # Spine line
    fig.add_trace(go.Scatter(
        x=months, y=[0.5]*len(months), mode="lines",
        line=dict(color="rgba(59,130,246,0.2)", width=2.5), showlegend=False, hoverinfo="skip"
    ))
    # Milestone dots
    for i, (m, g) in enumerate(zip(months, goals)):
        c = cols[i % len(cols)]
        fig.add_trace(go.Scatter(
            x=[m], y=[0.5], mode="markers+text",
            marker=dict(size=34, color=c, line=dict(color="#04040f", width=3)),
            text=[f"M{m}"], textposition="middle center", textfont=dict(size=10, color="white"),
            hovertext=f"<b>Month {m}</b><br>{g}", hoverinfo="text", showlegend=False
        ))
    # Labels above/below
    for i, (m, g) in enumerate(zip(months, goals)):
        yshift = 30 if i % 2 == 0 else -30
        yanchor = "bottom" if i % 2 == 0 else "top"
        short = (g[:44] + "…") if len(g) > 44 else g
        fig.add_annotation(
            x=m, y=0.5, text=short, showarrow=False, yshift=yshift,
            font=dict(size=10, color="#94a3b8"), yanchor=yanchor, xanchor="center"
        )
    fig.update_layout(**LAYOUT,
        title=dict(text="12-Month Milestone Roadmap", font=dict(size=14, color="#94a3b8"), x=0),
        height=360, showlegend=False,
        xaxis=dict(
            title=dict(text="Month", font=dict(size=12, color="#64748b")),
            tickvals=months, ticktext=[f"Month {m}" for m in months],
            tickfont=dict(size=10, color="#94a3b8"),
            gridcolor="rgba(255,255,255,0.04)",
            range=[min(months)-1, max(months)+1]
        ),
        yaxis=dict(visible=False, range=[0.1, 0.9])
    )
    return fig


def chart_competitors(data):
    comps  = data.get("competitors", [])
    names  = [c["name"] for c in comps]
    shares = [c["market_share"] for c in comps]
    colors = ["#ef4444","#f59e0b","#6366f1","#0ea5e9","#34d399"]
    fig = go.Figure(go.Pie(
        labels=names, values=shares, hole=0.62,
        marker=dict(colors=colors[:len(comps)], line=dict(color="#04040f", width=4)),
        textinfo="label+percent",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>",
        pull=[0, 0, 0, 0.1, 0],
        rotation=25
    ))
    fig.add_annotation(text="Market<br>Share", x=0.5, y=0.5, showarrow=False, font=dict(size=12, color="#64748b"))
    fig.update_layout(**LAYOUT,
        title=dict(text="Competitive Market Share Landscape", font=dict(size=14, color="#94a3b8"), x=0),
        height=360,
        legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=11, color="#94a3b8"))
    )
    return fig


def chart_risk(data):
    sm = {"High": 3, "Medium": 2, "Low": 1}
    pm = {"High": 3, "Medium": 2, "Low": 1}
    cl = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}
    fig = go.Figure()
    # Zone shading
    fig.add_shape(type="rect", x0=2.5, y0=2.5, x1=3.5, y1=3.5,
                  fillcolor="rgba(239,68,68,0.05)", line=dict(color="rgba(239,68,68,0.18)", width=1, dash="dot"))
    fig.add_shape(type="rect", x0=0.5, y0=0.5, x1=1.5, y1=1.5,
                  fillcolor="rgba(16,185,129,0.05)", line=dict(color="rgba(16,185,129,0.18)", width=1, dash="dot"))
    fig.add_annotation(x=3.0, y=3.38, text="High Risk Zone", showarrow=False,
                       font=dict(size=10, color="rgba(239,68,68,0.45)"))
    fig.add_annotation(x=1.0, y=0.62, text="Safe Zone", showarrow=False,
                       font=dict(size=10, color="rgba(16,185,129,0.45)"))
    for r in data.get("risks", []):
        sev  = r.get("severity", "Medium"); prob = r.get("probability", "Medium")
        cat  = r.get("category", "");       mit  = r.get("mitigation", "")
        c    = cl.get(sev, "#f59e0b")
        fig.add_trace(go.Scatter(
            x=[pm.get(prob, 2)], y=[sm.get(sev, 2)], mode="markers+text",
            marker=dict(size=54, color=c, opacity=0.13, line=dict(color=c, width=2)),
            text=[cat], textposition="middle center", textfont=dict(size=10, color=c),
            hovertemplate=f"<b>{cat}</b><br>Severity: {sev}<br>Probability: {prob}<br><br>Mitigation: {mit}<extra></extra>",
            showlegend=False
        ))
    fig.update_layout(**LAYOUT,
        title=dict(text="Risk Assessment — Probability vs Severity", font=dict(size=14, color="#94a3b8"), x=0),
        height=440, showlegend=False,
        xaxis=dict(
            title=dict(text="Probability →", font=dict(size=12, color="#64748b")),
            tickvals=[1,2,3], ticktext=["Low","Medium","High"],
            tickfont=dict(size=12, color="#94a3b8"),
            gridcolor="rgba(255,255,255,0.05)", range=[0.3,3.7]
        ),
        yaxis=dict(
            title=dict(text="Severity →", font=dict(size=12, color="#64748b")),
            tickvals=[1,2,3], ticktext=["Low","Medium","High"],
            tickfont=dict(size=12, color="#94a3b8"),
            gridcolor="rgba(255,255,255,0.05)", range=[0.3,3.7]
        )
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# SHARED TOPBAR  (used by history sub-pages)
# ══════════════════════════════════════════════════════════════════════════════
def _render_topbar(user: dict) -> None:
    t1, t2, t3 = st.columns([5, 4, 1])
    with t1:
        st.markdown(
            '<div class="nav-logo">'
            '<span class="nav-logo-icon">🚀</span>'
            'Startup Blueprint Generator'
            '</div>',
            unsafe_allow_html=True,
        )
    with t2:
        st.markdown(
            '<div style="padding-top:0.35rem">'
            '<span class="badge badge-ibm">IBM Granite 4.0</span>'
            '<span class="badge badge-groq">Groq Llama 3.3</span>'
            '<span class="badge badge-gemini">✨ Gemini</span>'
            '<span class="badge badge-rag">CRAG</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with t3:
        if st.button("Sign Out", key="tb_signout", type="secondary"):
            for k in ["logged_in", "user", "page", "blueprints", "current_blueprint"]:
                st.session_state[k] = {
                    "logged_in": False, "user": None,
                    "page": "login", "blueprints": [],
                    "current_blueprint": None,
                }[k]
            st.session_state.mentor_session     = None
            st.session_state.mentor_messages_ui = []
            st.rerun()
    st.markdown('<hr>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════════════════════
def page_dashboard():
    user = st.session_state.user

    # ── History routing — full-page views short-circuit everything below ──────
    if st.session_state.hist_view_id is not None:
        _render_topbar(user)
        render_history_view(
            blueprint_id=st.session_state.hist_view_id,
            render_rewrite_card_fn=render_rewrite_card,
            render_policy_brief_fn=render_policy_brief,
            render_score_bars_fn=render_score_bars,
            render_explore_section_fn=render_explore_section,
            render_keyword_chips_fn=render_keyword_chips,
            chart_budget_fn=chart_budget,
            chart_budget_donut_fn=chart_budget_donut,
            chart_channels_fn=chart_channels,
            chart_timeline_fn=chart_timeline,
            chart_competitors_fn=chart_competitors,
            chart_risk_fn=chart_risk,
        )
        render_footer()
        st.stop()

    if st.session_state.hist_open:
        _render_topbar(user)
        render_history_page(user_email=user.get("email"))
        render_footer()
        st.stop()

    # ── Sticky Top Bar ────────────────────────────────────────────────────────
    nb1, nb2, nb3, nb4 = st.columns([5, 4, 1, 1])
    with nb1:
        st.markdown(
            '<div class="nav-logo">'
            '<span class="nav-logo-icon">🚀</span>'
            'Startup Blueprint Generator'
            '</div>',
            unsafe_allow_html=True
        )
    with nb2:
        st.markdown(
            '<div style="padding-top:0.35rem">'
            '<span class="badge badge-ibm">IBM Granite 4.0</span>'
            '<span class="badge badge-groq">Groq Llama 3.3</span>'
            '<span class="badge badge-gemini">✨ Gemini</span>'
            '<span class="badge badge-rag">CRAG</span>'
            '</div>',
            unsafe_allow_html=True
        )
    with nb3:
        if st.button("📚 History", key="hist_btn", type="secondary"):
            st.session_state.hist_open = True
            st.session_state.hist_view_id = None
            st.rerun()
    with nb4:
        if st.button("Sign Out", key="signout", type="secondary"):
            for k in ["logged_in", "user", "page", "blueprints", "current_blueprint"]:
                st.session_state[k] = {
                    "logged_in": False, "user": None, "page": "login",
                    "blueprints": [], "current_blueprint": None,
                }[k]
            st.session_state.mentor_session     = None
            st.session_state.mentor_messages_ui = []
            st.rerun()

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Welcome Row ───────────────────────────────────────────────────────────
    wc1, wc2 = st.columns([3, 1])
    with wc1:
        blueprints_count = user.get("blueprints_generated", 0)
        st.markdown(
            f'<div style="margin-bottom:1.4rem">'
            f'<div style="font-size:1.5rem;font-weight:800;color:#f1f5f9;letter-spacing:-0.025em">'
            f'Good to see you, {user["name"].split()[0]} 👋</div>'
            f'<div style="font-size:0.84rem;color:#475569;margin-top:0.3rem">'
            f'Member since {user.get("created_at","")[:10]} &nbsp;·&nbsp; '
            f'{blueprints_count} blueprint{"s" if blueprints_count != 1 else ""} generated</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with wc2:
        st.markdown(
            f'<div style="text-align:right;padding-top:0.5rem">'
            f'<span class="user-chip">👤 {user["email"]}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Idea Input ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">💡 Describe Your Startup Idea</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.8rem;color:#475569;margin-bottom:0.75rem">'
        'Be specific — include your target customers, technology, geography, and problem being solved. '
        'The more detail you provide, the richer the blueprint.'
        '</div>',
        unsafe_allow_html=True
    )
    idea = st.text_area(
        "", height=130, label_visibility="collapsed",
        placeholder=(
            "e.g. An AI-powered B2B SaaS platform for small textile exporters in Surat and Tirupur — "
            "automates buyer matching using NLP, generates compliance documents for EU market entry, "
            "and provides real-time fabric price benchmarking via supplier API integrations..."
        )
    )

    # ── Configuration ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">⚙️ Configuration</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sector = st.selectbox(
            "Sector",
            ["Fintech","Edtech","Agritech","Healthtech","E-commerce","SaaS",
             "Logistics","Food & Beverage","Clean Energy","Retail Tech","Other"]
        )
    with c2:
        model_type = st.radio("Business Model", ["B2B","B2C","B2B2C"], horizontal=True)
    with c3:
        stage = st.selectbox("Startup Stage", ["Idea Stage","Pre-seed","Seed","Series A"])
    with c4:
        target_city = st.selectbox(
            "Primary Market",
            ["Pan India","Mumbai","Delhi","Bangalore","Pune","Hyderabad","Chennai"]
        )

    # ── CRAG Settings ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🎛️ CRAG Settings</div>', unsafe_allow_html=True)
    o1, o2, _ = st.columns([1, 1, 2])
    with o1:
        show_crag_debug = st.toggle(
            "Show CRAG reasoning", value=True,
            help="Full pipeline trace — nodes, logits, action triggered"
        )
    with o2:
        detailed = st.toggle(
            "Detailed mode", value=True,
            help="Show extra context, raw outputs, and Granite policy brief"
        )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    generate = st.button("🚀  Generate My Blueprint", use_container_width=True, type="primary")

    # ── Recent Blueprints ─────────────────────────────────────────────────────
    if st.session_state.blueprints:
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">🕐 Recent Blueprints</div>', unsafe_allow_html=True)
        recent = list(reversed(st.session_state.blueprints[-3:]))
        cols   = st.columns(len(recent))
        for i, b in enumerate(recent):
            with cols[i]:
                st.markdown(
                    f'<div class="card" style="padding:0.8rem 1.1rem;cursor:default">'
                    f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.4rem">'
                    f'<span style="color:#3b82f6;font-size:0.68rem;font-weight:700;text-transform:uppercase;'
                    f'letter-spacing:0.06em">{b["sector"]}</span>'
                    f'<span style="color:#475569;font-size:0.68rem">{b["time"]}</span>'
                    f'</div>'
                    f'<div style="font-size:0.82rem;color:#cbd5e1;line-height:1.45">{b["idea"][:65]}…</div>'
                    f'<div style="font-size:0.7rem;color:#475569;margin-top:0.35rem">{b["model_type"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # ══════════════════════════════════════════════════════════════════════════
    # GENERATION
    # ══════════════════════════════════════════════════════════════════════════
    if generate:
        if not idea.strip():
            st.warning("Please describe your startup idea first.")
            st.stop()

        st.markdown('<hr>', unsafe_allow_html=True)

        # ── CRAG Pipeline ──────────────────────────────────────────────────────
        with st.status("🔍 Running CRAG — Corrective Retrieval pipeline…", expanded=True) as crag_status:
            st.write("**Node 1 · retrieve** — Dense vector search over ChromaDB (top-8 candidate chunks)…")
            st.write("**Node 2 · eval_each_doc** — CrossEncoder scoring each chunk (raw logits, not sigmoid)…")
            st.write("**Node 3 · rewrite_query** — Gemini Flash transforming rough idea into structured brief…")

            crag_result = run_crag(
                idea, sector, stage, model_type, target_city,
                embedder, reranker, collection, granite, tavily, groq_client, gemini
            )

            confidence  = crag_result["confidence"]
            action_text = crag_result["action"]

            if confidence == "CORRECT":
                st.write("**Node 4 · refine** — Sentence-pair strips re-scored, top-4 kept…")
                st.write("**Node 5 · generate** — IBM Granite 4.0 synthesizing policy brief from PDF knowledge…")
                st.write("**Node 6 · explore_search** — Tavily fetching 4 live web articles as bonus exploration…")
            elif confidence == "AMBIGUOUS":
                st.write("**Node 4 · web_search** — Tavily querying live web (inc42, startupindia, ET)…")
                st.write("**Node 5 · refine** — PDF strips + web results merged into combined context…")
                st.write("**Node 6 · generate** — IBM Granite 4.0 synthesizing from combined knowledge…")
            else:
                st.write("**Node 4 · web_search** — PDF corpus insufficient; Tavily searching live web…")
                st.write("**Node 5 · conversational_answer** — Groq generating plain answer from web context…")

            crag_status.update(label=f"✅ CRAG complete — {confidence}", state="complete")

        # ── Rewrite Card ──────────────────────────────────────────────────────
        render_rewrite_card(crag_result["rewritten_query"])

        # ── Keywords ──────────────────────────────────────────────────────────
        if crag_result.get("keywords"):
            st.markdown('<div class="section-label">🔑 Extracted Keywords</div>', unsafe_allow_html=True)
            render_keyword_chips(crag_result["keywords"])
            st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

        # ── CRAG Action Box ────────────────────────────────────────────────────
        if show_crag_debug:
            badge_cls = {
                "CORRECT":   "crag-action-correct",
                "AMBIGUOUS": "crag-action-ambiguous",
                "INCORRECT": "crag-action-incorrect"
            }.get(confidence, "")
            st.markdown(
                f'<div class="crag-action-box {badge_cls}">{action_text}</div>',
                unsafe_allow_html=True
            )

            with st.expander("🔬 CRAG Technical Details — logits & sources"):
                dc1, dc2 = st.columns(2)
                with dc1:
                    render_score_bars(crag_result.get("raw_logits", []))
                with dc2:
                    st.markdown('<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin-bottom:0.75rem">Sources used</div>', unsafe_allow_html=True)
                    for src in crag_result["sources"]:
                        icon = "🌐" if src == "tavily_web_search" else "📄"
                        st.markdown(
                            f'<div style="font-size:0.8rem;color:#94a3b8;padding:3px 0">'
                            f'{icon} <code style="font-size:0.73rem;color:#60a5fa;'
                            f'background:rgba(15,98,254,0.08);padding:2px 7px;border-radius:5px">'
                            f'{src}</code></div>',
                            unsafe_allow_html=True
                        )
                    if crag_result.get("retrieval_queries"):
                        st.markdown('<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin:0.75rem 0 0.5rem">Retrieval queries → Tavily</div>', unsafe_allow_html=True)
                        for q in crag_result["retrieval_queries"][:3]:
                            st.markdown(
                                f'<div style="font-size:0.77rem;color:#64748b;background:rgba(255,255,255,0.025);'
                                f'border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:0.4rem 0.65rem;'
                                f'margin-bottom:4px;line-height:1.5">{q}</div>',
                                unsafe_allow_html=True
                            )

        # ══════════════════════════════════════════════════════════════════════
        # INCORRECT PATH — no blueprint (nothing persisted; transient response)
        # ══════════════════════════════════════════════════════════════════════
        if not crag_result["should_generate_blueprint"]:
            conv = crag_result["conversational_response"]
            st.markdown('<hr>', unsafe_allow_html=True)

            if conv["type"] == "redirect":
                st.markdown(f"""<div class="card-amber">
<div style="font-size:1rem;font-weight:700;color:#f59e0b;margin-bottom:0.8rem">
  🤖 Let's refine your startup idea
</div>
<div style="color:#cbd5e1;font-size:0.88rem;line-height:1.9;white-space:pre-line">{conv["message"]}</div>
</div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="card-blue">
<div style="font-size:1rem;font-weight:700;color:#60a5fa;margin-bottom:0.8rem">
  💬 Quick Market Snapshot
</div>
<div style="color:#cbd5e1;font-size:0.88rem;line-height:1.9">{conv["message"]}</div>
<div style="margin-top:1rem;padding-top:0.8rem;border-top:1px solid rgba(255,255,255,0.06);
font-size:0.76rem;color:#475569">
  Add more detail about your sector, target customers, and business model to unlock a full blueprint.
</div>
</div>""", unsafe_allow_html=True)

            render_explore_section(crag_result.get("explore_results", []), confidence)
            st.stop()

        # ══════════════════════════════════════════════════════════════════════
        # CORRECT / AMBIGUOUS — full blueprint generation
        # ══════════════════════════════════════════════════════════════════════
        granite_summary = crag_result["summary"]
        sources         = crag_result["sources"]
        rewritten_query = crag_result["rewritten_query"]

        with st.status("⚡ Groq Llama 3.3 — Generating structured blueprint sections…", expanded=True) as groq_status:
            st.write("📋 Business Model Canvas…")
            bmc_data        = gen_bmc(rewritten_query, sector, model_type, granite_summary)
            st.write("💰 Budget estimation…")
            budget_data     = gen_budget(rewritten_query, sector, granite_summary)
            st.write("📣 Go-to-Market strategy…")
            gtm_data        = gen_gtm(rewritten_query, sector, model_type, granite_summary)
            st.write("🤝 Investors & government schemes…")
            investor_data   = gen_investors(rewritten_query, sector, granite_summary)
            st.write("🏆 Competitor analysis…")
            competitor_data = gen_competitors(rewritten_query, sector)
            st.write("⚠️ Risk assessment…")
            risk_data       = gen_risks(rewritten_query, sector)
            groq_status.update(label="✅ All 6 sections generated", state="complete")

        increment_blueprint_count(user["email"])
        st.session_state.blueprints.append({
            "idea": idea, "sector": sector, "model_type": model_type,
            "time": datetime.now().strftime("%H:%M")
        })

        # ── Auto-save to history ──────────────────────────────────────────────
        # Captures whatever identifier the history layer returns (if any) so it
        # can be carried inside current_blueprint for the mentor/history pages.
        saved_blueprint_id = hist.save_blueprint_to_history(
            idea=idea, sector=sector, stage=stage,
            business_model=model_type, market=target_city,
            user_email=user["email"],
            crag_result=crag_result,
            bmc_data=bmc_data, budget_data=budget_data,
            gtm_data=gtm_data, investor_data=investor_data,
            competitor_data=competitor_data, risk_data=risk_data,
            explore_results=crag_result.get("explore_results", []),
        )

        # ── Persist EVERYTHING into the single source of truth ─────────────────
        # From this point on, the dashboard renders exclusively from
        # st.session_state.current_blueprint — never from these local variables.
        st.session_state.current_blueprint = {
            "idea":              idea,
            "sector":            sector,
            "stage":             stage,
            "business_model":    model_type,
            "target_market":     target_city,
            "crag_result":       crag_result,
            "bmc_data":          bmc_data,
            "budget_data":       budget_data,
            "gtm_data":          gtm_data,
            "investor_data":     investor_data,
            "competitor_data":   competitor_data,
            "risk_data":         risk_data,
            "summary":           granite_summary,
            "sources":           sources,
            "rewritten_query":   rewritten_query,
            "confidence":        confidence,
            "action_text":       action_text,
            "user_email":        user["email"],
            "blueprint_id":      saved_blueprint_id,
        }

        # A freshly generated blueprint means a fresh mentor conversation.
        st.session_state.mentor_session     = None
        st.session_state.mentor_session_id  = None
        st.session_state.mentor_messages_ui = []
        st.session_state.mentor_input_key   = 0

    # ══════════════════════════════════════════════════════════════════════════
    # RENDER — always from session_state.current_blueprint (survives reruns)
    # ══════════════════════════════════════════════════════════════════════════
    if st.session_state.current_blueprint:
        render_blueprint_section(st.session_state.current_blueprint, show_crag_debug, detailed)


def render_blueprint_section(bp: dict, show_crag_debug: bool, detailed: bool):
    """Renders the full generated blueprint (overview, policy brief, 7 tabs,
    mentor CTA) purely from a saved blueprint dict — no dependency on any
    local variables from the generation step. Safe to call on every rerun."""

    crag_result      = bp["crag_result"]
    confidence        = bp["confidence"]
    action_text       = bp["action_text"]
    sources           = bp["sources"]
    granite_summary   = bp["summary"]
    idea              = bp["idea"]
    sector            = bp["sector"]
    model_type        = bp["business_model"]
    bmc_data          = bp["bmc_data"]
    budget_data       = bp["budget_data"]
    gtm_data          = bp["gtm_data"]
    investor_data     = bp["investor_data"]
    competitor_data   = bp["competitor_data"]
    risk_data         = bp["risk_data"]
    user              = st.session_state.user

    # ── Overview Metrics ──────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 Blueprint Overview</div>', unsafe_allow_html=True)
    m1, m2, m3, m4, m5 = st.columns(5)
    crag_badge_cls = {
        "CORRECT":   "badge-crag-correct",
        "AMBIGUOUS": "badge-crag-ambiguous"
    }.get(confidence, "badge-crag-incorrect")
    overview_cards = [
        (gtm_data.get("market_size", "—"),                     "Est. Market Size",  ""),
        (len(bmc_data.get("revenue_streams", [])),              "Revenue Streams",   ""),
        (f'₹{budget_data.get("total_12_months",0):,.0f}',      "12-Month Budget",   ""),
        (len(investor_data.get("government_schemes", [])),      "Govt Schemes",      "via CRAG RAG"),
        (confidence,                                            "CRAG Confidence",   ""),
    ]
    for col, (val, label, sub) in zip([m1,m2,m3,m4,m5], overview_cards):
        with col:
            sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value" style="font-size:{"1.4rem" if len(str(val))>6 else "1.85rem"}">{val}</div>'
                f'<div class="metric-label">{label}</div>{sub_html}'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f'<span class="badge badge-ibm">IBM Granite 4.0</span>'
        f'<span class="badge badge-groq">Groq Llama 3.3</span>'
        f'<span class="badge badge-gemini">✨ Gemini Flash</span>'
        f'<span class="badge {crag_badge_cls}">CRAG: {confidence}</span>'
        f'<span class="badge badge-live">🔴 Tavily Live</span>'
        f'&nbsp;&nbsp;<span style="color:#475569;font-size:0.72rem">'
        f'Sources: {", ".join(sources)}</span>',
        unsafe_allow_html=True
    )
    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Granite Policy Brief (always shown before tabs) ───────────────────
    if granite_summary and detailed:
        render_policy_brief(granite_summary)

    # ── 7 Tabs ─────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📋  Business Model", "💰  Budget", "📣  GTM",
        "🤝  Investors", "🏆  Competitors", "⚠️  Risks", "🔬  CRAG Pipeline"
    ])

    # ── Tab 1: Business Model Canvas ──────────────────────────────────────
    with tab1:
        st.markdown('<div class="section-header">Business Model Canvas — 9 Building Blocks</div>', unsafe_allow_html=True)
        bmc_map = [
            ("customer_segments",     "👥", "Customer Segments",      "#3b82f6"),
            ("value_propositions",    "💡", "Value Propositions",     "#8b5cf6"),
            ("channels",              "📢", "Channels",               "#10b981"),
            ("customer_relationships","🤝", "Customer Relationships", "#3b82f6"),
            ("revenue_streams",       "💰", "Revenue Streams",        "#8b5cf6"),
            ("key_resources",         "🔑", "Key Resources",          "#10b981"),
            ("key_activities",        "⚙️", "Key Activities",         "#3b82f6"),
            ("key_partners",          "🤲", "Key Partners",           "#8b5cf6"),
            ("cost_structure",        "💸", "Cost Structure",         "#10b981"),
        ]
        for row_slice in [bmc_map[:3], bmc_map[3:6], bmc_map[6:]]:
            cols = st.columns(3)
            for col, (key, icon, label, color) in zip(cols, row_slice):
                with col:
                    items = bmc_data.get(key, [])
                    items_html = "".join([
                        f'<div class="bmc-item">'
                        f'<span class="bmc-bullet">▸</span>'
                        f'<span>{i}</span>'
                        f'</div>'
                        for i in items
                    ])
                    no_data_html = (
                            '<div class="bmc-item">'
                            '<span style="color:#475569;font-style:italic;font-size:0.76rem">'
                            'No data generated</span></div>'
                        )
                    st.markdown(
                                f'<div class="bmc-block">'
                                f'<div class="bmc-icon">{icon}</div>'
                                f'<div class="bmc-label" style="color:{color}">{label}</div>'
                                f'{items_html if items_html else no_data_html}'
                                f'</div>',
                                unsafe_allow_html=True
                            )
            st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    # ── Tab 2: Budget ─────────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="section-header">Phase-wise Budget Estimate</div>', unsafe_allow_html=True)
        bc1, bc2 = st.columns([3, 2])
        with bc1:
            st.plotly_chart(chart_budget(budget_data), use_container_width=True)
        with bc2:
            st.plotly_chart(chart_budget_donut(budget_data), use_container_width=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        ph_cols = st.columns(len(budget_data.get("phases", [])) or 1)
        for col, phase in zip(ph_cols, budget_data.get("phases", [])):
            with col:
                items_html = "".join([
                    f'<div style="font-size:0.8rem;color:#94a3b8;padding:5px 0;'
                    f'border-bottom:1px solid rgba(255,255,255,0.04);'
                    f'display:flex;justify-content:space-between;align-items:center">'
                    f'<span>▸ {i["item"]}</span>'
                    f'<span style="color:#60a5fa;font-weight:600;font-family:\'JetBrains Mono\',monospace;font-size:0.77rem">'
                    f'₹{i["amount"]:,.0f}</span></div>'
                    for i in phase.get("items", [])
                ])
                st.markdown(
                    f'<div class="card">'
                    f'<div style="font-weight:800;color:#60a5fa;margin-bottom:0.2rem;font-size:0.95rem">{phase["name"]}</div>'
                    f'<div style="font-size:0.71rem;color:#475569;margin-bottom:0.7rem;text-transform:uppercase;'
                    f'letter-spacing:0.05em;font-weight:600">{phase["duration"]}</div>'
                    f'{items_html}'
                    f'<div style="font-weight:800;color:#34d399;margin-top:0.7rem;font-size:0.92rem;'
                    f'font-family:\'JetBrains Mono\',monospace">'
                    f'₹{phase["total"]:,.0f}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        st.info(f"💡 **Funding suggestion:** {budget_data.get('funding_suggestion','')}")
        st.success(f"**Total 12-Month Investment: ₹{budget_data.get('total_12_months',0):,.0f}**")

    # ── Tab 3: GTM ────────────────────────────────────────────────────────
    with tab3:
        st.markdown('<div class="section-header">Go-to-Market Strategy</div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            st.markdown(
                f'<div class="card-blue">'
                f'<div style="font-size:0.7rem;font-weight:700;color:#3b82f6;text-transform:uppercase;'
                f'letter-spacing:0.07em;margin-bottom:0.6rem">🎯 Target Market</div>'
                f'<div style="color:#cbd5e1;font-size:0.87rem;line-height:1.75">'
                f'{gtm_data.get("target_market","—")}</div>'
                f'<div style="margin-top:0.75rem;padding-top:0.65rem;border-top:1px solid rgba(15,98,254,0.15);'
                f'font-size:0.7rem;font-weight:700;color:#3b82f6;text-transform:uppercase;letter-spacing:0.07em">'
                f'📈 Est. Market Size</div>'
                f'<div style="font-size:1.3rem;font-weight:900;color:#60a5fa;margin-top:0.25rem;letter-spacing:-0.02em">'
                f'{gtm_data.get("market_size","—")}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;'
                'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.6rem">'
                '📊 Key Metrics to Track</div>',
                unsafe_allow_html=True
            )
            for m in gtm_data.get("key_metrics", []):
                st.markdown(
                    f'<div style="font-size:0.83rem;color:#94a3b8;padding:6px 0;'
                    f'border-bottom:1px solid rgba(255,255,255,0.04);display:flex;align-items:center;gap:7px">'
                    f'<span style="color:#3b82f6;font-size:0.7rem">◆</span> {m}</div>',
                    unsafe_allow_html=True
                )

        with g2:
            st.markdown(
                '<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;'
                'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.7rem">'
                '🚀 Launch Strategy</div>',
                unsafe_allow_html=True
            )
            for i, step in enumerate(gtm_data.get("launch_strategy", []), 1):
                st.markdown(
                    f'<div class="card" style="padding:0.7rem 1rem;margin-bottom:0.5rem;'
                    f'border-left:3px solid #3b82f6">'
                    f'<span style="color:#3b82f6;font-weight:800;font-size:0.72rem;'
                    f'text-transform:uppercase;letter-spacing:0.05em">Step {i}</span>'
                    f'<div style="font-size:0.85rem;color:#cbd5e1;margin-top:0.3rem;line-height:1.5">{step}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        st.plotly_chart(chart_channels(gtm_data.get("growth_channels", [])), use_container_width=True)
        st.caption("Each bar shows channel priority — longer = higher priority. Focus on blue (High) channels first.")

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        st.plotly_chart(chart_timeline(gtm_data.get("milestones", [])), use_container_width=True)
        st.caption("Hover any milestone dot to see the full goal description.")

        # Explore section
        render_explore_section(crag_result.get("explore_results", []), confidence)

    # ── Tab 4: Investors ──────────────────────────────────────────────────
    with tab4:
        st.markdown('<div class="section-header">Investors & Government Schemes</div>', unsafe_allow_html=True)

        # Government Schemes
        schemes = investor_data.get("government_schemes", [])
        st.markdown(
            f'<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;'
            f'letter-spacing:0.06em;margin-bottom:0.8rem">'
            f'🏛️ Government Schemes — retrieved via CRAG '
            f'<span style="color:#60a5fa">({confidence.lower()} confidence)</span></div>',
            unsafe_allow_html=True
        )
        sc_cols = st.columns(min(len(schemes), 3) or 1)
        for i, s in enumerate(schemes):
            with sc_cols[i % len(sc_cols)]:
                st.markdown(
                    f'<div class="card">'
                    f'<div style="font-weight:700;color:#60a5fa;margin-bottom:0.55rem;font-size:0.9rem">'
                    f'📜 {s.get("name","")}</div>'
                    f'<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.4rem;line-height:1.55">'
                    f'<span style="color:#e2e8f0;font-weight:600">Benefit:</span> {s.get("benefit","")}</div>'
                    f'<div style="font-size:0.8rem;color:#94a3b8;line-height:1.55">'
                    f'<span style="color:#e2e8f0;font-weight:600">Eligibility:</span> {s.get("eligibility","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown('<hr>', unsafe_allow_html=True)

        # Investor types + Incubators
        i1, i2 = st.columns(2)
        with i1:
            st.markdown(
                '<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.06em;margin-bottom:0.7rem">💼 Investor Types</div>',
                unsafe_allow_html=True
            )
            for inv in investor_data.get("investor_types", []):
                st.markdown(
                    f'<div class="card" style="padding:0.7rem 1rem">'
                    f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.3rem">'
                    f'<span style="color:#a78bfa;font-weight:700">{inv.get("type","")}</span>'
                    f'<span style="font-size:0.7rem;background:rgba(105,41,196,0.1);color:#a78bfa;'
                    f'padding:2px 9px;border-radius:8px;border:1px solid rgba(105,41,196,0.2)">{inv.get("stage","")}</span>'
                    f'</div>'
                    f'<div style="font-size:0.77rem;color:#64748b">{", ".join(inv.get("examples",[]))}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        with i2:
            st.markdown(
                '<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.06em;margin-bottom:0.7rem">🏢 Incubators & Accelerators</div>',
                unsafe_allow_html=True
            )
            for inc in investor_data.get("incubators", []):
                st.markdown(
                    f'<div class="card" style="padding:0.7rem 1rem">'
                    f'<div style="font-weight:700;color:#34d399;margin-bottom:0.2rem">{inc.get("name","")}</div>'
                    f'<div style="font-size:0.76rem;color:#64748b">'
                    f'📍 {inc.get("location","")} &nbsp;·&nbsp; 🎯 {inc.get("focus","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown('<hr>', unsafe_allow_html=True)

        # Funding Roadmap
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;'
            'letter-spacing:0.06em;margin-bottom:0.9rem">🗺️ Funding Roadmap</div>',
            unsafe_allow_html=True
        )
        roadmap = investor_data.get("funding_roadmap", [])
        rm_cols = st.columns(len(roadmap) or 1)
        for i, stg in enumerate(roadmap):
            with rm_cols[i]:
                st.markdown(
                    f'<div class="funding-stage">'
                    f'<div class="funding-stage-name">{stg.get("stage","")}</div>'
                    f'<div class="funding-stage-amount">{stg.get("amount","")}</div>'
                    f'<div class="funding-stage-time">{stg.get("timeline","")}</div>'
                    f'<div class="funding-stage-src">{stg.get("source","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;'
            'letter-spacing:0.06em;margin-bottom:0.6rem">💬 Pitch Tips</div>',
            unsafe_allow_html=True
        )
        for tip in investor_data.get("pitch_tips", []):
            st.success(f"💡 {tip}")

    # ── Tab 5: Competitors ────────────────────────────────────────────────
    with tab5:
        st.markdown('<div class="section-header">Competitive Landscape</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns([2, 3])
        with cc1:
            st.plotly_chart(chart_competitors(competitor_data), use_container_width=True)
        with cc2:
            st.markdown(
                '<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.06em;margin-bottom:0.7rem">⚔️ Competitor Breakdown</div>',
                unsafe_allow_html=True
            )
            for comp in competitor_data.get("competitors", []):
                is_us  = comp.get("name","") == "Our Startup"
                border = "border-left:3px solid #3b82f6" if is_us else ""
                nc     = "#60a5fa" if is_us else "#e2e8f0"
                badge_bg = "rgba(15,98,254,0.12)" if is_us else "rgba(255,255,255,0.06)"
                badge_c  = "#93c5fd" if is_us else "#94a3b8"
                st.markdown(
                    f'<div class="card" style="{border}">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.45rem">'
                    f'<span style="font-weight:700;color:{nc};font-size:0.92rem">{comp.get("name","")}</span>'
                    f'<span style="background:{badge_bg};color:{badge_c};padding:3px 10px;'
                    f'border-radius:10px;font-size:0.71rem;font-weight:700">'
                    f'{comp.get("market_share",0)}% share</span>'
                    f'</div>'
                    f'<div style="font-size:0.8rem;color:#94a3b8;display:flex;align-items:flex-start;gap:5px">'
                    f'<span style="color:#34d399">✓</span> {comp.get("strength","")}</div>'
                    f'<div style="font-size:0.8rem;color:#94a3b8;margin-top:0.2rem;display:flex;align-items:flex-start;gap:5px">'
                    f'<span style="color:#f87171">✗</span> {comp.get("weakness","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown('<hr>', unsafe_allow_html=True)
        diff_col, gap_col = st.columns(2)
        with diff_col:
            st.markdown(
                '<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.06em;margin-bottom:0.7rem">🌟 Our Differentiators</div>',
                unsafe_allow_html=True
            )
            for d in competitor_data.get("our_differentiators", []):
                st.markdown(
                    f'<div class="card-green" style="padding:0.65rem 1rem;margin-bottom:0.5rem">'
                    f'<span style="color:#34d399;font-weight:600;font-size:0.84rem">⭐ {d}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        with gap_col:
            st.markdown(
                '<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.06em;margin-bottom:0.7rem">🔍 Market Gaps to Exploit</div>',
                unsafe_allow_html=True
            )
            for g in competitor_data.get("market_gaps", []):
                st.markdown(
                    f'<div class="card-blue" style="padding:0.65rem 1rem;margin-bottom:0.5rem">'
                    f'<span style="color:#60a5fa;font-weight:600;font-size:0.84rem">💎 {g}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # ── Tab 6: Risks ──────────────────────────────────────────────────────
    with tab6:
        st.markdown('<div class="section-header">Risk Assessment Matrix</div>', unsafe_allow_html=True)
        st.plotly_chart(chart_risk(risk_data), use_container_width=True)
        st.caption("Each bubble represents a risk — X axis = probability, Y axis = severity. Hover for mitigation strategy.")
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        rc1, rc2 = st.columns(2)
        for i, risk in enumerate(risk_data.get("risks", [])):
            sev   = risk.get("severity", "Medium")
            emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(sev, "🟡")
            col   = rc1 if i % 2 == 0 else rc2
            with col:
                st.markdown(
                    f'<div class="card">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">'
                    f'<span style="font-weight:700;color:#e2e8f0;font-size:0.9rem">{emoji} {risk.get("category","")}</span>'
                    f'<span class="risk-{sev.lower()}">{sev}</span>'
                    f'</div>'
                    f'<div style="font-size:0.83rem;color:#94a3b8;margin-bottom:0.5rem;line-height:1.55">'
                    f'{risk.get("risk","")}</div>'
                    f'<div style="font-size:0.78rem;background:rgba(52,211,153,0.05);'
                    f'border:1px solid rgba(52,211,153,0.13);border-radius:10px;'
                    f'padding:0.5rem 0.7rem;color:#34d399;line-height:1.55">'
                    f'🛡️ {risk.get("mitigation","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # ── Tab 7: CRAG Pipeline ──────────────────────────────────────────────
    with tab7:
        st.markdown('<div class="section-header">CRAG — Pipeline Trace</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.8rem;color:#475569;margin-bottom:1.4rem;font-style:italic">'
            'Yan et al. 2024 (arXiv:2401.15884) — adapted with CrossEncoder evaluator + Gemini Flash rewriter</div>',
            unsafe_allow_html=True
        )

        nodes_always = [
            ("✅", "Node 1 · retrieve", "done",
             f"ChromaDB returned top-8 chunks via dense embedding (all-MiniLM-L6-v2). "
             f"Sources: {', '.join([s for s in crag_result['sources'] if s != 'tavily_web_search']) or 'PDF corpus'}."),
            ("✅", "Node 2 · eval_each_doc", "done",
             f"CrossEncoder (ms-marco-MiniLM-L-6-v2) scored all 8 chunks. "
             f"Max logit: {max(crag_result['raw_logits']):.2f}. "
             f"Confidence → <b style='color:#60a5fa'>{confidence}</b>."),
            ("✅", "Node 3 · rewrite_query (Gemini Flash)", "done",
             "Rough founder idea converted to 10-field structured brief: Problem Statement, Target Users, "
             "Core Solution, Key Features, Technologies, Industry, Geography, Business Model, "
             "Analysis Requested, Search Context."),
        ]
        if confidence == "CORRECT":
            nodes_branch = [
                ("✅", "Node 4 · refine — PDF only", "done",
                 "Relevant docs split into sentence-pair strips, re-scored by CrossEncoder, top-4 kept. "
                 "Internal knowledge is sufficient — Tavily not used for blueprint context."),
                ("✅", "Node 5 · generate (IBM Granite 4.0)", "done",
                 "Granite synthesized a startup policy brief from refined PDF strips only."),
                ("✅", f"Node 6 · explore_search (Tavily) — {len(crag_result.get('explore_results',[]))} articles", "done",
                 "Live web search results shown as bonus exploration — NOT fed into blueprint generation."),
            ]
        elif confidence == "AMBIGUOUS":
            nodes_branch = [
                ("✅", f"Node 4 · web_search (Tavily) — {len(crag_result.get('explore_results',[]))} results", "done",
                 "Rewritten retrieval queries sent to Tavily for live web augmentation."),
                ("✅", "Node 5 · refine — PDF + web combined", "done",
                 "PDF sentence strips and Tavily web snippets merged into combined context for Granite."),
                ("✅", "Node 6 · generate (IBM Granite 4.0)", "done",
                 "Granite synthesized policy brief from combined internal + external knowledge."),
            ]
        else:
            nodes_branch = [
                ("✅", f"Node 4 · web_search (Tavily) — {len(crag_result.get('explore_results',[]))} results", "done",
                 "Internal knowledge base is insufficient. Live web search used as primary source."),
                ("✅", "Node 5 · conversational_answer (Groq)", "done",
                 "Groq Llama 3.3 generated a plain market snapshot — no blueprint produced."),
            ]

        for idx, (icon, title, cls, desc) in enumerate(nodes_always + nodes_branch):
            st.markdown(
                f'<div class="crag-node {cls}">'
                f'<div class="crag-icon">{icon}</div>'
                f'<div class="crag-body">'
                f'<div class="crag-title">{title}</div>'
                f'<div class="crag-desc">{desc}</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )
            # Draw connector between nodes (not after last)
            total_nodes = len(nodes_always) + len(nodes_branch)
            if idx < total_nodes - 1:
                st.markdown('<div class="crag-connector"></div>', unsafe_allow_html=True)

        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
        badge_cls = {
            "CORRECT":   "crag-action-correct",
            "AMBIGUOUS": "crag-action-ambiguous",
            "INCORRECT": "crag-action-incorrect"
        }.get(confidence, "")
        st.markdown(
            f'<div class="crag-action-box {badge_cls}">'
            f'Action triggered: <b>{confidence}</b><br>'
            f'<span style="font-weight:400;font-size:0.83rem">{action_text}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        if detailed:
            st.markdown('<hr>', unsafe_allow_html=True)
            pc1, pc2 = st.columns(2)
            with pc1:
                st.markdown(
                    '<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;'
                    'letter-spacing:0.06em;margin-bottom:0.6rem">📄 Internal Knowledge (PDF strips)</div>',
                    unsafe_allow_html=True
                )
                if crag_result.get("internal_context"):
                    st.markdown(
                        f'<div class="card"><p style="color:#94a3b8;font-size:0.8rem;line-height:1.7;margin:0">'
                        f'{crag_result["internal_context"][:1000]}…</p></div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.info("Not used — INCORRECT confidence; internal docs discarded.")
            with pc2:
                st.markdown(
                    '<div style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;'
                    'letter-spacing:0.06em;margin-bottom:0.6rem">🌐 External Knowledge (Tavily)</div>',
                    unsafe_allow_html=True
                )
                if crag_result.get("external_context"):
                    st.markdown(
                        f'<div class="card"><p style="color:#94a3b8;font-size:0.8rem;line-height:1.7;margin:0">'
                        f'{crag_result["external_context"][:1000]}…</p></div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.info("Not used — CORRECT confidence; PDF-only was sufficient.")

        with st.expander("ℹ️ How CRAG works in this app"):
            st.markdown("""
**Node 1 · retrieve** — ChromaDB returns top-8 candidate chunks using dense vector search (all-MiniLM-L6-v2 embeddings over 13 Indian policy PDFs).

**Node 2 · eval_each_doc** — CrossEncoder (ms-marco-MiniLM-L-6-v2) scores each chunk. We threshold on raw logits (not sigmoid) because this corpus produces logits in the −10 to 0 range — sigmoid collapses all values near 0 and loses the signal.

**Thresholds:** CORRECT ≥ −3.0 · INCORRECT < −6.5 · AMBIGUOUS: between

**Node 3 · rewrite_query (Gemini Flash)** — The rough founder idea is expanded into a 10-field structured brief used for ALL downstream steps: Tavily search queries, Granite summarisation, and all 6 Groq blueprint sections.

**CORRECT branch** — PDF context is strong. Refine (sentence-pair strip re-scoring) → Granite summary → Blueprint. Tavily used for bonus explore section only.

**AMBIGUOUS branch** — Partial relevance. PDF strips + Tavily results merged → Granite summary from combined context → Blueprint.

**INCORRECT branch** — PDF corpus insufficient. Tavily web search → Groq conversational answer. No blueprint generated.
""")

    # ── 🧠 AI Mentor CTA — shown at the end of every full blueprint ─────────
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown("""
<div style="background:linear-gradient(135deg,rgba(15,98,254,0.1) 0%,rgba(105,41,196,0.08) 100%);
border:1px solid rgba(15,98,254,0.22);border-radius:20px;padding:1.6rem 2rem;
display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap">
  <div>
    <div style="font-size:1.05rem;font-weight:800;color:#f1f5f9;letter-spacing:-0.02em;margin-bottom:0.3rem">
      🧠 Ready to go deeper? Explore with AI Mentor
    </div>
    <div style="font-size:0.82rem;color:#64748b;line-height:1.6;max-width:520px">
      Your blueprint is now the mentor's working memory. Ask anything — feasibility,
      competitors, funding, execution roadmap, investor prep. Every answer is cited
      and grounded in your data.
    </div>
    <div style="margin-top:0.6rem">
      <span style="background:rgba(15,98,254,0.1);border:1px solid rgba(15,98,254,0.2);
      color:#60a5fa;padding:2px 11px;border-radius:12px;font-size:0.7rem;font-weight:700;margin-right:5px">
      IBM Granite 4.0 Answers</span>
      <span style="background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.18);
      color:#34d399;padding:2px 11px;border-radius:12px;font-size:0.7rem;font-weight:700;margin-right:5px">
      14 Intent Types</span>
      <span style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.18);
      color:#f59e0b;padding:2px 11px;border-radius:12px;font-size:0.7rem;font-weight:700">
      Never Hallucinate</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    if st.button(
        "🧠  Explore with AI Mentor →",
        key="open_mentor",
        type="primary",
        use_container_width=True,
    ):
        # current_blueprint is already the single source of truth — saved once,
        # right after generation. Nothing to rebuild here; just navigate.
        st.session_state.page = "mentor"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
def render_footer():
    st.markdown("""
<div style="margin-top:4rem;padding-top:1.5rem;border-top:1px solid rgba(255,255,255,0.055);
text-align:center;color:#334155;font-size:0.75rem;line-height:1.8">
  <div style="margin-bottom:0.3rem">
    <span style="color:#475569;font-weight:600">Startup Blueprint Generator</span>
    &nbsp;·&nbsp; IBM Granite 4.0 &nbsp;·&nbsp; Groq Llama 3.3 &nbsp;·&nbsp;
    Gemini Flash &nbsp;·&nbsp; CRAG (Yan et al. 2024)
  </div>
  <div>
    Built for the Indian startup ecosystem &nbsp;·&nbsp;
    <span style="color:#334155">Powered by ChromaDB · Tavily · SentenceTransformers</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
# Handle OAuth callback first (App ID redirect)
params = st.query_params
if "code" in params:
    from auth import exchange_code_for_tokens, get_user_profile, set_session
    with st.spinner("Signing you in..."):
        tokens = exchange_code_for_tokens(params["code"])
        if tokens:
            profile = get_user_profile(tokens["access_token"])
            set_session(profile)
            st.session_state.logged_in = True
            st.session_state.user = {
                "name":                 profile.get("name", profile.get("email", "User")),
                "email":                profile.get("email", ""),
                "blueprints_generated": 0,
                "created_at":           "",
            }
            st.session_state.page = "dashboard"
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Login failed. Please try again.")
            st.query_params.clear()

if not st.session_state.logged_in:
    page_auth()
elif st.session_state.page == "mentor":
    bp = st.session_state.get("current_blueprint")
    if bp is None:
        # Edge case: mentor page without blueprint data — fall back to dashboard
        st.session_state.page = "dashboard"
        st.rerun()
    else:
        render_mentor_page(
            idea=bp["idea"],
            sector=bp["sector"],
            stage=bp["stage"],
            business_model=bp["business_model"],
            market=bp["target_market"],
            crag_result=bp["crag_result"],
            bmc_data=bp["bmc_data"],
            budget_data=bp["budget_data"],
            gtm_data=bp["gtm_data"],
            investor_data=bp["investor_data"],
            competitor_data=bp["competitor_data"],
            risk_data=bp["risk_data"],
            blueprint_id=bp.get("blueprint_id"),
            user_email=bp.get("user_email", ""),
            groq_client=groq_client,
            granite_client=granite,
            embedder=embedder,
            collection=collection,
            tavily_client=tavily,
        )
else:
    page_dashboard()

render_footer()