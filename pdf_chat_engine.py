import os
import chromadb

from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer

# Load Gemini API Key
load_dotenv(override=True)

from llm_provider import LLMProvider
llm_chat = LLMProvider()

client_gemini = None
if os.getenv("GEMINI_API_KEY"):
    try:
        client_gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    except Exception:
        pass

# Embedding Model
embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

# ChromaDB
current_dir = os.path.dirname(os.path.abspath(__file__))
chroma_path = os.path.join(current_dir, "chroma_db")
client = chromadb.PersistentClient(path=chroma_path)


# Create Collection
try:
    client.delete_collection("uploaded_pdf")
except:
    pass

collection = client.create_collection(
    "uploaded_pdf"
)


def store_document(document_text):
    global collection
    
    # Recreate the collection to clear previous document chunks
    try:
        client.delete_collection("uploaded_pdf")
    except Exception as e:
        print("Note on delete_collection:", e)
        
    collection = client.create_collection("uploaded_pdf")

    chunks = []

    chunk_size = 500

    for i in range(0, len(document_text), chunk_size):

        chunks.append(
            document_text[i:i + chunk_size]
        )

    ids = [str(i) for i in range(len(chunks))]

    embeddings = embedding_model.encode(
        chunks
    ).tolist()

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings
    )

    print("PDF Stored Successfully")



def ask_pdf(question):

    query_embedding = embedding_model.encode(
        question
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    context = "\n".join(
        results["documents"][0]
    )

    prompt = f"""
You are a Legal Document Assistant.

Your job is to answer ONLY from the provided document context.

LANGUAGE RULES:

1. If the question is in English, answer in English.

2. If the question is in Tamil, answer in Tamil.

3. If the question contains:
   - answer in tamil
   - say in tamil
   - explain in tamil
   - tamil la
   - தமிழில்
   then answer in Tamil.

4. If the question contains:
   - answer in english
   - say in english
   - explain in english
   - ஆங்கிலத்தில்
   then answer in English.

5. If the user uses Tanglish:
   Examples:
   - document la enna iruku
   - penalty iruka
   - owner yaru
   - risk enna

   Answer in simple Tamil.

ANSWER STYLE:

1. Use simple language.

2. Explain like talking to an ordinary person.

3. Avoid complicated legal words.

4. If a legal term appears, explain it.

5. Mention clause number if available.

6. If the document contains:
   - penalty
   - fine
   - charges
   - liability
   - termination
   - risk
   explain it clearly.

7. Search all provided context before answering.

8. Be consistent across languages.

9. Never invent information.

10. If answer is not available:

English:
This information is not available in the uploaded document.

Tamil:
இந்த தகவல் ஆவணத்தில் இல்லை.

FOR TAMIL ANSWERS:

- Use natural conversational Tamil.
- Do not translate word by word.
- Suitable for rural users.
- Suitable for elderly people.
- Keep answers easy to understand.

Document Context:

{context}

User Question:

{question}
"""

    try:
        if client_gemini:
            response = client_gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if hasattr(response, "text") and response.text:
                return response.text
        return llm_chat.generate(prompt)
    except Exception as e:
        try:
            return llm_chat.generate(prompt)
        except Exception as e2:
            return f"Error: {str(e2)}"