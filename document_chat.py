import os
import chromadb

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from llm_provider import LLMProvider

load_dotenv(override=True)

current_dir = os.path.dirname(os.path.abspath(__file__))
chroma_path = os.path.join(current_dir, "chroma_db")
os.makedirs(chroma_path, exist_ok=True)
client = chromadb.PersistentClient(path=chroma_path)
collection = client.get_or_create_collection("legal_contracts")

_embedding_model = None
def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model

llm = LLMProvider()

def ask_document(question):
    model = get_embedding_model()
    query_embedding = model.encode(question).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    docs = results.get("documents", [[]])
    context = "\n".join(docs[0]) if docs and docs[0] else ""

    prompt = f"""
You are a legal document assistant.
Use the context below to answer.

Context:
{context}

Question:
{question}

Answer in simple English.
"""

    return llm.generate(prompt)