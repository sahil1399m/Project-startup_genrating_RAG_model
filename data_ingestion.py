"""
data_ingestion.py — Ingest PDFs into ChromaDB using Google text-embedding-004
"""
import os
import glob
import chromadb
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Configure Google API
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
    # Delete old chroma_db
    import shutil
    if os.path.exists("chroma_db"):
        shutil.rmtree("chroma_db")
        print("Deleted old chroma_db")

    # Create new client
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.create_collection(
        name="startup_docs",
        metadata={"hnsw:space": "cosine"}
    )

    # Find all PDFs
    pdf_files = glob.glob("data/**/*.pdf", recursive=True)
    print(f"Found {len(pdf_files)} PDFs")

    import pdfplumber
    doc_id = 0

    for pdf_path in pdf_files:
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
            print(f"  {len(chunks)} chunks")

            import time

            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:
                    continue
                try:
                    time.sleep(1)  # 1 second delay between calls
                    embedding = get_embedding(chunk)
                    collection.add(
                        ids=[f"doc_{doc_id}"],
                        embeddings=[embedding],
                        documents=[chunk],
                        metadatas=[{
                            "source": os.path.basename(pdf_path),
                            "chunk": i
                        }]
                    )
                    doc_id += 1
                except Exception as e:
                    print(f"  Chunk {i} error: {e}")
                    continue

            print(f"  Done — {doc_id} total chunks so far")

        except Exception as e:
            print(f"  Error: {e}")
            continue

    print(f"\n✅ Ingestion complete! {doc_id} chunks stored in chroma_db")

if __name__ == "__main__":
    ingest_pdfs()