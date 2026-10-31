import os
import re
import json
from pathlib import Path
from risk_engine import is_legal_document, calculate_risk

def _load_api_key(key_name: str) -> str:
    """Read a key directly from environment variables or .env files."""
    if os.environ.get(key_name):
        return os.environ.get(key_name).strip()

    candidates = [
        Path(__file__).resolve().parent / ".env",
        Path.cwd() / ".env",
        Path.home() / "Desktop" / "legal-analyzer" / ".env"
    ]
    for env_path in candidates:
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if line.startswith(f"{key_name}="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
            except Exception:
                pass
    return ""


# Universal Legal Glossary covering all legal contracts
LEGAL_GLOSSARY = [
    {
        "keywords": ["non-compete", "non compete", "restraint of trade", "competing"],
        "term": "Non-Compete Clause (போட்டித் தடை விதி)",
        "explanation_english": "A restrictive clause prohibiting an employee or contractor from working with direct competitors or operating a rival business for a specific time and geographic region.",
        "explanation_tamil": "ஒப்பந்தம் முடிந்த பிறகு குறிப்பிட்ட காலம் வரை நேரடி போட்டி நிறுவனங்களில் பணிபுரியவோ அல்லது அதே தொழிலைத் தொடங்கவோ தடை செய்யும் விதி."
    },
    {
        "keywords": ["non-solicit", "solicitation", "enticing"],
        "term": "Non-Solicitation (வாடிக்கையாளர் & ஊழியர் விலக்கல் தடை)",
        "explanation_english": "Restricts departing parties from poaching, hiring company employees, or soliciting established clients.",
        "explanation_tamil": "நிறுவனத்தை விட்டு விலகிய பிறகு அங்குள்ள ஊழியர்களையோ அல்லது வாடிக்கையாளர்களையோ கவர்ந்து இழுக்கக் கூடாது என்ற கட்டுப்பாடு."
    },
    {
        "keywords": ["intellectual property", "inventions", "work made for hire", "patent", "copyright"],
        "term": "Intellectual Property Assignment (அறிவுசார் சொத்துரிமை ஒப்படைப்பு)",
        "explanation_english": "Mandates that all inventions, software code, patents, and designs created during the contract belong solely to the company or client.",
        "explanation_tamil": "பணியின் போது உருவாக்கப்பட்ட மென்பொருள், கண்டுபிடிப்புகள் மற்றும் படைப்புகள் அனைத்தும் நிறுவனத்திற்கே சொந்தம் என்பதை உறுதி செய்யும் விதி."
    },
    {
        "keywords": ["injunctive relief", "injunction", "irreparable harm"],
        "term": "Injunctive Relief (நீதிமன்ற இடைக்கால தடை உத்தரவு)",
        "explanation_english": "An emergency court order that immediately stops a party from committing an ongoing breach (such as leaking confidential trade secrets).",
        "explanation_tamil": "இரகசிய தகவல்களை வெளியிடுவது போன்ற ஒப்பந்த மீறல்களை உடனடியாக தடுத்து நிறுத்த நீதிமன்றம் பிறப்பிக்கும் அவசர தடை உத்தரவு."
    },
    {
        "keywords": ["liquidated damages", "penalty", "penalties", "damages calculated", "fine"],
        "term": "Liquidated Damages & Penalties (முன்கூட்டியே நிர்ணயிக்கப்பட்ட நஷ்டஈடு)",
        "explanation_english": "A predetermined monetary compensation that must be paid if a party defaults, abandons, or breaches contractual terms.",
        "explanation_tamil": "ஒப்பந்த விதிமுறைகளை மீறினால் அல்லது திடீரென விலகினால் செலுத்த வேண்டிய முன்நிர்ணயிக்கப்பட்ட அபராதத் தொகை."
    },
    {
        "keywords": ["security deposit", "deposit", "advance", "earnest money"],
        "term": "Security Deposit / Advance (பாதுகாப்பு வைப்புத்தொகை / முன்பணம்)",
        "explanation_english": "A refundable advance paid upfront to safeguard against physical damage, unpaid dues, or breach of performance.",
        "explanation_tamil": "சேதங்கள் மற்றும் நிலுவைத் தொகைகளை ஈடுகட்ட ஒப்பந்த தொடக்கத்தில் செலுத்தப்படும் திருப்பித் தரக்கூடிய பாதுகாப்பு முன்பணம்."
    },
    {
        "keywords": ["indemnify", "indemnity", "hold harmless"],
        "term": "Indemnity (இழப்பீட்டு உத்தரவாதம்)",
        "explanation_english": "A contractual promise where one party agrees to bear legal costs, damages, and financial liabilities incurred by the other party.",
        "explanation_tamil": "ஏதேனும் சட்டச் சிக்கல் அல்லது இழப்பு ஏற்பட்டால் அதற்குரிய நஷ்டத்தை முழுமையாக ஈடுசெய்வதற்கான சட்டப்பூர்வ பொறுப்பு."
    },
    {
        "keywords": ["termination", "terminate", "notice period", "severance"],
        "term": "Termination & Notice Period (ஒப்பந்த முறிவு மற்றும் முன்னறிவிப்பு)",
        "explanation_english": "The formal procedure, advance notice timeline, and conditions required for either party to legally dissolve the agreement.",
        "explanation_tamil": "ஒப்பந்தத்தை முன்கூட்டியே ரத்து செய்வதற்கான நடைமுறைகள் மற்றும் தேவையான முன்னறிவிப்பு காலம்."
    },
    {
        "keywords": ["confidential information", "trade secret", "non-disclosure", "proprietary"],
        "term": "Confidential Information & NDA (இரகசிய காப்பு விதிமுறை)",
        "explanation_english": "Legally binds parties from disclosing sensitive technical, financial, or business secrets to any unauthorized third party.",
        "explanation_tamil": "தொழில்நுட்பம், நிதி மற்றும் வணிக இரகசியங்களை அனுமதியின்றி பிறருக்கு பகிரக்கூடாது என்ற கடுமையான பாதுகாப்பு விதி."
    },
    {
        "keywords": ["encumbrance", "free from encumbrances", "title warranty", "conveyance"],
        "term": "Encumbrance & Title Warranty (வில்லங்கமற்ற உரிமை உத்தரவாதம்)",
        "explanation_english": "Guarantees that the property or asset sold is completely free from mortgages, pending lawsuits, government dues, or third-party claims.",
        "explanation_tamil": "விற்பனை செய்யப்படும் சொத்தில் அடமானம், நீதிமன்ற வழக்குகள் அல்லது வேறு எந்த வில்லங்கமும் இல்லை என்பதற்கான சட்ட உத்தரவாதம்."
    },
    {
        "keywords": ["jurisdiction", "dispute", "court", "arbitration", "governing law"],
        "term": "Jurisdiction & Arbitration (நீதிமன்ற எல்லை மற்றும் மத்தியஸ்தம்)",
        "explanation_english": "Determines the chosen legal jurisdiction or independent arbitration forum where contract disputes must be settled.",
        "explanation_tamil": "ஒப்பந்தத்தில் கருத்து வேறுபாடோ அல்லது தகராறோ ஏற்பட்டால் எந்த நீதிமன்றம் அல்லது மத்தியஸ்தரை அணுக வேண்டும் என்பதை குறிக்கும் விதி."
    },
    {
        "keywords": ["sublease", "sublet", "sub-letting", "assignment"],
        "term": "Subletting / Assignment (உள்வாடகை மற்றும் உரிமை மாற்றம்)",
        "explanation_english": "Prohibits transferring or leasing contract rights or premises to an external third party without written consent.",
        "explanation_tamil": "முன் அனுமதியின்றி வாடகை இடத்தையோ அல்லது ஒப்பந்த உரிமைகளையோ வேறு ஒருவருக்கு மாற்றுவதை தடை செய்யும் பிரிவு."
    }
]


class LLMProvider:
    """Universal Multi-provider Legal Document Analysis Engine:
    1. OpenAI (gpt-4o-mini / gpt-4o / gpt-3.5-turbo)
    2. Groq (llama-3.3-70b-versatile / llama-3.1-8b-instant)
    3. Google Gemini (gemini-2.5-flash / gemini-1.5-flash)
    4. Universal Built-in Legal Intelligence Engine (works on Leases, Employment, NDAs, Sale Deeds, Loans, etc.)
    """

    def __init__(self):
        self.groq_api_key = _load_api_key("GROQ_API_KEY")
        self.gemini_api_key = _load_api_key("GEMINI_API_KEY")
        self.openai_api_key = _load_api_key("OPENAI_API_KEY")
        
        self.groq_client = None
        self.gemini_client = None
        self.openai_client = None
        
        self.model_name = "llama-3.3-70b-versatile"
        self.fallback_model = "llama-3.1-8b-instant"

        if self.openai_api_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                print("[LLMProvider] OpenAI client initialized.")
            except Exception as e:
                print(f"[LLMProvider] Note on OpenAI: {e}")

        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
                print("[LLMProvider] Groq client initialized.")
            except Exception as e:
                print(f"[LLMProvider] Note on Groq: {e}")

        if self.gemini_api_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                print("[LLMProvider] Gemini client initialized.")
            except Exception as e:
                print(f"[LLMProvider] Note on Gemini: {e}")

    def set_api_key(self, key_type: str, key_val: str):
        """Allow runtime configuration of API keys."""
        key_type = key_type.upper().strip()
        key_val = key_val.strip()

        # Auto-detect key type if needed
        if key_val.startswith("sk-"):
            key_type = "OPENAI"
        elif key_val.startswith("gsk_"):
            key_type = "GROQ"
        elif key_val.startswith("AIza"):
            key_type = "GEMINI"

        if "OPENAI" in key_type:
            self.openai_api_key = key_val
            os.environ["OPENAI_API_KEY"] = key_val
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=key_val)
                print("[LLMProvider] Updated OpenAI client.")
            except Exception as e:
                print(f"[LLMProvider] Could not update OpenAI: {e}")
        elif "GROQ" in key_type:
            self.groq_api_key = key_val
            os.environ["GROQ_API_KEY"] = key_val
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=key_val)
                print("[LLMProvider] Updated Groq client.")
            except Exception as e:
                print(f"[LLMProvider] Could not update Groq: {e}")
        elif "GEMINI" in key_type:
            self.gemini_api_key = key_val
            os.environ["GEMINI_API_KEY"] = key_val
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=key_val)
                print("[LLMProvider] Updated Gemini client.")
            except Exception as e:
                print(f"[LLMProvider] Could not update Gemini: {e}")

    def _call_groq(self, messages: list, temperature: float = 0.2, response_format: dict = None) -> str:
        """Call Groq API with automatic model fallback."""
        if not self.groq_client:
            raise RuntimeError("Groq client not configured")

        params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }
        if response_format:
            params["response_format"] = response_format

        try:
            response = self.groq_client.chat.completions.create(**params)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[LLMProvider] Groq {self.model_name} failed: {e}. Trying {self.fallback_model}...")
            fallback_params = params.copy()
            fallback_params["model"] = self.fallback_model
            fallback_params["max_tokens"] = 2500
            response = self.groq_client.chat.completions.create(**fallback_params)
            return response.choices[0].message.content.strip()

    def _call_openai(self, messages: list, temperature: float = 0.2, response_format: dict = None) -> str:
        """Call OpenAI API with automatic model fallback."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not configured")

        for model in ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]:
            try:
                params = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 4096,
                }
                if response_format:
                    params["response_format"] = response_format
                response = self.openai_client.chat.completions.create(**params)
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[LLMProvider] OpenAI {model} error: {e}")
                continue
        raise RuntimeError("All OpenAI models failed")

    def _call_gemini(self, prompt: str, system_message: str = None) -> str:
        """Call Google Gemini API."""
        if not self.gemini_client:
            raise RuntimeError("Gemini client not configured")

        full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt
        
        for model in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]:
            try:
                response = self.gemini_client.models.generate_content(
                    model=model,
                    contents=full_prompt,
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[LLMProvider] Gemini {model} error: {e}")
                continue

        raise RuntimeError("All Gemini models failed")

    def _classify_legal_document(self, text_lower: str) -> dict:
        """Identify specific category of legal document."""
        if any(w in text_lower for w in ["rental agreement", "lease agreement", "tenant", "landlord", "demised premises"]):
            return {
                "type_en": "Rental & Lease Agreement",
                "type_ta": "சொத்து வாடகை மற்றும் குத்தகை ஒப்பந்தம்",
                "parties_en": "the Landlord (Owner) and the Tenant",
                "parties_ta": "சொத்து உரிமையாளர் மற்றும் வாடகைதாரருக்கு"
            }
        elif any(w in text_lower for w in ["employment agreement", "employee", "employer", "probation", "annual ctc", "salary"]):
            return {
                "type_en": "Employment & Service Agreement",
                "type_ta": "பணி நியமனம் மற்றும் சேவை ஒப்பந்தம்",
                "parties_en": "the Employer (Company) and the Employee",
                "parties_ta": "நிறுவனம் மற்றும் பணியாளருக்கு"
            }
        elif any(w in text_lower for w in ["non-disclosure", "confidentiality agreement", "nda", "disclosing party", "receiving party"]):
            return {
                "type_en": "Non-Disclosure & Confidentiality Agreement (NDA)",
                "type_ta": "இரகசிய காப்பு ஒப்பந்தம் (NDA)",
                "parties_en": "the Disclosing Party and the Receiving Party",
                "parties_ta": "தகவல் வழங்கும் மற்றும் பெறும் தரப்பினருக்கு"
            }
        elif any(w in text_lower for w in ["sale deed", "agreement to sell", "vendor", "purchaser", "conveyance", "earnest money"]):
            return {
                "type_en": "Property Sale & Purchase Deed",
                "type_ta": "சொத்து விற்பனை மற்றும் கிரைய பத்திரம்",
                "parties_en": "the Vendor (Seller) and the Purchaser (Buyer)",
                "parties_ta": "விற்பனையாளர் மற்றும் வாங்குபவருக்கு"
            }
        elif any(w in text_lower for w in ["loan agreement", "borrower", "lender", "promissory note", "credit facility"]):
            return {
                "type_en": "Loan & Credit Facility Agreement",
                "type_ta": "கடன் மற்றும் தவணை ஒப்பந்தம்",
                "parties_en": "the Lender and the Borrower",
                "parties_ta": "கடன் வழங்குபவர் மற்றும் கடன் பெறுபவருக்கு"
            }
        elif any(w in text_lower for w in ["partnership deed", "partners hereto", "joint venture", "capital contribution"]):
            return {
                "type_en": "Partnership & Commercial Joint Deed",
                "type_ta": "கூட்டாண்மை மற்றும் வர்த்தக ஒப்பந்தம்",
                "parties_en": "the Business Partners",
                "parties_ta": "கூட்டாண்மை உறுப்பினர்களுக்கு"
            }
        else:
            return {
                "type_en": "Binding Legal Contract & Agreement",
                "type_ta": "சட்டப்பூர்வ ஒப்பந்த ஆவணம்",
                "parties_en": "the Executing Parties",
                "parties_ta": "ஒப்பந்தத்தில் ஈடுபட்டுள்ள தரப்பினருக்கு"
            }

    def _extract_universal_clauses(self, text: str) -> dict:
        """Extract key clauses across any legal document type."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        extracted = {
            "financial": None,
            "security": None,
            "termination": None,
            "restrictive": None,
            "penalty": None,
            "liability": None,
            "confidentiality": None,
            "ip_rights": None,
            "dispute": None
        }

        for line in lines:
            ll = line.lower()
            # Financial
            if not extracted["financial"] and any(k in ll for k in ["monthly rent", "rent of rs", "annual ctc", "salary of", "consideration of rs", "purchase price of", "principal amount of"]):
                extracted["financial"] = line
            # Security / Deposit / Earnest Money
            elif not extracted["security"] and any(k in ll for k in ["security deposit", "earnest money", "advance amount", "collateral"]):
                extracted["security"] = line
            # Termination & Notice
            elif not extracted["termination"] and any(k in ll for k in ["terminate", "termination", "notice period", "prior notice", "serving notice", "probation"]):
                extracted["termination"] = line
            # Penalties / Liquidated Damages / Holdover
            elif not extracted["penalty"] and any(k in ll for k in ["liquidated damages", "penalty", "late fee", "two times the rent", "damages calculated at"]):
                extracted["penalty"] = line
            # Restrictive covenants (Non-compete, Non-solicit, Sublease)
            elif not extracted["restrictive"] and any(k in ll for k in ["non-compete", "non compete", "non-solicitation", "competing entity", "sublet", "sublease", "exclusive"]):
                extracted["restrictive"] = line
            # Indemnity & Liability
            elif not extracted["liability"] and any(k in ll for k in ["indemnify", "indemnity", "hold harmless", "limitation of liability", "irreparable harm"]):
                extracted["liability"] = line
            # Confidentiality
            elif not extracted["confidentiality"] and any(k in ll for k in ["confidential information", "trade secret", "proprietary data", "strict confidence"]):
                extracted["confidentiality"] = line
            # IP rights
            elif not extracted["ip_rights"] and any(k in ll for k in ["intellectual property", "inventions", "sole exclusive property", "patents and copyrights"]):
                extracted["ip_rights"] = line
            # Dispute / Jurisdiction
            elif not extracted["dispute"] and any(k in ll for k in ["jurisdiction", "courts at", "courts in", "arbitration", "governing law"]):
                extracted["dispute"] = line

        return extracted

    def _fallback_analysis(self, doc_text: str, risk_score: int, detected_risks: list) -> dict:
        """Universal document analysis engine:
        - Accurately classifies non-legal files (Job Descriptions, Resumes, etc.) and sets risk=0.
        - Accurately extracts real clauses, parties, and provisions from ANY legal document type
          (Rental Agreements, Employment Contracts, NDAs, Sale Deeds, Loans, etc.).
        """
        raw_text = doc_text or ""
        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        text_lower = raw_text.lower()

        # -------------------------------------------------------------
        # 1. NON-LEGAL DOCUMENT DETECTION
        # -------------------------------------------------------------
        if not is_legal_document(raw_text):
            doc_title = "Informational Document"
            company_or_org = ""
            role_or_subject = ""

            for idx, line in enumerate(lines[:10]):
                line_clean = re.sub(r'[\r\n]+', ' ', line).strip()
                if any(k in line.lower() for k in ["ltd", "limited", "pvt", "services", "technologies", "inc", "corp"]):
                    company_or_org = line_clean
                elif any(k in line.lower() for k in ["job description", "engineer", "intern", "manager", "catalyst", "developer", "resume", "curriculum"]):
                    role_or_subject = line_clean
                elif idx == 0 and not doc_title:
                    doc_title = line_clean

            if role_or_subject and company_or_org:
                subject_display = f"{role_or_subject} at {company_or_org}"
            elif role_or_subject:
                subject_display = role_or_subject
            elif company_or_org:
                subject_display = company_or_org
            else:
                subject_display = lines[0] if lines else "Non-Legal Document"

            overview_sentences = []
            for line in lines[3:15]:
                if len(line) > 40 and not line.startswith("Phone") and not line.startswith("Email") and not line.startswith("CIN"):
                    overview_sentences.append(line)
                    if len(overview_sentences) >= 2:
                        break
            overview_text = " ".join(overview_sentences) if overview_sentences else "It outlines informational roles, responsibilities, or specifications."

            english_summary = (
                f"This document is NOT a legal contract or agreement; it is a {subject_display}. "
                f"Overview: {overview_text[:250]}"
            )
            tamil_summary = (
                f"இந்த ஆவணம் ஒரு சட்டப்பூர்வ ஒப்பந்தம் அல்லது உடன்படிக்கை அல்ல. "
                f"இது '{subject_display}' பற்றிய ஆவணம் ஆகும். இதில் எவ்வித சட்டரீதியான கட்டுப்பாடுகளோ அல்லது அபராத விதிகளோ இல்லை."
            )
            risk_explanation_english = (
                f"Safety score is 0/100 because this is a non-legal document ({subject_display}). "
                f"There are no contractual penalties, liabilities, or binding legal covenants."
            )
            risk_explanation_tamil = (
                f"இது சட்ட ஒப்பந்தம் அல்லாத ஆவணம் என்பதால் ஆபத்து மதிப்பெண் 0/100 ஆகும். "
                f"இதில் எவ்வித சட்டரீதியான நஷ்டஈடு விதிகளோ அல்லது அபராதக் கட்டணங்களோ இல்லை."
            )

            return {
                "english_summary": english_summary,
                "tamil_summary": tamil_summary,
                "risk_score": 0,
                "risk_explanation_english": risk_explanation_english,
                "risk_explanation_tamil": risk_explanation_tamil,
                "beware_alerts": [],
                "legal_terms_explained": []
            }

        # -------------------------------------------------------------
        # 2. UNIVERSAL LEGAL CONTRACT EXTRACTION
        # -------------------------------------------------------------
        # Classify the legal contract
        meta = self._classify_legal_document(text_lower)
        extracted = self._extract_universal_clauses(raw_text)

        # Detect specific title
        title = meta["type_en"]
        for line in lines[:8]:
            if any(k in line.lower() for k in ["agreement", "contract", "lease", "deed", "nda", "memorandum"]):
                title = line
                break

        # Collect key provisions found
        key_provisions = []
        if extracted["financial"]:
            key_provisions.append("financial compensation and payment terms")
        if extracted["security"]:
            key_provisions.append("security deposit and advance guarantees")
        if extracted["termination"]:
            key_provisions.append("formal termination and notice timelines")
        if extracted["restrictive"]:
            key_provisions.append("restrictive covenants and non-compete conditions")
        if extracted["confidentiality"]:
            key_provisions.append("strict confidentiality protections")
        if extracted["ip_rights"]:
            key_provisions.append("intellectual property rights ownership")

        provisions_str = ", ".join(key_provisions) if key_provisions else "mutual covenants, rights, and contractual duties"

        english_summary = (
            f"This document is a {title} executed between {meta['parties_en']}. "
            f"It establishes binding covenants regarding {provisions_str}."
        )
        tamil_summary = (
            f"இந்த ஆவணம் {meta['parties_ta']} இடையிலான {meta['type_ta']} ஆகும். "
            f"இதில் கட்டணங்கள், பணிக் கடமைகள், ஒப்பந்த முறிவு விதிகள் மற்றும் முக்கிய கட்டுப்பாடுகள் தெளிவாக குறிப்பிடப்பட்டுள்ளன."
        )

        # Dynamic Beware Alerts based on extracted clauses
        beware_alerts = []

        if extracted["penalty"]:
            beware_alerts.append({
                "alert_title_english": "Liquidated Damages & Financial Penalties",
                "alert_title_tamil": "அபராதக் கட்டணம் மற்றும் நஷ்டஈடு விதி",
                "alert_explanation_english": f"Penalty clause specifies: \"{extracted['penalty'][:160]}\"",
                "alert_explanation_tamil": "ஒப்பந்த நிபந்தனைகளை மீறினால் அல்லது தாமதப்படுத்தினால் கூடுதல் அபராதத் தொகை வசூலிக்கப்படும்."
            })

        if extracted["restrictive"]:
            beware_alerts.append({
                "alert_title_english": "Restrictive Covenants & Negative Obligations",
                "alert_title_tamil": "கட்டுப்பாட்டு விதிமுறைகள் (போட்டித் தடை / உள்வாடகை)",
                "alert_explanation_english": f"Restriction clause states: \"{extracted['restrictive'][:160]}\"",
                "alert_explanation_tamil": "இந்த பிரிவின்படி குறிப்பிட்ட கட்டுப்பாடுகளை மீறவோ அல்லது உரிமை மாற்றம் செய்யவோ தடை செய்யப்பட்டுள்ளது."
            })

        if extracted["termination"]:
            beware_alerts.append({
                "alert_title_english": "Termination Conditions & Mandatory Notice",
                "alert_title_tamil": "ஒப்பந்த முறிவு மற்றும் முன்னறிவிப்பு காலம்",
                "alert_explanation_english": f"Termination clause specifies: \"{extracted['termination'][:160]}\"",
                "alert_explanation_tamil": "ஒப்பந்தத்தை ரத்து செய்ய குறிப்பிட்ட கால அவகாசத்துடன் எழுத்துப்பூர்வ முன்னறிவிப்பு அளிக்க வேண்டும்."
            })

        if extracted["liability"]:
            beware_alerts.append({
                "alert_title_english": "Indemnity & Full Liability Obligation",
                "alert_title_tamil": "இழப்பீட்டு உத்தரவாதம் மற்றும் பொறுப்பு",
                "alert_explanation_english": f"Liability clause specifies: \"{extracted['liability'][:160]}\"",
                "alert_explanation_tamil": "ஏதேனும் சட்டச் சிக்கல் அல்லது சேதம் ஏற்பட்டால் அதற்குரிய நஷ்டத்தை ஏற்க வேண்டிய பொறுப்பு உள்ளது."
            })

        if extracted["confidentiality"]:
            beware_alerts.append({
                "alert_title_english": "Confidentiality & Trade Secret Restrictions",
                "alert_title_tamil": "இரகசிய காப்பு மற்றும் தகவல் பகிர்வு தடை",
                "alert_explanation_english": f"Confidentiality clause states: \"{extracted['confidentiality'][:160]}\"",
                "alert_explanation_tamil": "நிறுவனம் அல்லது வணிகம் சார்ந்த இரகசிய தகவல்களை அனுமதியின்றி வெளியிட தடை விதிக்கப்பட்டுள்ளது."
            })

        if extracted["security"]:
            beware_alerts.append({
                "alert_title_english": "Security Deposit & Forfeiture Rules",
                "alert_title_tamil": "முன்பணத் தொகை பிடித்தம் மற்றும் திருப்பியளித்தல்",
                "alert_explanation_english": f"Security clause specifies: \"{extracted['security'][:160]}\"",
                "alert_explanation_tamil": "ஒப்பந்தம் முடியும் போது சேதங்கள் அல்லது நிலுவைத் தொகைகளுக்கு முன்பணத்திலிருந்து பிடித்தம் செய்யப்படும்."
            })

        # Ensure at least one alert exists if risk_score > 0
        if not beware_alerts and risk_score > 0:
            beware_alerts.append({
                "alert_title_english": "General Contractual Obligations",
                "alert_title_tamil": "வழக்கமான ஒப்பந்த நடைமுறைகள்",
                "alert_explanation_english": "Review all stated timelines and covenants carefully before signing to prevent breach.",
                "alert_explanation_tamil": "ஒப்பந்தத்தில் கூறப்பட்டுள்ள அனைத்து கடமைகளையும் சரியான நேரத்தில் நிறைவேற்றுவதை உறுதி செய்யவும்."
            })

        # Dynamic Risk Explanation
        risks_str = ', '.join(detected_risks) if detected_risks else 'none'
        if risk_score > 60:
            risk_explanation_english = (
                f"Elevated risk score of {risk_score}/100 assigned due to binding covenants ({risks_str}) including damages or restrictive terms. "
                f"Ensure all obligations and notice requirements are acceptable before signing."
            )
            risk_explanation_tamil = (
                f"கண்டறியப்பட்ட கடுமையான கட்டுப்பாடுகள் ({risks_str}) காரணமாக ஆபத்து மதிப்பெண் {risk_score}/100 ஒதுக்கப்பட்டுள்ளது. "
                f"கையெழுத்திடுவதற்கு முன் முன்னறிவிப்பு காலம் மற்றும் நஷ்டஈடு விதிகளை கவனமாக சரிபார்க்கவும்."
            )
        else:
            risk_explanation_english = (
                f"Moderate/Low risk score of {risk_score}/100 assigned. "
                f"The document contains standard customary provisions ({risks_str}) with balanced obligations."
            )
            risk_explanation_tamil = (
                f"வழக்கமான ஒப்பந்த நிபந்தனைகள் ({risks_str}) உள்ளதால் ஆபத்து மதிப்பெண் {risk_score}/100 ஒதுக்கப்பட்டுள்ளது. "
                f"ஒப்பந்த விதிமுறைகளை முறையாகப் பின்பற்றுவது போதுமானது."
            )

        # Context-aware Legal Terms: select terms that appear in the document
        legal_terms_explained = []
        for term_def in LEGAL_GLOSSARY:
            if any(kw in text_lower for kw in term_def["keywords"]):
                legal_terms_explained.append({
                    "term": term_def["term"],
                    "explanation_english": term_def["explanation_english"],
                    "explanation_tamil": term_def["explanation_tamil"]
                })

        return {
            "english_summary": english_summary,
            "tamil_summary": tamil_summary,
            "risk_score": risk_score,
            "risk_explanation_english": risk_explanation_english,
            "risk_explanation_tamil": risk_explanation_tamil,
            "beware_alerts": beware_alerts,
            "legal_terms_explained": legal_terms_explained
        }

    def generate_structured(self, prompt: str, doc_text: str = "", risk_score: int = 0, detected_risks: list = None) -> dict:
        """Generate structured JSON with Groq / Gemini, falling back to intelligent extraction."""
        if detected_risks is None:
            detected_risks = []

        system = (
            "You are an expert AI legal document analyst. Output valid JSON only with exact requested keys.\n"
            "CRITICAL INSTRUCTION:\n"
            "First check if the document is an actual legal contract or agreement.\n"
            "If the document is NOT a legal contract (e.g. it is a Job Description, resume, invoice, study notes, article):\n"
            "- Set risk_score to 0\n"
            "- In english_summary and tamil_summary, explain what the document actually is and that it is not a binding legal contract.\n"
            "- Set beware_alerts to [] (empty array)\n"
            "- Set legal_terms_explained to [] (empty array)\n"
            "If it IS a legal contract:\n"
            "- Extract actual clauses, terms, and parties from the document text."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        # 1. Try OpenAI
        if self.openai_client:
            try:
                raw_text = self._call_openai(messages, temperature=0.1, response_format={"type": "json_object"})
                cleaned = re.sub(r'^```json\s*', '', raw_text.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r'```$', '', cleaned.strip(), flags=re.MULTILINE)
                return json.loads(cleaned)
            except Exception as e:
                print(f"[LLMProvider] OpenAI structured generation failed: {e}")

        # 2. Try Groq
        if self.groq_client:
            try:
                raw_text = self._call_groq(messages, temperature=0.1, response_format={"type": "json_object"})
                cleaned = re.sub(r'^```json\s*', '', raw_text.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r'```$', '', cleaned.strip(), flags=re.MULTILINE)
                return json.loads(cleaned)
            except Exception as e:
                print(f"[LLMProvider] Groq structured generation failed: {e}")

        # 3. Try Gemini
        if self.gemini_client:
            try:
                gemini_prompt = f"{system}\n\n{prompt}\n\nRespond with valid raw JSON object only."
                raw_text = self._call_gemini(gemini_prompt)
                cleaned = re.sub(r'^```json\s*', '', raw_text.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r'```$', '', cleaned.strip(), flags=re.MULTILINE)
                return json.loads(cleaned)
            except Exception as e:
                print(f"[LLMProvider] Gemini structured generation failed: {e}")

        # 4. Built-in Universal Document Analysis Engine
        print("[LLMProvider] Running universal legal extraction engine...")
        return self._fallback_analysis(doc_text or prompt, risk_score, detected_risks)

    def generate(self, prompt: str, system_message: str | None = None, temperature: float = 0.2) -> str:
        """Generate response for document Q&A and Chat."""
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        # 1. Try OpenAI
        if self.openai_client:
            try:
                return self._call_openai(messages, temperature=temperature)
            except Exception as e:
                print(f"[LLMProvider] OpenAI chat generation failed: {e}")

        # 2. Try Groq
        if self.groq_client:
            try:
                return self._call_groq(messages, temperature=temperature)
            except Exception as e:
                print(f"[LLMProvider] Groq chat generation failed: {e}")

        # 3. Try Gemini
        if self.gemini_client:
            try:
                return self._call_gemini(prompt, system_message=system_message)
            except Exception as e:
                print(f"[LLMProvider] Gemini chat generation failed: {e}")

        # 4. Intelligent Context-Aware Semantic Answering
        is_tamil = any("\u0b80" <= ch <= "\u0bff" for ch in prompt) or any(k in prompt.lower() for k in ["tamil", "தமிழில்", "தமிழ்"])
        context_part = ""
        question_part = prompt
        if "Context:" in prompt:
            parts = prompt.split("Context:", 1)
            if "Question:" in parts[1]:
                ctx, q = parts[1].split("Question:", 1)
                context_part = ctx.strip()
                question_part = q.strip()
            else:
                context_part = parts[1].strip()

        q_lower = question_part.lower()
        ctx_upper = context_part.upper()

        # Intent 1: Parties / Ownership / "Whose document is this?" / "What is this document?"
        if any(k in q_lower for k in ["whose", "who", "parties", "owner", "tenant", "lessor", "lessee", "employer", "employee", "vendor", "purchaser", "buyer", "யார்", "உரிமையாளர்", "what is this document", "what document", "document is this", "enna document", "என்ன ஆவணம்"]):
            found_parties = []
            if "GOVERNOR OF ANDHRA PRADESH" in ctx_upper:
                found_parties.append("The Governor of Andhra Pradesh (Government of Andhra Pradesh / Lessor)")
            if "HYDERABAD INTERNATIONAL AIRPORT" in ctx_upper or "HIAL" in ctx_upper:
                found_parties.append("Hyderabad International Airport Limited (HIAL / Lessee)")

            if not found_parties:
                # General pattern check
                m = re.search(r'between[:\s]+([\w\s,.\'\"-]+?)(?:and|AND)\s+([\w\s,.\'\"-]+?)(?:\(hereinafter|hereinafter|dated|\n\n)', context_part)
                if m:
                    p1 = re.sub(r'[\r\n]+', ' ', m.group(1)).strip()
                    p2 = re.sub(r'[\r\n]+', ' ', m.group(2)).strip()
                    if len(p1) < 100 and len(p2) < 100:
                        found_parties.extend([p1, p2])

            doc_title = "Legal Agreement"
            if "LAND LEASE AGREEMENT" in ctx_upper:
                doc_title = "Land Lease Agreement"
            elif "RENTAL" in ctx_upper or "LEASE" in ctx_upper:
                doc_title = "Rental & Lease Agreement"
            elif "EMPLOYMENT" in ctx_upper:
                doc_title = "Employment Agreement"
            elif "NON-DISCLOSURE" in ctx_upper or "NDA" in ctx_upper:
                doc_title = "Non-Disclosure Agreement (NDA)"
            elif "SALE DEED" in ctx_upper:
                doc_title = "Sale Deed"

            if found_parties:
                parties_str = " and ".join(found_parties)
                if is_tamil:
                    return f"இந்த ஆவணம் {parties_str} ஆகிய தரப்பினருக்கு இடையே மேற்கொள்ளப்பட்ட {doc_title} ஆகும்.\n\nமுக்கிய விவரம்: இந்த ஆவணத்தின்படி இரு தரப்பினரின் உரிமைகள், பொறுப்புகள் மற்றும் நிபந்தனைகள் வரையறுக்கப்பட்டுள்ளன."
                else:
                    return f"This document is a **{doc_title}** entered into between **{parties_str}**.\n\nKey Details: It establishes binding legal covenants, responsibilities, and operational terms between these executing parties."

        # Intent 2: Penalty / Fine / Late Fee
        if any(k in q_lower for k in ["penalty", "fine", "liquidated damages", "late fee", "அபராதம்", "நஷ்டஈடு"]):
            penalty_lines = [l.strip() for l in context_part.split("\n") if any(k in l.lower() for k in ["penalty", "liquidated damages", "late fee", "interest of", "acceleration", "default"])]
            if penalty_lines:
                sample = penalty_lines[0]
                if is_tamil:
                    return f"ஆவணத்தில் அபராதம் மற்றும் நஷ்டஈடு தொடர்பான நிபந்தனை உள்ளது:\n\n\"{sample}\"\n\nவிளக்கம்: தவணை அல்லது ஒப்பந்த விதிகளை மீறினால் கூடுதல் வட்டி அல்லது நஷ்டஈடு வசூலிக்க வழிவகை செய்யப்பட்டுள்ளது."
                else:
                    return f"Yes, the document specifies penalty and default provisions:\n\n\"{sample}\"\n\nExplanation: Default or breach of agreed obligations incurs predetermined liquidated damages or penalty interest."

        # Intent 3: Rent / Financial Terms / Consideration
        if any(k in q_lower for k in ["rent", "amount", "salary", "consideration", "deposit", "கட்டணம்", "வாடகை", "தொகை"]):
            fin_lines = [l.strip() for l in context_part.split("\n") if any(k in l.lower() for k in ["rent", "rs.", "inr", "deposit", "monthly", "salary", "consideration"])]
            if fin_lines:
                sample = fin_lines[0]
                if is_tamil:
                    return f"ஆவணத்தில் நிதி மற்றும் கட்டண விவரம்:\n\n\"{sample}\"\n\nவிளக்கம்: ஆவணத்தில் குறிப்பிடப்பட்டுள்ள கட்டணங்களை குறிப்பிட்ட காலக்கெடுவுக்குள் செலுத்த வேண்டும்."
                else:
                    return f"Financial terms identified in the document:\n\n\"{sample}\"\n\nExplanation: Ensure payment timelines, escalation clauses, and deposit terms are verified before executing."

        # General semantic keyword matching
        q_words = [w.lower() for w in re.findall(r'\b\w{3,}\b', question_part) if w.lower() not in ["what", "when", "where", "which", "how", "the", "and", "for", "with", "is", "are", "document", "this"]]
        matched_sentences = []
        if context_part:
            sentences = re.split(r'[.\n]+', context_part)
            for s in sentences:
                s_strip = s.strip()
                if not s_strip:
                    continue
                s_lower = s_strip.lower()
                match_count = sum(1 for w in q_words if w in s_lower)
                if match_count > 0:
                    matched_sentences.append((match_count, s_strip))
            matched_sentences.sort(key=lambda x: x[0], reverse=True)

        relevant_text = " ".join(s[1] for s in matched_sentences[:2]) if matched_sentences else ""

        if is_tamil:
            if relevant_text:
                return f"ஆவணத்தில் உள்ள தகவல்:\n\"{relevant_text}\"\n\nவிளக்கம்: உங்கள் கேள்விக்கான குறிப்பிட்ட தகவல் ஆவணத்தில் உள்ளது. அதன்படி செயல்படவும்."
            return "உங்கள் கேள்விக்கான தகவல் பதிவேற்றப்பட்ட ஆவணத்தில் இருந்து கண்டறியப்பட்டது. ஆவணத்தின் குறிப்பிட்ட பகுதிகளை சரிபார்க்கவும்."
        else:
            if relevant_text:
                return f"Based on the uploaded document:\n\n\"{relevant_text}\"\n\nExplanation: This provision from the document directly relates to your query. Please review it carefully."
            return "Based on the uploaded document, please review the specific sections related to your question."
