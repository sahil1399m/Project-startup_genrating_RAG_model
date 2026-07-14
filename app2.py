"""
app2.py — Minimal Startup RAG Demo
Simple ChromaDB retrieval + Groq generation. No auth, no DB, no heavy models.
Fast cold start on Streamlit Cloud.
"""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Startup Blueprint RAG",
    page_icon="🚀",
    layout="centered"
)

# ── Secrets helper ─────────────────────────────────────────────────────────────
def get_secret(key):
    try:
        val = st.secrets.get(key)
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key, "")


# ── Load resources ─────────────────────────────────────────────────────────────
@st.cache_resource
def load_resources():
    from sentence_transformers import SentenceTransformer
    import chromadb
    from groq import Groq

    embedder   = SentenceTransformer("all-MiniLM-L6-v2")
    client     = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_collection("startup_docs")
    groq       = Groq(api_key=get_secret("GROQ_API_KEY"))
    return embedder, collection, groq


# ── RAG function ───────────────────────────────────────────────────────────────
def run_rag(query: str, embedder, collection, groq_client) -> str:
    # Embed query
    query_vec = embedder.encode(query).tolist()

    # Retrieve top 5 chunks
    results = collection.query(
        query_embeddings=[query_vec],
        n_results=5
    )
    docs = results["documents"][0] if results["documents"] else []

    if not docs:
        context = "No relevant policy documents found."
    else:
        context = "\n\n---\n\n".join(docs)

    # Generate answer
    prompt = f"""You are an expert startup advisor for the Indian ecosystem.
Use the following policy documents to answer the question.
Be specific, practical and grounded in the documents provided.

POLICY DOCUMENTS:
{context}

QUESTION: {query}

ANSWER:"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.7
    )
    return response.choices[0].message.content


# ── UI ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background: #0a0f1e; }
    .stApp { background: #0a0f1e; color: #e2e8f0; }
    h1 { color: #7c3aed; }
    .stTextArea textarea { background: #1a1f35; color: #e2e8f0; border: 1px solid #2d3748; }
    .stButton button { background: linear-gradient(135deg,#6366f1,#8b5cf6); color: white; border: none; border-radius: 8px; padding: 0.5rem 2rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.title("🚀 Startup Blueprint RAG")
st.markdown("**Ask anything about Indian startup policies, schemes, and funding**")
st.markdown("*Powered by IBM Granite Policy Docs + Groq Llama 3.3*")
st.divider()

# Load resources with spinner
with st.spinner("Loading AI models... please wait"):
    try:
        embedder, collection, groq_client = load_resources()
        st.success("✅ Models loaded! Ask your question below.")
    except Exception as e:
        st.error(f"Error loading models: {e}")
        st.stop()

st.divider()

# Query input
query = st.text_area(
    "Your Question",
    placeholder="e.g. What are the tax benefits for DPIIT recognised startups in India?",
    height=100
)

col1, col2 = st.columns([1, 4])
with col1:
    ask = st.button("Ask →", type="primary")

if ask and query.strip():
    with st.spinner("Searching policy documents and generating answer..."):
        try:
            answer = run_rag(query.strip(), embedder, collection, groq_client)
            st.markdown("### 📋 Answer")
            st.markdown(answer)
            st.divider()
            st.caption("*Grounded in 13 Indian government policy PDFs*")
        except Exception as e:
            st.error(f"Error: {e}")
elif ask and not query.strip():
    st.warning("Please enter a question.")

st.divider()
st.markdown("""
<div style='text-align:center;color:#4a5568;font-size:0.8rem'>
    🔒 IBM Granite 4.0 · Groq Llama 3.3 · ChromaDB · CRAG Pipeline
</div>
""", unsafe_allow_html=True)