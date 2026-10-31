import os
import shutil
import json
import uuid
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Local imports
from llm_provider import LLMProvider
from analysis_cache import store_result, get_result
from rag_engine import chunk_and_store, retrieve_chunks
from pdf_processor import extract_text_from_pdf, get_representative_legal_text
from risk_engine import calculate_risk

app = FastAPI(title="AI Legal Document Analyzer")

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

current_dir = os.path.dirname(os.path.abspath(__file__))
# Locate frontend: check current directory first (local run), then ../frontend (Docker run)
if os.path.exists(os.path.join(current_dir, "index.html")):
    frontend_dir = current_dir
elif os.path.exists(os.path.join(current_dir, "..", "frontend", "index.html")):
    frontend_dir = os.path.abspath(os.path.join(current_dir, "..", "frontend"))
else:
    frontend_dir = current_dir

# Initialize LLM provider (Groq / Gemini / Local Engine)
llm = LLMProvider()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    doc_id: str
    question: str

class AnalyzeResponse(BaseModel):
    doc_id: str

class AnalysisResult(BaseModel):
    analysis: dict

class KeyUpdateRequest(BaseModel):
    provider: str
    api_key: str

# ---------------------------------------------------------------------------
# Helper: language detection (simple Unicode/Tanglish heuristic)
# ---------------------------------------------------------------------------
def detect_language(text: str) -> str:
    """Return 'ta' for Tamil or Tanglish, otherwise 'en'."""
    if any("\u0b80" <= ch <= "\u0bff" for ch in text):
        return "ta"
    tanglish_keywords = ["padi", "iruku", "kaasu", "thaan", "pen", "ma", "aan", "vanakkam", "eppadi", "nandri"]
    lowered = text.lower()
    if any(word in lowered for word in tanglish_keywords):
        return "ta"
    return "en"

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/config")
def get_config():
    """Return the active AI engine status."""
    has_openai = bool(llm.openai_client)
    has_groq = bool(llm.groq_client)
    has_gemini = bool(llm.gemini_client)
    if has_openai:
        active_engine = "OpenAI (GPT-4o-mini)"
    elif has_groq:
        active_engine = "Groq (Llama 3.3)"
    elif has_gemini:
        active_engine = "Google Gemini"
    else:
        active_engine = "Built-in Legal Intelligence Engine"

    return {
        "has_openai": has_openai,
        "has_groq": has_groq,
        "has_gemini": has_gemini,
        "active_engine": active_engine
    }

@app.post("/api/set-key")
def update_api_key(req: KeyUpdateRequest):
    """Set OpenAI, Groq, or Gemini API key dynamically."""
    llm.set_api_key(req.provider, req.api_key)
    # Also save to .env for persistence
    env_file = os.path.join(current_dir, ".env")
    provider_up = req.provider.upper()
    if req.api_key.strip().startswith("sk-") or "OPENAI" in provider_up:
        key_name = "OPENAI_API_KEY"
    elif req.api_key.strip().startswith("gsk_") or "GROQ" in provider_up:
        key_name = "GROQ_API_KEY"
    else:
        key_name = "GEMINI_API_KEY"

    try:
        lines = []
        found = False
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    if line.strip().startswith(f"{key_name}="):
                        lines.append(f"{key_name}={req.api_key.strip()}\n")
                        found = True
                    else:
                        lines.append(line)
        if not found:
            lines.append(f"{key_name}={req.api_key.strip()}\n")
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"[main] Failed to save key to .env: {e}")

    return {"status": "success", "message": f"{key_name} updated successfully."}

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_pdf(file: UploadFile = File(...)):
    """Upload PDF, chunk, embed, store in Chroma, and run analysis.
    Returns a document identifier for later queries.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # Save uploaded file with a safe unique name
        safe_name = f"{uuid.uuid4()}_{os.path.basename(file.filename)}"
        file_path = os.path.join(UPLOAD_FOLDER, safe_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Chunk the PDF and embed into vector database
        try:
            doc_id = chunk_and_store(file_path)
        except Exception as e:
            print(f"[main] Note on chunk_and_store: {e}")
            doc_id = str(uuid.uuid4())

        # Extract full text for legal analysis
        full_text = extract_text_from_pdf(file_path)
        if not full_text or not full_text.strip():
            raise HTTPException(status_code=400, detail="Failed to extract text from PDF. The document may be empty or an unreadable scanned image.")

        # Calculate deterministic risk score using risk engine
        risk_score, detected_risks = calculate_risk(full_text)

        # Get representative text subset for LLM prompt
        representative_text = get_representative_legal_text(full_text)

        # Build prompt for LLM
        analysis_prompt = f"""
You are an AI legal assistant. Analyze the following legal document and output a JSON object **exactly** with these keys:

- english_summary
- tamil_summary
- risk_score (integer 0‑100)
- risk_explanation_english
- risk_explanation_tamil
- beware_alerts: array of objects with alert_title_english, alert_title_tamil, alert_explanation_english, alert_explanation_tamil
- legal_terms_explained: array of objects with term, explanation_english, explanation_tamil

Write in simple, user‑friendly language suitable for non‑technical, rural users. Tamil strings must be natural spoken Tamil, not a literal translation. Crucial: Do NOT output repetitive syllables, words, or gibberish. Keep sentences coherent, natural, and informative.

CRITICAL LENGTH CONSTRAINTS:
- 'english_summary' and 'tamil_summary' must be at most 2 sentences.
- 'risk_explanation_english' and 'risk_explanation_tamil' must be at most 2 sentences.
- Each alert's 'alert_explanation_english' and 'alert_explanation_tamil' must be at most 1 sentence.
- Each legal term's explanation must be at most 1 sentence.
Keep all text extremely concise and to the point to prevent output truncation.

PRE-CALCULATED RISK SCORE:
{risk_score}

DETECTED RISKS:
{', '.join(detected_risks) if detected_risks else 'None'}

IMPORTANT:
Use the provided risk score of {risk_score} for the 'risk_score' field in the JSON response. Do not generate a new score. Explain in both English and Tamil ('risk_explanation_english' and 'risk_explanation_tamil') why this score was assigned based on the detected risks.

Document text:
{representative_text}
"""
        # Generate analysis with automatic provider fallback
        analysis_json = llm.generate_structured(
            analysis_prompt,
            doc_text=full_text,
            risk_score=risk_score,
            detected_risks=detected_risks
        )

        # Validate that essential keys exist
        required_keys = [
            "english_summary", "tamil_summary", "risk_score",
            "risk_explanation_english", "risk_explanation_tamil",
            "beware_alerts", "legal_terms_explained"
        ]
        fallback_data = None
        for key in required_keys:
            if key not in analysis_json or not analysis_json[key]:
                if fallback_data is None:
                    fallback_data = llm._fallback_analysis(full_text, risk_score, detected_risks)
                analysis_json[key] = fallback_data.get(key)

        # Ensure risk_score is integer
        analysis_json["risk_score"] = risk_score

        # Cache the analysis result for retrieval
        store_result(doc_id, analysis_json)

        return {"doc_id": doc_id}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[main] Error in analyze_pdf: {e}")
        traceback.print_exc()
        # Fallback to local analysis on unexpected error so user never gets 500
        try:
            doc_id = str(uuid.uuid4())
            full_text = extract_text_from_pdf(file_path) if 'file_path' in locals() else ""
            risk_score, detected_risks = calculate_risk(full_text)
            analysis_json = llm._fallback_analysis(full_text, risk_score, detected_risks)
            store_result(doc_id, analysis_json)
            return {"doc_id": doc_id}
        except Exception as final_e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/analysis/{doc_id}", response_model=AnalysisResult)
async def get_analysis(doc_id: str):
    """Return the cached analysis JSON for a given document identifier."""
    result = get_result(doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found for this document.")
    return {"analysis": result}

@app.post("/chat")
async def chat_pdf(request: ChatRequest):
    """RAG chat: retrieve relevant chunks, build prompt, ask LLM.
    The answer language matches the detected language of the user question.
    """
    if not request.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Retrieve relevant chunks
    try:
        retrieved = retrieve_chunks(request.doc_id, request.question, k=5)
        context_text = "\n---\n".join([chunk for chunk, _ in retrieved])
    except Exception as e:
        print(f"[main] Note on retrieve_chunks: {e}")
        context_text = ""

    # Detect language of question
    lang = detect_language(request.question)
    language_name = "Tamil" if lang == "ta" else "English"

    # Build RAG prompt
    rag_prompt = f"""
You are a helpful AI legal assistant. Answer the following question **in {language_name}**, using only the provided context. Keep the answer simple, explain the meaning, importance, and any cautions. Do **not** fabricate information not present in the context.

Context:
{context_text}

Question: {request.question}
"""
    try:
        answer = llm.generate(rag_prompt)
    except Exception as e:
        print(f"[main] LLM chat failed: {e}")
        if lang == "ta":
            answer = "உங்கள் கேள்விக்கான தகவல் பரிசீலிக்கப்பட்டது. ஆவணத்தின் குறிப்பிட்ட பகுதிகளை சரிபார்த்து அதன்படி செயல்படவும்."
        else:
            answer = f"Based on the document context, please review the specific provisions relating to '{request.question}' carefully."

    return {"answer": answer}

# ---------------------------------------------------------------------------
# Static file serving (frontend)
# ---------------------------------------------------------------------------
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def home():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Legal Document Analyzer Running."}

@app.get("/app.js")
def get_app_js():
    js_path = os.path.join(frontend_dir, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")

@app.get("/style.css")
def get_style_css():
    css_path = os.path.join(frontend_dir, "style.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="style.css not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)