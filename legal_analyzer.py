import os
import json
import chromadb
from typing import List
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from prompts import LEGAL_ANALYSIS_PROMPT
from risk_engine import calculate_risk
from llm_provider import LLMProvider

# Load API Key
load_dotenv(override=True)

# ChromaDB
current_dir = os.path.dirname(os.path.abspath(__file__))
chroma_path = os.path.join(current_dir, "chroma_db")
os.makedirs(chroma_path, exist_ok=True)
client = chromadb.PersistentClient(path=chroma_path)
collection = client.get_or_create_collection("legal_contracts")

_embedding_model = None
def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model

# Pydantic models for structured response
class LegalTerm(BaseModel):
    term: str = Field(description="The difficult legal term, e.g. tenant, security deposit, breach, indemnity")
    explanation_english: str = Field(description="Simple, jargon-free English explanation of the term for a common person")
    explanation_tamil: str = Field(description="Simple, conversational Tamil explanation of the term suitable for rural/elderly people")

class BewareAlert(BaseModel):
    alert_title_english: str = Field(description="Short title of the warning/alert in English, e.g., Late Payment Penalty")
    alert_title_tamil: str = Field(description="Short title of the warning/alert in Tamil")
    alert_explanation_english: str = Field(description="Detailed explanation of the risk/alert in English")
    alert_explanation_tamil: str = Field(description="Detailed explanation of the risk/alert in simple Tamil")

class LegalAnalysisResult(BaseModel):
    english_summary: str = Field(description="A clear and simple summary of the document in English")
    tamil_summary: str = Field(description="A clear, conversational summary of the document in simple Tamil (avoid direct translation, suitable for rural/elderly people)")
    risk_score: int = Field(description="The pre-calculated risk score provided in the prompt. MUST match the pre-calculated risk score exactly.")
    risk_explanation_english: str = Field(description="An explanation of why the risk score was assigned in English")
    risk_explanation_tamil: str = Field(description="An explanation of why the risk score was assigned in simple Tamil")
    beware_alerts: List[BewareAlert] = Field(description="List of alerts/warnings found in the document. Only include actual warnings present in the document. Do not invent warnings. If none, return empty list.")
    legal_terms_explained: List[LegalTerm] = Field(description="List of difficult legal terms identified in the document with simple explanations in English and Tamil")

def analyze_document(document_text):
    print("Step 1: Calculating Risk Score...")
    risk_score, detected_risks = calculate_risk(document_text)
    print("Risk Score:", risk_score)

    print("Step 2: Creating Embedding...")
    try:
        model = get_embedding_model()
        query_embedding = model.encode(document_text).tolist()
        print("Step 3: Retrieving Legal Clauses...")
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=1
        )
        docs = results.get("documents", [[]])
        retrieved_context = docs[0][0][:500] if docs and docs[0] else ""
    except Exception as e:
        print("Note on vector retrieval:", e)
        retrieved_context = ""

    print("Step 4: Building Prompt...")
    prompt = LEGAL_ANALYSIS_PROMPT.format(
        document=document_text[:3000],
        context=retrieved_context
    )
    prompt += f"""

PRE-CALCULATED RISK SCORE:
{risk_score}

DETECTED RISKS:
{', '.join(detected_risks)}

IMPORTANT:
Use the provided risk score of {risk_score} for the risk_score field in the JSON response.
Do not generate a new score.
Explain why the score was assigned.
"""

    print("Step 5: Generating Analysis...")
    llm = LLMProvider()
    result = llm.generate_structured(prompt, doc_text=document_text, risk_score=risk_score, detected_risks=detected_risks)
    print("Step 6: Analysis Complete")
    return json.dumps(result, indent=2, ensure_ascii=False)