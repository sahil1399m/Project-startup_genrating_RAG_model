from dotenv import load_dotenv
import os
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────
# doc_type inference
# ──────────────────────────────────────────────────────────────────────────
# Preferred: organize your `data/` folder into subfolders named after the
# doc_type itself, e.g.:
#   data/government_scheme/startup_india_guidelines.pdf
#   data/government_scheme/msme_policy.pdf
#   data/market_report/fintech_trends_2026.pdf
#   data/legal/companies_act_startup_clauses.pdf
#   data/investor/incubator_directory.pdf
#
# If a PDF isn't in one of these subfolders, we fall back to keyword
# matching on the filename so existing flat folders still get tagged
# reasonably instead of all landing in "general".

KNOWN_DOC_TYPES = {
    "government_scheme", "market_report", "legal", "investor", "general"
}

FILENAME_KEYWORDS = {
    "government_scheme": ["scheme", "msme", "startup_india", "dpiit", "policy", "subsidy", "yojana"],
    "market_report":     ["market", "trend", "report", "survey", "industry"],
    "legal":             ["legal", "compliance", "act", "regulation", "tax", "gst", "company_law"],
    "investor":          ["investor", "incubator", "accelerator", "vc", "funding", "angel"],
}


def infer_doc_type(filepath, folder_root):
    """
    1. If the PDF lives directly under data/<doc_type>/..., use that.
    2. Otherwise, keyword-match the filename.
    3. Otherwise, "general".
    """
    rel = os.path.relpath(filepath, folder_root)
    parts = rel.split(os.sep)

    if len(parts) > 1 and parts[0].lower() in KNOWN_DOC_TYPES:
        return parts[0].lower()

    fname = parts[-1].lower()
    for doc_type, keywords in FILENAME_KEYWORDS.items():
        if any(kw in fname for kw in keywords):
            return doc_type

    return "general"


def load_pdfs(folder="data"):
    docs = []
    for root, dirs, files in os.walk(folder):
        for filename in files:
            if filename.endswith(".pdf"):
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, folder)
                doc_type = infer_doc_type(filepath, folder)
                print(f"  Reading: {rel_path}  [doc_type={doc_type}]")
                try:
                    reader = PdfReader(filepath)
                    for i, page in enumerate(reader.pages):
                        text = page.extract_text()
                        if text and len(text.strip()) > 50:
                            docs.append({
                                "text": text.strip(),
                                "source": rel_path,
                                "page": i + 1,
                                "doc_type": doc_type,
                            })
                except Exception as e:
                    print(f"  Skipping {rel_path}: {e}")
    return docs


def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


def ingest():
    print("Loading PDFs from all subfolders...")
    docs = load_pdfs()
    print(f"\nFound {len(docs)} pages across all PDFs\n")

    print("Chunking text...")
    all_chunks = []
    all_metadata = []
    for doc in docs:
        chunks = chunk_text(doc["text"])
        for j, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadata.append({
                "source": doc["source"],
                "page": doc["page"],
                "chunk": j,
                "doc_type": doc["doc_type"],
            })
    print(f"Created {len(all_chunks)} chunks total")

    print("\nGenerating embeddings...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = embedder.encode(all_chunks, show_progress_bar=True)

    print("\nStoring in ChromaDB...")
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_or_create_collection("startup_docs")
    collection.add(
        documents=all_chunks,
        embeddings=embeddings.tolist(),
        metadatas=all_metadata,
        ids=[f"chunk_{i}" for i in range(len(all_chunks))]
    )
    print(f"\nDone! {len(all_chunks)} chunks stored in ChromaDB")

    print("\nSources indexed:")
    sources = set(m["source"] for m in all_metadata)
    for s in sorted(sources):
        print(f"  - {s}")

    print("\ndoc_type breakdown:")
    from collections import Counter
    type_counts = Counter(m["doc_type"] for m in all_metadata)
    for dt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  - {dt}: {count} chunks")


if __name__ == "__main__":
    ingest()
