import os
import chromadb

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

DATASET_FOLDER = r"datasets/dataset/full_contract_txt 2/full_contract_txt"

# Load contracts
contracts = []

files = os.listdir(DATASET_FOLDER)

for file in files[:20]:   # start with 20 contracts only

    if file.endswith(".txt"):

        path = os.path.join(DATASET_FOLDER, file)

        with open(path, "r", encoding="utf-8", errors="ignore") as f:

            contracts.append(f.read())

# Combine text
all_text = "\n".join(contracts)

# Chunking
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

chunks = splitter.split_text(all_text)

print("Chunks:", len(chunks))

# Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# ChromaDB
client = chromadb.PersistentClient(path="chroma_db")

collection = client.get_or_create_collection(
    name="legal_contracts"
)

# Store chunks
for i, chunk in enumerate(chunks):

    embedding = model.encode(chunk).tolist()

    collection.add(
        ids=[str(i)],
        embeddings=[embedding],
        documents=[chunk]
    )

print("Stored in ChromaDB Successfully!")