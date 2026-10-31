import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path="chroma_db")

collection = client.get_collection("legal_contracts")

model = SentenceTransformer("all-MiniLM-L6-v2")

query = "termination clause"

query_embedding = model.encode(query).tolist()

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3
)

print("\nTOP RESULTS:\n")

for doc in results["documents"][0]:
    print("-" * 50)
    print(doc[:500])