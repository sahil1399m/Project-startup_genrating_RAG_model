from sentence_transformers import SentenceTransformer
import chromadb

embedder = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_collection("startup_docs")

query = "What government schemes are available for startups in India?"
query_embedding = embedder.encode([query]).tolist()

results = collection.query(
    query_embeddings=query_embedding,
    n_results=3
)

print(f"Query: {query}\n")
for i, doc in enumerate(results["documents"][0]):
    print(f"--- Result {i+1} ---")
    print(f"Source: {results['metadatas'][0][i]['source']}")
    print(f"Page: {results['metadatas'][0][i]['page']}")
    print(f"Text: {doc[:300]}...")
    print()