"""
data_ingestion.py — Ingest PDFs into ChromaDB using gemini-embedding-001
Resumes from where it stopped — skips already embedded docs.
"""
import os
import glob
import time
import chromadb
import pdfplumber
from dotenv import load_dotenv
from google import genai

load_dotenv()

client_genai = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def get_embedding(text: str) -> list:
    result = client_genai.models.embed_content(
        model="models/gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

def ingest_pdfs():
    # ── Connect to existing ChromaDB (don't delete it) ────────────────────────
    client = chromadb.PersistentClient(path="chroma_db")

    # Get or create collection
    try:
        collection = client.get_collection(name="startup_docs")
        print(f"✅ Resuming — existing collection has {collection.count()} chunks")
    except Exception:
        collection = client.create_collection(
            name="startup_docs",
            metadata={"hnsw:space": "cosine"}
        )
        print("🆕 Created new collection")

    # ── Get already embedded sources ──────────────────────────────────────────
    existing = collection.get(include=["metadatas"])
    already_done = {}  # {filename: set of chunk indices}
    for meta in existing["metadatas"]:
        src = meta.get("source", "")
        chunk_idx = meta.get("chunk", -1)
        if src not in already_done:
            already_done[src] = set()
        already_done[src].add(chunk_idx)

    print(f"📋 Already embedded: {list(already_done.keys())}")

    # ── Find all PDFs ─────────────────────────────────────────────────────────
    pdf_files = glob.glob("data/**/*.pdf", recursive=True)
    print(f"Found {len(pdf_files)} PDFs total\n")

    # Start doc_id from current count
    doc_id = collection.count()

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)

        # Check if this PDF is fully done
        if filename in already_done:
            print(f"⏭️  Skipping (already embedded): {filename}")
            continue

        print(f"Processing: {pdf_path}")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"

            if not full_text.strip():
                print(f"  Skipping — no text extracted")
                continue

            chunks = chunk_text(full_text)
            print(f"  {len(chunks)} chunks to embed")

            failed_chunks = []

            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:
                    continue

                # Skip already embedded chunk indices for this file
                if filename in already_done and i in already_done[filename]:
                    continue

                try:
                    time.sleep(1.5)  # slightly safer delay
                    embedding = get_embedding(chunk)
                    collection.add(
                        ids=[f"doc_{doc_id}"],
                        embeddings=[embedding],
                        documents=[chunk],
                        metadatas=[{
                            "source": filename,
                            "chunk": i
                        }]
                    )
                    doc_id += 1
                    print(f"  ✓ Chunk {i} embedded (total: {doc_id})")

                except Exception as e:
                    err = str(e)
                    if "429" in err or "RESOURCE_EXHAUSTED" in err:
                        print(f"\n⚠️  Rate limit hit at chunk {i} of {filename}")
                        print(f"   Chunks embedded so far: {doc_id}")
                        print(f"   Run the script again tomorrow to resume.\n")
                        return  # Exit cleanly — resumes next run
                    else:
                        print(f"  Chunk {i} error: {e}")
                        failed_chunks.append(i)
                        continue

            print(f"  ✅ Done: {filename} — {doc_id} total chunks so far")
            if failed_chunks:
                print(f"  ⚠️  Failed chunks: {failed_chunks}")

        except Exception as e:
            print(f"  Error processing {pdf_path}: {e}")
            continue

    print(f"\n✅ Ingestion complete! {doc_id} chunks stored in chroma_db")

if __name__ == "__main__":
    ingest_pdfs()