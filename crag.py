"""
Corrective Retrieval Augmented Generation (CRAG)
Based on: Yan et al. 2024, https://arxiv.org/abs/2401.15884
Graph structure adapted from: github.com/campusx-official/corrective-rag

ARCHITECTURAL NOTE ON MODEL SUBSTITUTION:
The original CRAG paper fine-tunes a T5-large (0.77B) model on labeled
query-document relevance pairs to act as the "Retrieval Evaluator". We
substitute this with a pre-trained CrossEncoder (ms-marco-MiniLM-L-6-v2,
~22M params), since fine-tuning T5 requires a labeled relevance dataset
that does not exist for our domain-specific startup policy corpus.

Both models serve the same architectural role: producing a lightweight
relevance score (independent of the large generator LLM) that triggers
one of three actions — Correct / Ambiguous / Incorrect — exactly as
defined in Section 4.3 of the paper.

GRAPH FLOW (LangGraph-style state machine):

    __start__
        |
     retrieve
        |
   eval_each_doc
        |
   ┌────┼────────────┐
CORRECT AMBIGUOUS  INCORRECT
   |       |            |
rewrite_query (Gemini Flash — rich structured rewrite used downstream everywhere)
   |       |            |
 refine  web_search   web_search         ← ALL branches now get Tavily
   |       |            |
   |    refine       (no refine)
   |   (internal+web)    |
   |       |        conversational_answer
   |       |         (NO blueprint — just
   |       |          a redirect message)
   |  explore_search  explore_search     ← bonus Tavily for CORRECT/AMBIGUOUS/INCORRECT
   └───┬───┘               |
    generate           shown in UI
   (blueprint)        as "Explore Further"
        |
     __end__

QUERY REWRITE (Gemini Flash):
Instead of a short 15-word search query, Gemini Flash produces a rich
structured rewrite that covers: problem statement, target customer,
value proposition, business model, geography, and tech approach.
This richer representation is used for everything downstream:
  - Tavily web search (all branches)
  - Granite summary generation
  - All 6 Groq blueprint sections
  - UI "How We Understood Your Idea" card

TAVILY — ALL BRANCHES:
  - CORRECT:    Tavily used for explore_results only (bonus section). Blueprint
                still generated from PDF-only context (unchanged behaviour).
  - AMBIGUOUS:  Tavily used for both context (fed into Granite) and explore_results.
  - INCORRECT:  Tavily used for conversational answer and explore_results.

THRESHOLDS (calibrated on RAW CrossEncoder logits, not sigmoid):
Diagnostic testing on this corpus (13 Indian govt/startup policy PDFs) showed
raw ms-marco-MiniLM logits cluster much lower than typical web-search ranges.
We threshold on the raw logit directly instead of sigmoid-compressing it,
since sigmoid collapsed all values near 0 and destroyed the signal.
"""

import os
import re
import json
from unittest import result
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb
from ibm_watsonx_ai.foundation_models import ModelInference
from tavily import TavilyClient
from groq import Groq
import google.generativeai as genai

load_dotenv()

UPPER_THRESHOLD = -3.0   # raw logit above this → CORRECT
LOWER_THRESHOLD = -6.5   # raw logit below this → INCORRECT
                         # between → AMBIGUOUS

def _get_gemini_embedding(text: str) -> list:
    from google import genai as _genai
    import os
    import streamlit as st

    # Guard against empty text
    if not text or not text.strip():
        text = "startup business idea India"

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            pass
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment or secrets")
    
    # Debug — remove after fixing
    st.write(f"DEBUG: API key found: {bool(api_key)}, length: {len(api_key) if api_key else 0}")

    _client = _genai.Client(api_key=api_key)
    result = _client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=text.strip()
    )
    if result is None or not result.embeddings:
        raise ValueError("Gemini embedding returned empty result")
    return list(result.embeddings[0].values)

# ══════════════════════════════════════════════════════════════════════════════
# NODE: retrieve
# ══════════════════════════════════════════════════════════════════════════════

def node_retrieve(query, embedder, collection, n=8):
    """Fetch top-n candidate chunks from ChromaDB using Gemini embeddings."""
    embedding = _get_gemini_embedding(query)
    results   = collection.query(query_embeddings=[embedding], n_results=n)
    docs      = results["documents"][0]
    metas     = results["metadatas"][0]
    return docs, metas


# ══════════════════════════════════════════════════════════════════════════════
# NODE: eval_each_doc  (retrieval evaluator → routes to Correct/Ambiguous/Incorrect)
# ══════════════════════════════════════════════════════════════════════════════
def node_eval_each_doc(query, docs, reranker):
    """
    Score each retrieved doc with the CrossEncoder and derive a confidence label.
    Thresholds are calibrated on raw logits (not sigmoid) for this corpus.
    """
    if not docs:
        return [], [], "INCORRECT"

    pairs      = [(query, doc) for doc in docs]
    raw_logits = reranker.predict(pairs)
    raw_logits = np.array(raw_logits)
    max_logit  = float(raw_logits.max())

    # Sigmoid scores kept only for display in the UI
    norm_scores = (1 / (1 + np.exp(-raw_logits))).tolist()

    print(f"[CRAG DEBUG] Raw logits: {raw_logits.tolist()}")
    print(f"[CRAG DEBUG] Max raw logit: {max_logit:.3f}  "
          f"(Correct >= {UPPER_THRESHOLD}, Incorrect < {LOWER_THRESHOLD})")

    if max_logit >= UPPER_THRESHOLD:
        confidence = "CORRECT"
    elif max_logit < LOWER_THRESHOLD:
        confidence = "INCORRECT"
    else:
        confidence = "AMBIGUOUS"

    return norm_scores, raw_logits.tolist(), confidence


def node_rewrite_query(query, sector, stage, model_type, target_city, gemini_client):

    prompt = f"""
You are a Retrieval Query Understanding Agent for an AI Startup Blueprint Generator.

Your task is NOT to summarize or shorten the startup idea.

Your goal is to preserve every important piece of information from the user's idea while restructuring it for optimal semantic retrieval from a knowledge base and web search.

User Startup Idea:
{query}

Selected Context:
Sector: {sector}
Startup Stage: {stage}
Business Model: {model_type}
Primary Market: {target_city}

Rules:
- Never omit important information.
- Never replace detailed features with generic descriptions.
- Preserve AI techniques, technologies, customer segments, geography, integrations, business model and requested analyses.
- Remove only filler words.
- Do NOT invent new features.

Return ONLY the following format.

PROBLEM STATEMENT
2-4 detailed sentences.

TARGET USERS
- Primary
- Secondary
- Enterprise

CORE SOLUTION
2-3 detailed sentences.

KEY FEATURES
- Feature 1
- Feature 2
- Feature 3
- Feature 4
- Feature 5
- Feature 6

TECHNOLOGIES
- ...

INDUSTRY
...

GEOGRAPHY
...

BUSINESS MODEL
...

REQUESTED BUSINESS ANALYSIS
- Competitor Analysis
- Customer Segmentation
- Revenue Model
- Pricing Strategy
- Marketing Strategy
- Funding
- Government Schemes
- Legal Compliance
- Financial Projection
- Growth Roadmap

KEYWORDS:
keyword1, keyword2, keyword3, ...

RETRIEVAL QUERIES:
1. ...
2. ...
3. ...
4. ...
5. ...

SEARCH CONTEXT:
Write one 50-80 word retrieval-focused paragraph combining every important concept naturally.
"""

    try:

        model = gemini_client.GenerativeModel("gemini-2.5-flash")

        response = model.generate_content(
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=3000
            )

        )

        rewritten = response.text.strip()

        if len(rewritten) < 80:
            raise Exception("Rewrite too short")

        import re

        keywords = []
        retrieval_queries = []
        search_context = ""

        # ---------------- KEYWORDS ----------------

        m = re.search(
            r"KEYWORDS:\s*(.*?)\n\s*RETRIEVAL QUERIES:",
            rewritten,
            re.S
        )

        if m:
            keywords = [
                k.strip()
                for k in m.group(1).split(",")
                if k.strip()
            ]

        # ---------------- RETRIEVAL QUERIES ----------------

        m = re.search(
            r"RETRIEVAL QUERIES:\s*(.*?)\n\s*SEARCH CONTEXT:",
            rewritten,
            re.S
        )

        if m:

            lines = m.group(1).splitlines()

            for line in lines:

                line = line.strip()

                if "." in line:
                    retrieval_queries.append(
                        line.split(".", 1)[1].strip()
                    )

        # ---------------- SEARCH CONTEXT ----------------

        m = re.search(
            r"SEARCH CONTEXT:\s*(.*)",
            rewritten,
            re.S
        )

        if m:
            search_context = m.group(1).strip()

        return {
            "structured_brief": rewritten,
            "keywords": keywords,
            "retrieval_queries": retrieval_queries,
            "search_context": search_context
        }

    except Exception as e:

        print(f"[CRAG] Rewrite failed: {e}")

        return {
            "structured_brief": query,
            "keywords": [],
            "retrieval_queries": [query],
            "search_context": query
        }


def node_web_search(search_context, retrieval_queries, tavily, sector="startup", max_results=5):
    """
    Search Tavily using multiple optimized retrieval queries.
    Falls back to search_context if retrieval queries are unavailable.
    """

    all_results = []
    seen_urls = set()

    queries = retrieval_queries if retrieval_queries else [search_context]

    for q in queries:

        search_query = f"{q} India startup {sector} 2024 2025"

        try:

            results = tavily.search(
                query=search_query,
                search_depth="advanced",
                max_results=max_results,
                include_domains=[
                    "startupindia.gov.in",
                    "msme.gov.in",
                    "aim.gov.in",
                    "investindia.gov.in",
                    "inc42.com",
                    "yourstory.com",
                    "economictimes.indiatimes.com",
                    "entrackr.com",
                    "techcrunch.com"
                ]
            )

            for r in results.get("results", []):

                url = r.get("url", "")

                if url in seen_urls:
                    continue

                seen_urls.add(url)

                all_results.append({
                    "title": r.get("title", ""),
                    "content": r.get("content", "")[:500],
                    "url": url,
                    "score": r.get("score", 0)
                })

        except Exception as e:
            print(f"[CRAG] Tavily search failed for '{q}': {e}")

    all_results.sort(key=lambda x: x["score"], reverse=True)

    return all_results


# ══════════════════════════════════════════════════════════════════════════════
# NODE: refine  (decompose-then-recompose knowledge refinement)
# ══════════════════════════════════════════════════════════════════════════════
def node_refine(query, docs, raw_logits, reranker, top_k=4):
    """
    Refine internal PDF documents into clean knowledge strips.
    Splits each relevant doc into sentence-pair strips, re-scores them,
    and returns only the most relevant top_k strips — filtering intra-doc noise.
    """
    all_strips = []
    for doc, doc_logit in zip(docs, raw_logits):
        if doc_logit < LOWER_THRESHOLD:
            continue
        strips  = [s.strip() for s in re.split(r'(?<=[.!?])\s+', doc) if len(s.strip()) > 30]
        grouped = []
        for i in range(0, len(strips), 2):
            group = " ".join(strips[i:i+2])
            if group:
                grouped.append(group)
        all_strips.extend(grouped)

    if not all_strips:
        return "\n\n".join(docs[:3])

    strip_pairs   = [(query, strip) for strip in all_strips]
    strip_scores  = reranker.predict(strip_pairs)
    scored_strips = sorted(zip(strip_scores, all_strips), key=lambda x: x[0], reverse=True)
    top_strips    = [strip for _, strip in scored_strips[:top_k]]

    return "\n\n".join(top_strips) if top_strips else "\n\n".join(docs[:2])


def refine_web_results(web_results):
    """Format Tavily results into a clean knowledge block for Granite."""
    if not web_results:
        return ""
    blocks = []
    for r in web_results:
        blocks.append(f"[{r['title']}]\n{r['content']}\nSource: {r['url']}")
    return "\n\n---\n\n".join(blocks)


# ══════════════════════════════════════════════════════════════════════════════
# NODE: generate  (Granite summarizes grounded context — used for CORRECT/AMBIGUOUS)
# ══════════════════════════════════════════════════════════════════════════════
def node_generate_summary(query, context, granite, context_type="internal"):
    """
    Granite 4.0 synthesizes the grounded context into a startup policy brief.
    The full Gemini-rewritten query is passed as `query` so Granite has rich
    context about the business model, target customer, and geography.
    """
    type_note = {
        "internal": "retrieved from official Indian government policy documents",
        "combined": "retrieved from both official policy documents and live web sources"
    }.get(context_type, "retrieved")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior Indian startup policy advisor with deep knowledge of "
                "government schemes, DPIIT regulations, MSME policies, and the Indian "
                "entrepreneurship ecosystem. Synthesize the provided context into a clear, "
                "actionable policy brief. Focus on: applicable government schemes and "
                "their eligibility, funding pathways, regulatory requirements, and "
                "sector-specific support available. Be specific, factual, and concise. "
                "Only use information present in the provided context — do not hallucinate."
            )
        },
        {
            "role": "user",
            "content": (
                f"Startup Brief:\n{query}\n\n"
                f"Grounded Context ({type_note}):\n{context}\n\n"
                "Write a concise policy brief (300-500 words) covering the most relevant "
                "schemes, eligibility criteria, funding options, and actionable next steps "
                "for this specific startup idea."
            )
        }
    ]
    response = granite.chat(messages=messages, params={"max_tokens": 1800, "temperature": 0.2})
    return response["choices"][0]["message"]["content"]


# ══════════════════════════════════════════════════════════════════════════════
# NODE: conversational_answer  (INCORRECT path — NO blueprint, just plain answer)
# ══════════════════════════════════════════════════════════════════════════════
def node_conversational_answer(query, web_results, groq_client):
    """
    For INCORRECT confidence: the internal knowledge base can't ground this query.
    We give a plain conversational answer using only Tavily web results,
    with NO blueprint generation.
    If Tavily also finds nothing useful, return a generic redirect with examples.
    """
    web_context = refine_web_results(web_results)

    if not web_context or len(web_context.strip()) < 50:
        return {
            "type": "redirect",
            "message": (
                "I'm a startup strategy assistant focused on the Indian entrepreneurship "
                "ecosystem — government schemes, business models, funding, and go-to-market "
                "planning. Your query doesn't seem specific enough to generate a blueprint.\n\n"
                "Try describing your idea with more detail, like:\n"
                "• \"An AI-powered logistics platform for last-mile delivery in Tier-2 cities\"\n"
                "• \"A SaaS tool for small clinics to manage patient appointments and billing\"\n"
                "• \"A B2B marketplace connecting textile manufacturers with export buyers in EU\""
            )
        }

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a startup strategy assistant for the Indian market. "
                        "The user's query didn't match our internal policy knowledge base "
                        "well, but live web search found some relevant context. "
                        "Give a helpful, structured answer in 4-6 sentences covering: "
                        "what this space looks like in India, key players or trends, "
                        "and one concrete next step the founder should take. "
                        "Do NOT produce a full business blueprint — keep it conversational."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Structured Startup Brief:\n{query}\n\n"
                        f"Live web context:\n{web_context}\n\n"
                        "Give a helpful conversational answer:"
                    )
                }
            ],
            temperature=0.2,
            max_tokens=1600
        )
        answer = response.choices[0].message.content.strip()
        return {"type": "answer", "message": answer, "web_context": web_context}
    except Exception as e:
        return {
            "type": "redirect",
            "message": "Something went wrong fetching a response. Please try rephrasing your startup idea with more detail."
        }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CRAG GRAPH RUNNER
# ══════════════════════════════════════════════════════════════════════════════
def run_crag(
    query, sector, stage, model_type, target_city,
    embedder, reranker, collection, granite, tavily, groq_client, gemini_client
):
    """
    Full CRAG graph execution.

    retrieve → eval_each_doc → rewrite_query (Gemini) → branch

    CORRECT:    refine(PDF) → generate(PDF only) + explore_search(Tavily bonus)
    AMBIGUOUS:  web_search → refine(PDF+web) → generate(combined) + explore_search
    INCORRECT:  web_search → conversational_answer (NO blueprint) + explore_results

    The Gemini rewritten query (rich structured brief) replaces the original
    idea for ALL downstream steps: Tavily queries, Granite summarisation,
    and all 6 Groq blueprint generation calls.
    """
    result = {
        "confidence":              "",
        "action":                  "",
        "should_generate_blueprint": False,
        "summary":                 "",
        "sources":                 [],
        "internal_context":        "",
        "external_context":        "",
        "scores":                  [],
        "raw_logits":              [],
        "original_query":          query,
        "rewritten_query":         "",

        # NEW
        "keywords":                [],
        "retrieval_queries":       [],
        "search_context":          "",

        "conversational_response": None,
        "explore_results":         [],
    }

    # ── Node 3: rewrite_query (Gemini Flash — runs in ALL branches) ───────────
    rewrite = node_rewrite_query(
    query,
    sector,
    stage,
    model_type,
    target_city,
    gemini_client)

    result["rewritten_query"] = rewrite["structured_brief"]
    result["keywords"] = rewrite["keywords"]
    result["retrieval_queries"] = rewrite["retrieval_queries"]
    result["search_context"] = rewrite["search_context"]

    # ── Node 1: retrieve ──────────────────────────────────────────────────────
    docs, metas = node_retrieve(result["search_context"],embedder,collection,n=8)
    sources = list({m.get("source", "Unknown") for m in metas})

    # ── Node 2: eval_each_doc ─────────────────────────────────────────────────
    scores, raw_logits, confidence = node_eval_each_doc(
    result["search_context"],
    docs,
    reranker
    )
    result["confidence"] = confidence
    result["scores"]     = scores
    result["raw_logits"] = raw_logits
    result["sources"]    = sources



    # ── Branch: CORRECT ───────────────────────────────────────────────────────
    if confidence == "CORRECT":
        result["action"] = (
            "✅ CORRECT — Internal policy documents are strongly relevant. "
            "Blueprint generated from refined PDF knowledge. "
            "Live web results shown below as bonus exploration."
        )
        result["should_generate_blueprint"] = True

        # Blueprint context: PDF only (unchanged from original behaviour)
        refined_internal        = node_refine(result["search_context"], docs, raw_logits, reranker)
        result["internal_context"] = refined_internal
        summary                 = node_generate_summary(result["rewritten_query"], refined_internal, granite, "internal")
        result["summary"]       = summary

        # Bonus exploration: Tavily results (NOT fed into blueprint)
        explore = node_web_search(
    result["search_context"],
    result["retrieval_queries"],
    tavily,
    sector,
    max_results=4
)
        result["explore_results"] = explore
        if explore:
            result["sources"].append("tavily_web_search")

    # ── Branch: AMBIGUOUS ─────────────────────────────────────────────────────
    elif confidence == "AMBIGUOUS":
        result["action"] = (
            "⚡ AMBIGUOUS — Partial relevance detected. "
            "Combining policy documents with live web search for a richer context. "
            "Blueprint generated from both sources."
        )
        result["should_generate_blueprint"] = True

        # Blueprint context: PDF + Tavily combined (fed into Granite)
        refined_internal = node_refine(result["search_context"], docs, raw_logits, reranker)
        web_results = node_web_search(
    result["search_context"],
    result["retrieval_queries"],
    tavily,
    sector,
    max_results=3
)
        web_context      = refine_web_results(web_results)

        result["internal_context"] = refined_internal
        result["external_context"] = web_context

        combined_context = (
            "=== FROM POLICY DOCUMENTS ===\n" + refined_internal +
            "\n\n=== FROM LIVE WEB SEARCH ===\n" + web_context
        )
        summary          = node_generate_summary(result["rewritten_query"], combined_context, granite, "combined")
        result["summary"] = summary

        # Explore results = same Tavily batch (shown as bonus in UI)
        result["explore_results"] = web_results
        if web_results:
            result["sources"].append("tavily_web_search")

    # ── Branch: INCORRECT ─────────────────────────────────────────────────────
    else:
        result["action"] = (
            "❌ INCORRECT — Internal knowledge base is not relevant enough. "
            "Searching the live web for a direct answer. "
            "No blueprint generated — refine your idea for a full analysis."
        )
        result["should_generate_blueprint"] = False

        web_results = node_web_search(
    result["search_context"],
    result["retrieval_queries"],
    tavily,
    sector,
    max_results=3
)
        web_context              = refine_web_results(web_results)
        result["external_context"] = web_context
        result["explore_results"]  = web_results

        conv = node_conversational_answer(result["rewritten_query"], web_results, groq_client)
        result["conversational_response"] = conv
        result["sources"] = ["tavily_web_search"] if web_results else []

    return result