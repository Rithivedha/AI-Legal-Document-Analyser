import os
import uuid
from pathlib import Path
from typing import List, Tuple

# In-memory chunk store fallback
_memory_chunks = {}
_client = None
_embedding_model = None

def _get_chroma_client():
    """Lazy initialize ChromaDB client if available."""
    global _client
    if _client is None:
        try:
            import chromadb
            from chromadb.config import Settings
            chroma_path = Path(__file__).resolve().parent / "chroma_db"
            os.makedirs(chroma_path, exist_ok=True)
            _client = chromadb.PersistentClient(path=str(chroma_path), settings=Settings(allow_reset=True))
        except Exception as e:
            print(f"[rag_engine] ChromaDB client note: {e}")
            _client = False
    return _client if _client is not False else None

def _get_embedding_model():
    """Lazy-load sentence-transformers model only when memory allows."""
    global _embedding_model
    if _embedding_model is False:
        return None
    if _embedding_model is None:
        # On Render free tier or low-memory flags, skip 400MB PyTorch model to avoid OOM
        if os.environ.get("RENDER") or os.environ.get("LOW_MEMORY") == "1":
            print("[rag_engine] Render/low-memory environment detected: using instant keyword RAG.")
            _embedding_model = False
            return None
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            print(f"[rag_engine] SentenceTransformer load failed: {e}")
            _embedding_model = False
    return _embedding_model if _embedding_model is not False else None

def _load_pdf_text(file_path: str) -> str:
    """Extract raw text from a PDF using PyMuPDF (fitz) or pypdf."""
    # 1. Try PyMuPDF
    try:
        import fitz
        doc = fitz.open(file_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        if text.strip():
            return text
    except Exception as e:
        print(f"[rag_engine] PyMuPDF failed: {e}")

    # 2. Try pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        if text.strip():
            return text
    except Exception as e:
        print(f"[rag_engine] pypdf failed: {e}")

    # 3. Fallback to PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        if text.strip():
            return text
    except Exception as e:
        print(f"[rag_engine] PyPDF2 failed: {e}")

    return ""

def _split_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    length = len(text)
    step = max(chunk_size - overlap, 1)
    while start < length:
        end = min(start + chunk_size, length)
        chunks.append(text[start:end])
        start += step
    return chunks

def _embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed texts using local sentence-transformers model if available."""
    model = _get_embedding_model()
    if model is None:
        return []
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()

def chunk_and_store(pdf_path: str, doc_id: str = None) -> str:
    """Process a PDF: extract text, split into chunks, embed and store."""
    if not doc_id:
        doc_id = str(uuid.uuid4())

    raw_text = _load_pdf_text(pdf_path)
    if not raw_text.strip():
        raw_text = "Standard legal agreement document."

    chunks = _split_into_chunks(raw_text)
    chunks = chunks[:500]
    _memory_chunks[doc_id] = chunks

    client = _get_chroma_client()
    if client:
        try:
            collection_name = f"doc_chunks_{doc_id}"
            existing = [getattr(c, 'name', str(c)) for c in client.list_collections()]
            if collection_name in existing:
                client.delete_collection(name=collection_name)
            collection = client.create_collection(name=collection_name)

            batch_size = 20
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                try:
                    embeddings = _embed_texts(batch)
                except Exception:
                    embeddings = None

                if embeddings:
                    collection.add(
                        documents=batch,
                        embeddings=embeddings,
                        ids=[f"chunk_{i + j}" for j in range(len(batch))],
                        metadatas=[{"source": pdf_path, "index": i + j} for j in range(len(batch))],
                    )
                else:
                    collection.add(
                        documents=batch,
                        ids=[f"chunk_{i + j}" for j in range(len(batch))],
                        metadatas=[{"source": pdf_path, "index": i + j} for j in range(len(batch))],
                    )
        except Exception as e:
            print(f"[rag_engine] Chroma storage note: {e}. In-memory chunks active.")

    return doc_id

def retrieve_chunks(doc_id: str, query: str, k: int = 5) -> List[Tuple[str, str]]:
    """Retrieve top-k most relevant chunks for a query."""
    client = _get_chroma_client()
    if client:
        try:
            collection_name = f"doc_chunks_{doc_id}"
            existing = [getattr(c, 'name', str(c)) for c in client.list_collections()]
            if collection_name in existing:
                collection = client.get_collection(name=collection_name)
                emb_list = _embed_texts([query])
                if emb_list:
                    results = collection.query(
                        query_embeddings=emb_list,
                        n_results=k,
                        include=['documents', 'metadatas']
                    )
                    docs = results.get('documents', [[]])[0]
                    metas = results.get('metadatas', [[]])[0]
                    retrieved_list = list(zip(docs, metas)) if docs else []
                    
                    if doc_id in _memory_chunks and _memory_chunks[doc_id]:
                        preamble = _memory_chunks[doc_id][0]
                        if not any(preamble[:50] in doc[:50] for doc, _ in retrieved_list):
                            retrieved_list.insert(0, (preamble, {"source": "preamble", "index": 0}))

                    if retrieved_list:
                        return retrieved_list[:k+1]
        except Exception as e:
            print(f"[rag_engine] Chroma retrieve note: {e}")

    # High-speed keyword match fallback from in-memory chunks
    if doc_id in _memory_chunks:
        chunks = _memory_chunks[doc_id]
        words = set(w.lower() for w in query.replace("?", "").replace(",", "").split() if len(w) > 2)
        scored = []
        for c in chunks:
            c_lower = c.lower()
            score = sum(2 if w in c_lower else 0 for w in words)
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        retrieved = [(c, "memory") for _, c in scored[:k]]
        if chunks and not any(chunks[0][:50] in c[:50] for c, _ in retrieved):
            retrieved.insert(0, (chunks[0], "preamble"))
        return retrieved[:k+1]

    return [("Agreement terms and general legal conditions.", "default")]