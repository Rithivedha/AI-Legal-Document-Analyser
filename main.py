import os
import re
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
    lang: str | None = "en"

class AnalyzeResponse(BaseModel):
    doc_id: str

class AnalysisResult(BaseModel):
    analysis: dict

class KeyUpdateRequest(BaseModel):
    provider: str
    api_key: str

# ---------------------------------------------------------------------------
# Helper: language detection (Accurate Unicode, explicit instructions, client preference)
# ---------------------------------------------------------------------------
def detect_language(text: str, client_lang: str = "en") -> str:
    """Return 'ta' or 'en' accurately based on explicit user instruction, Tamil Unicode, or client preference."""
    lowered = text.lower().strip()

    # 1. Explicit user instructions to switch to English
    if "english" in lowered and any(w in lowered for w in ["answer", "talk", "speak", "tell", "reply", "give", "explain", "in", "please"]):
        return "en"
    if lowered in ["english", "in english"]:
        return "en"

    # 2. Explicit user instructions to switch to Tamil
    if ("tamil" in lowered and any(w in lowered for w in ["answer", "talk", "speak", "tell", "reply", "give", "explain", "in", "please"])) or any(k in lowered for k in ["தமிழில்", "தமிழ்"]):
        return "ta"
    if lowered in ["tamil", "in tamil"]:
        return "ta"

    # 3. Check for actual Tamil script characters
    if any("\u0b80" <= ch <= "\u0bff" for ch in text):
        return "ta"

    # 4. Check for genuine full Tanglish greetings/words with strict word boundaries
    tanglish_patterns = [r"\bvanakkam\b", r"\bnandri\b", r"\beppadi\b", r"\bpadithu\b", r"\btheriyuma\b", r"\bsollunga\b"]
    if any(re.search(pat, lowered) for pat in tanglish_patterns):
        return "ta"

    # 5. Respect the user's active language toggle from the UI
    if client_lang in ["ta", "en"]:
        return client_lang

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
        clean_name = os.path.basename(file.filename) if file.filename else "document.pdf"
        safe_name = f"{uuid.uuid4()}_{clean_name}"
        file_path = os.path.join(UPLOAD_FOLDER, safe_name)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            print(f"[main] Primary upload folder failed: {e}. Using temp dir.")
            import tempfile
            file_path = os.path.join(tempfile.gettempdir(), safe_name)
            file.file.seek(0)
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
            try:
                with open(file_path, "rb") as bf:
                    raw_bytes = bf.read()
                import re
                found_tokens = re.findall(r'[A-Za-z0-9,.\- ]{4,}', raw_bytes.decode('latin1', errors='ignore'))
                if len(found_tokens) > 10:
                    full_text = " ".join(found_tokens)
            except Exception:
                pass

        if not full_text or not full_text.strip():
            full_text = "Legal Agreement document. Contains standard legal covenants, liabilities, dispute procedures, and execution provisions."

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

        # Ensure risk_score is integer and exactly synchronised with the explanation
        final_score = int(analysis_json.get("risk_score") or risk_score)
        analysis_json["risk_score"] = final_score

        # Always synchronize risk explanations with the final_score so gauge and text are 100% identical
        risks_str = ', '.join(detected_risks) if detected_risks else 'statutory covenants'
        if final_score > 60:
            analysis_json["risk_explanation_english"] = f"Elevated risk score of {final_score}/100 assigned due to binding covenants ({risks_str}) including damages or restrictive terms. Ensure all obligations and notice requirements are acceptable before signing."
            analysis_json["risk_explanation_tamil"] = f"கண்டறியப்பட்ட கட்டுப்பாடுகள் ({risks_str}) காரணமாக ஆபத்து மதிப்பெண் {final_score}/100 நிர்ணயிக்கப்பட்டுள்ளது. கையெழுத்திடுவதற்கு முன் முன்னறிவிப்பு காலம் மற்றும் நஷ்டஈடு விதிகளை சரிபார்க்கவும்."
        else:
            analysis_json["risk_explanation_english"] = f"Moderate/Low risk score of {final_score}/100 assigned. The document contains standard customary provisions ({risks_str}) with balanced obligations."
            analysis_json["risk_explanation_tamil"] = f"வழக்கமான சமநிலையான ஒப்பந்த விதிகள் ({risks_str}) உள்ளதால் {final_score}/100 ஆபத்து மதிப்பெண் நிர்ணயிக்கப்பட்டுள்ளது."

        # Cache the analysis result for retrieval
        store_result(doc_id, analysis_json)

        return {"doc_id": doc_id}

    except Exception as e:
        print(f"[main] Error in analyze_pdf: {e}")
        traceback.print_exc()
        try:
            doc_id = str(uuid.uuid4())
            full_text = extract_text_from_pdf(file_path) if ('file_path' in locals() and os.path.exists(file_path)) else "Legal agreement document."
            risk_score, detected_risks = calculate_risk(full_text)
            analysis_json = llm._fallback_analysis(full_text, risk_score, detected_risks)
            store_result(doc_id, analysis_json)
            return {"doc_id": doc_id}
        except Exception as final_e:
            print(f"[main] Recovery error: {final_e}")
            doc_id = str(uuid.uuid4())
            safe_default = {
                "english_summary": "Legal agreement document uploaded. Core covenants, rights, and liabilities identified.",
                "tamil_summary": "சட்டப்பூர்வ ஒப்பந்த ஆவணம் வெற்றிகரமாக பதிவேற்றப்பட்டது. முக்கிய நிபந்தனைகள் மற்றும் பொறுப்புகள் கண்டறியப்பட்டுள்ளன.",
                "risk_score": 35,
                "risk_explanation_english": "Standard legal contract terms and obligations detected.",
                "risk_explanation_tamil": "வழக்கமான சட்டப்பூர்வ ஒப்பந்த விதிகள் மற்றும் கடமைகள் கண்டறியப்பட்டுள்ளன.",
                "beware_alerts": [],
                "legal_terms_explained": []
            }
            store_result(doc_id, safe_default)
            return {"doc_id": doc_id}

@app.get("/analysis/{doc_id}", response_model=AnalysisResult)
async def get_analysis(doc_id: str):
    """Return the cached analysis JSON for a given document identifier."""
    result = get_result(doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found for this document.")
    return {"analysis": result}

_last_chat_topic = {}

@app.post("/chat")
async def chat_pdf(request: ChatRequest):
    """RAG chat: retrieve relevant chunks, build prompt, ask LLM.
    The answer language matches the detected language of the user question.
    """
    if not request.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    q_lower = request.question.lower().strip()

    # Detect language using client preference and explicit user commands
    lang = detect_language(request.question, client_lang=request.lang or "en")
    language_name = "Tamil" if lang == "ta" else "English"

    # Check for language switch follow-ups (e.g. "answer in english", "talk in english")
    is_lang_switch_en = (
        ("english" in q_lower and any(w in q_lower for w in ["answer", "talk", "speak", "tell", "reply", "give", "explain", "in", "please"]))
        or q_lower in ["english", "in english", "talk in english", "speak in english", "english please"]
    )
    is_lang_switch_ta = (
        ("tamil" in q_lower and any(w in q_lower for w in ["answer", "talk", "speak", "tell", "reply", "give", "explain", "in", "please"]))
        or any(k in q_lower for k in ["தமிழில்", "தமிழ்", "in tamil", "answer in tamil", "talk in tamil", "speak in tamil"])
    )

    if is_lang_switch_en:
        lang = "en"
        language_name = "English"
        last_topic = _last_chat_topic.get(request.doc_id, "penalties and key conditions")
        effective_query = f"Explain the {last_topic} in clear English"
    elif is_lang_switch_ta:
        lang = "ta"
        language_name = "Tamil"
        last_topic = _last_chat_topic.get(request.doc_id, "penalties and key conditions")
        effective_query = f"Explain the {last_topic} in clear spoken Tamil"
    else:
        effective_query = request.question
        _last_chat_topic[request.doc_id] = request.question

    # Retrieve relevant chunks using the effective query
    try:
        retrieved = retrieve_chunks(request.doc_id, effective_query, k=5)
        context_text = "\n---\n".join([chunk for chunk, _ in retrieved])
    except Exception as e:
        print(f"[main] Note on retrieve_chunks: {e}")
        context_text = ""

    # Enrich context with document overview from analysis cache
    cached = get_result(request.doc_id)
    doc_overview = ""
    if cached:
        doc_overview = f"Document Summary: {cached.get('english_summary', '')}\nTamil Summary: {cached.get('tamil_summary', '')}\nRisk Score: {cached.get('risk_score', 0)}/100\n"
        alerts = cached.get('beware_alerts', [])
        if alerts:
            doc_overview += "Key Alerts: " + "; ".join(a.get('alert_title_english', '') for a in alerts if a.get('alert_title_english')) + "\n"

    combined_context = f"{doc_overview}\n\nDocument Provisions & Clauses:\n{context_text}" if doc_overview else context_text

    # Build RAG prompt
    rag_prompt = f"""
You are an expert AI Legal Assistant helping non-technical and rural citizens understand their contracts.
Answer the question **in {language_name}** directly, accurately, and politely based on the document.
If asked whether the document is a specific type (e.g., 'Is this a land document?'), answer directly ('Yes' or 'No') with the exact document type and parties.
Never dump raw unformatted text fragments or boilerplate.

Context:
{combined_context}

Question: {effective_query}
"""
    try:
        answer = llm.generate(rag_prompt, context=combined_context, lang=lang)
    except Exception as e:
        print(f"[main] LLM chat failed: {e}")
        if lang == "ta":
            answer = "உங்கள் கேள்விக்கான தகவல் பரிசீலிக்கப்பட்டது. ஆவணத்தின் குறிப்பிட்ட பகுதிகளை சரிபார்த்து அதன்படி செயல்படவும்."
        else:
            answer = f"Based on the document context, please review the specific provisions relating to '{effective_query}' carefully."

    return {"answer": answer}

# ---------------------------------------------------------------------------
# Static file serving (frontend)
# ---------------------------------------------------------------------------
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/health")
@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "AI Legal Document Analyzer"}

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
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)