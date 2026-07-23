"""
deep_research.py — Startup Intelligence Report engine.
Runs 5 parallel research agents on a saved blueprint and caches to Supabase.
"""

from __future__ import annotations
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _groq_json(groq_client, system: str, user: str, model="llama-3.3-70b-versatile") -> dict:
    """Call Groq and return parsed JSON. Retries up to 3 times on failure."""
    for attempt in range(3):
        try:
            resp = groq_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content.strip()
            return json.loads(raw)
        except Exception as e:
            if attempt == 2:
                print(f"[deep_research] Groq call failed after 3 attempts: {e}")
                return {}
            time.sleep(1)
    return {}


def _tavily_search(tavily, query: str, max_results=5) -> list[dict]:
    """Run a single Tavily search and return cleaned results."""
    try:
        results = tavily.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_domains=[
                "inc42.com", "yourstory.com", "economictimes.indiatimes.com",
                "entrackr.com", "techcrunch.com", "startupindia.gov.in",
                "msme.gov.in", "investindia.gov.in", "moneycontrol.com",
                "livemint.com",
            ],
        )
        return [
            {
                "title":   r.get("title", ""),
                "content": r.get("content", "")[:600],
                "url":     r.get("url", ""),
                "score":   r.get("score", 0),
            }
            for r in results.get("results", [])
        ]
    except Exception as e:
        print(f"[deep_research] Tavily search failed: {e}")
        return []


def _format_web_context(results: list[dict]) -> str:
    return "\n\n".join(
        f"[{r['title']}]\n{r['content']}"
        for r in results
        if r.get("content")
    )


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — COMPETITOR LANDSCAPE
# ══════════════════════════════════════════════════════════════════════════════

def get_competitors(blueprint: dict, groq_client, tavily) -> dict:
    idea   = blueprint.get("original_query", "")
    sector = blueprint.get("sector", "startup")
    
    print(f"[DEBUG] get_competitors called with idea={idea[:50]}, sector={sector}")  # ← ADD
    
    query  = f"top competitors {sector} startups India 2024 2025"
    results = _tavily_search(tavily, query, max_results=6)
    
    print(f"[DEBUG] Tavily returned {len(results)} results")  # ← ADD
    
    web_ctx = _format_web_context(results)
    # ... rest stays same
    
    result = _groq_json(groq_client, system, user)
    print(f"[DEBUG competitors] Full result: {result}")  # ← ADD THIS
    print(f"[DEBUG competitors] Keys: {list(result.keys())}")  # ← ADD THIS
    return result


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2 — LIVE NEWS PULSE
# ══════════════════════════════════════════════════════════════════════════════

def get_news_pulse(blueprint: dict, groq_client, tavily) -> dict:
    """
    Returns:
    {
        "headlines": [{"title": str, "summary": str, "url": str}],
        "sentiment": "Hot" | "Neutral" | "Cold",
        "sentiment_reason": str,
        "market_signal": str
    }
    """
    sector = blueprint.get("sector", "startup")
    idea   = blueprint.get("original_query", "")

    query   = f"{sector} startup India news funding 2025"
    results = _tavily_search(tavily, query, max_results=7)
    web_ctx = _format_web_context(results)

    # Build headline list for context
    raw_headlines = [
        {"title": r["title"], "url": r["url"]}
        for r in results if r.get("title")
    ]

    system = """You are a startup market analyst tracking the Indian startup ecosystem.
Respond ONLY with valid JSON matching this exact schema:
{
  "headlines": [
    {
      "title": "string",
      "summary": "string (1-2 sentence summary of why this matters)",
      "url": "string"
    }
  ],
  "sentiment": "Hot",
  "sentiment_reason": "string (one sentence explaining the sentiment)",
  "market_signal": "string (2-3 sentences on what this means for the user's startup)"
}
sentiment must be exactly one of: Hot, Neutral, Cold.
Pick 4-5 most relevant headlines. No extra keys."""

    user = f"""Startup idea: {idea}
Sector: {sector}
Raw headlines found: {json.dumps(raw_headlines)}
Web context:\n{web_ctx}

Summarize the market pulse for this sector."""

    return _groq_json(groq_client, system, user)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 3 — SWOT + RISK ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def get_swot(blueprint: dict, groq_client) -> dict:
    """
    Returns:
    {
        "strengths": [str],
        "weaknesses": [str],
        "opportunities": [str],
        "threats": [str],
        "sector_risks": [{"risk": str, "severity": "High"|"Medium"|"Low", "mitigation": str}]
    }
    """
    idea    = blueprint.get("original_query", "")
    sector  = blueprint.get("sector", "startup")
    stage   = blueprint.get("stage", "")
    market  = blueprint.get("market", "")
    summary = blueprint.get("summary", "")

    # Sector-specific risk hints
    sector_risk_hints = {
        "fintech":   "RBI regulations, NBFC licensing, UPI competition from incumbents",
        "healthtech":"CDSCO approvals, patient data privacy (DPDP Act), doctor adoption",
        "edtech":    "NEP 2020 compliance, high CAC, retention after free trial",
        "agritech":  "farmer digitization, last-mile connectivity, monsoon dependency",
        "saas":      "enterprise sales cycles, data residency laws, churn management",
        "ecommerce": "logistics costs, GST compliance, marketplace competition",
        "logistics": "fuel price volatility, driver retention, hyperlocal competition",
    }
    risk_hint = sector_risk_hints.get(sector.lower(), "regulatory compliance, funding environment")

    system = """You are a startup strategy consultant for the Indian market.
Respond ONLY with valid JSON matching this exact schema:
{
  "strengths": ["string", "string", "string"],
  "weaknesses": ["string", "string", "string"],
  "opportunities": ["string", "string", "string"],
  "threats": ["string", "string", "string"],
  "sector_risks": [
    {
      "risk": "string",
      "severity": "High",
      "mitigation": "string (one concrete action)"
    }
  ]
}
Each array must have 3-4 items. sector_risks must have 3-5 items.
severity must be exactly one of: High, Medium, Low. No extra keys."""

    user = f"""Startup idea: {idea}
Sector: {sector}
Stage: {stage}
Target market: {market}
Blueprint summary: {summary}
Known sector risks to consider: {risk_hint}

Generate a detailed SWOT analysis and sector-specific risk assessment."""

    return _groq_json(groq_client, system, user)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 4 — MARKET SIZING (TAM / SAM / SOM)
# ══════════════════════════════════════════════════════════════════════════════

def get_market_sizing(blueprint: dict, groq_client, tavily) -> dict:
    """
    Returns:
    {
        "tam": {"value": str, "description": str},
        "sam": {"value": str, "description": str},
        "som": {"value": str, "description": str},
        "cagr": str,
        "narrative": str,
        "key_assumptions": [str]
    }
    """
    idea   = blueprint.get("original_query", "")
    sector = blueprint.get("sector", "startup")
    market = blueprint.get("market", "India")

    query   = f"{sector} market size India TAM 2024 2025 billion"
    results = _tavily_search(tavily, query, max_results=5)
    web_ctx = _format_web_context(results)

    system = """You are a market research analyst specializing in Indian startup sectors.
Respond ONLY with valid JSON matching this exact schema:
{
  "tam": {
    "value": "string (e.g. $12B)",
    "description": "string (what this represents)"
  },
  "sam": {
    "value": "string (e.g. $3B)",
    "description": "string (serviceable segment)"
  },
  "som": {
    "value": "string (e.g. $150M)",
    "description": "string (realistic capture in 3 years)"
  },
  "cagr": "string (e.g. 18% CAGR through 2028)",
  "narrative": "string (3-4 sentences on market opportunity)",
  "key_assumptions": ["string", "string", "string"]
}
Use Indian market data. Values should be realistic estimates. No extra keys."""

    user = f"""Startup idea: {idea}
Sector: {sector}
Target market: {market}
Web research on market size:\n{web_ctx}

Calculate TAM, SAM, SOM for this startup in the Indian market."""

    return _groq_json(groq_client, system, user)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 5 — FUNDING PATHWAY
# ══════════════════════════════════════════════════════════════════════════════

def get_funding_pathway(blueprint: dict, groq_client) -> dict:
    """
    Returns:
    {
        "current_stage_advice": str,
        "schemes": [
            {"name": str, "type": str, "amount": str, "eligibility": str, "url": str}
        ],
        "investor_types": [str],
        "pitch_readiness_score": int (0-100),
        "pitch_readiness_tips": [str],
        "roadmap": [
            {"phase": str, "timeline": str, "action": str}
        ]
    }
    """
    idea   = blueprint.get("original_query", "")
    sector = blueprint.get("sector", "startup")
    stage  = blueprint.get("stage", "idea")

    # Static knowledge of Indian funding schemes (no web search needed)
    schemes_context = """
Indian Funding Schemes:
- Startup India Seed Fund: Up to ₹20L for early-stage, DPIIT registered
- SIDBI Fund of Funds: Via VC funds, for growth-stage startups
- Atal Innovation Mission (AIM): Grants for deep-tech/innovation
- iCreate: Technology startups, up to ₹50L
- NIDHI Prayas: PoC grants up to ₹10L for DPIIT startups
- Kerala Startup Mission, T-Hub, NASSCOM 10000 Startups (accelerators)
- Angel networks: Indian Angel Network, Mumbai Angels, LetsVenture
- YC, Sequoia Surge for exceptional startups
"""

    system = """You are a startup funding advisor for the Indian ecosystem.
Respond ONLY with valid JSON matching this exact schema:
{
  "current_stage_advice": "string (2-3 sentences on what funding stage this startup is at)",
  "schemes": [
    {
      "name": "string",
      "type": "string (Grant / Equity / Debt / Accelerator)",
      "amount": "string (e.g. Up to ₹20L)",
      "eligibility": "string (key requirement)",
      "url": "string (official URL or empty string)"
    }
  ],
  "investor_types": ["string", "string", "string"],
  "pitch_readiness_score": 65,
  "pitch_readiness_tips": ["string", "string", "string"],
  "roadmap": [
    {
      "phase": "string (e.g. Phase 1: Validate)",
      "timeline": "string (e.g. Month 1-3)",
      "action": "string"
    }
  ]
}
List 3-5 schemes. pitch_readiness_score is an integer 0-100. roadmap has 3 phases. No extra keys."""

    user = f"""Startup idea: {idea}
Sector: {sector}
Current stage: {stage}
{schemes_context}

Recommend the best funding pathway for this startup."""

    return _groq_json(groq_client, system, user)


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR — Run all 5 agents in parallel
# ══════════════════════════════════════════════════════════════════════════════

def run_deep_research(blueprint: dict, groq_client, tavily) -> dict:
    """
    Runs all 5 research agents in parallel using ThreadPoolExecutor.
    Returns a unified result dict.
    """
    results = {
        "competitors":   {},
        "news_pulse":    {},
        "swot":          {},
        "market_sizing": {},
        "funding":       {},
        "error":         None,
    }

    tasks = {
        "competitors":   lambda: get_competitors(blueprint, groq_client, tavily),
        "news_pulse":    lambda: get_news_pulse(blueprint, groq_client, tavily),
        "swot":          lambda: get_swot(blueprint, groq_client),
        "market_sizing": lambda: get_market_sizing(blueprint, groq_client, tavily),
        "funding":       lambda: get_funding_pathway(blueprint, groq_client),
    }

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fn): key for key, fn in tasks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                print(f"[deep_research] Agent '{key}' failed: {e}")
                results[key] = {}

    return results


# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE CACHE — Save & Load
# ══════════════════════════════════════════════════════════════════════════════

def save_deep_research(supabase_client, blueprint_id: int, user_id: str, data: dict) -> bool:
    """Cache deep research results in Supabase."""
    try:
        supabase_client.table("deep_research").upsert({
            "blueprint_id":    blueprint_id,
            "user_id":         user_id,
            "competitor_data": data.get("competitors", {}),
            "market_sizing":   data.get("market_sizing", {}),
            "swot":            data.get("swot", {}),
            "funding":         data.get("funding", {}),
            "news_pulse":      data.get("news_pulse", {}),
            "sentiment":       data.get("news_pulse", {}).get("sentiment", "Neutral"),
        }, on_conflict="blueprint_id").execute()
        return True
    except Exception as e:
        print(f"[deep_research] Supabase save failed: {e}")
        return False


def load_deep_research(supabase_client, blueprint_id: int) -> dict | None:
    """Load cached deep research from Supabase. Returns None if not found."""
    try:
        resp = (
            supabase_client.table("deep_research")
            .select("*")
            .eq("blueprint_id", blueprint_id)
            .limit(1)
            .execute()
        )
        if resp.data:
            row = resp.data[0]
            return {
                "competitors":   row.get("competitor_data", {}),
                "market_sizing": row.get("market_sizing", {}),
                "swot":          row.get("swot", {}),
                "funding":       row.get("funding", {}),
                "news_pulse":    row.get("news_pulse", {}),
            }
        return None
    except Exception as e:
        print(f"[deep_research] Supabase load failed: {e}")
        return None