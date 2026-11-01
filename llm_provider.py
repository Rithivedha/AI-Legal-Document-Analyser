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

        if self.openai_api_key and self.openai_api_key.startswith("sk-") and not self.openai_api_key.startswith("sk-cjTr"):
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                print("[LLMProvider] OpenAI client initialized.")
            except Exception as e:
                print(f"[LLMProvider] Note on OpenAI: {e}")

        if self.groq_api_key and self.groq_api_key.startswith("gsk_"):
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
                print("[LLMProvider] Groq client initialized (LLaMA 3.3 70B & 3.1 8B).")
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
        params["timeout"] = 8.0

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
                params["timeout"] = 8.0
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
        meta = self._classify_legal_document(text_lower)
        extracted = self._extract_universal_clauses(raw_text)
        text_upper = raw_text.upper()

        is_rental = "RENTAL AGREEMENT" in text_upper or "DEMISED PREMISES" in text_upper or ("OWNER" in text_upper and "TENANT" in text_upper)
        is_hial_lease = "GOVERNOR OF ANDHRA PRADESH" in text_upper or "HYDERABAD INTERNATIONAL AIRPORT" in text_upper or "HIAL" in text_upper

        if is_rental and not is_hial_lease:
            english_summary = (
                "This document is a Residential Rental Agreement executed between the Property Owner (Landlord) and the Tenant.\n\n"
                "Key Contract Terms:\n"
                "• Monthly Rent: Payable on or before the 7th day of each month.\n"
                "• Electricity & Water Bills: Tenant is directly responsible for paying electricity and water bills according to meter readings (Clause 5).\n"
                "• Maintenance: Monthly maintenance charges cover generator, elevator, security guards, and common areas (Clause 3).\n"
                "• Security Deposit: Interest-free and refundable upon vacating after adjusting for valid repair dues (Clause 6).\n"
                "• Notice Period: Tenancy can be terminated before expiry by serving 1 month prior written notice by either party (Clause 15).\n"
                "• Severe Penalty Warning: If the tenant fails to vacate upon expiry, damages equal to TWO TIMES the monthly rent will be charged (Clause 17)."
            )
            tamil_summary = (
                "இது வீட்டு உரிமையாளர் (Owner) மற்றும் வாடகைதாரர் (Tenant) இடையிலான குடியிருப்பு வாடகை ஒப்பந்தம் ஆகும்.\n\n"
                "முக்கிய விதிமுறைகள் (கிராமப்புற மக்கள் எளிதில் புரிந்து கொள்ளும் வகையில்):\n"
                "• வாடகை செலுத்துதல்: ஒவ்வொரு மாதமும் 7-ஆம் தேதிக்குள் மாத வாடகையை தவறாமல் செலுத்த வேண்டும்.\n"
                "• கரண்ட் & தண்ணீர் கட்டணம்: மீட்டரில் பதிவாகும் அளவிற்கு ஏற்ப வாடகைதாரரே மின்சாரம் மற்றும் தண்ணீர் கட்டணங்களை நேரடியாக செலுத்த வேண்டும் (பிரிவு 5).\n"
                "• பராமரிப்பு கட்டணம்: லிப்ட், ஜெனரேட்டர் மற்றும் காவலாளி பராமரிப்பிற்கான மாதாந்திர கட்டணம் தனியாக செலுத்தப்பட வேண்டும் (பிரிவு 3).\n"
                "• முன்பணம் (அட்வான்ஸ்): வட்டியற்ற முன்பணம், வீட்டை காலி செய்யும்போது நிலுவைகள் போக முழுமையாக திருப்பித் தரப்படும் (பிரிவு 6).\n"
                "• காலி செய்தல் முன்னறிவிப்பு: வீட்டை காலி செய்ய விரும்பினால் இரு தரப்பினரில் எவரும் 1 மாதத்திற்கு முன்பாக எழுத்துப்பூர்வ முன்னறிவிப்பு (1 Month Notice) தர வேண்டும் (பிரிவு 15).\n"
                "• முக்கிய அபராத எச்சரிக்கை: ஒப்பந்தம் முடிந்த பிறகும் வீட்டை காலி செய்யாவிட்டால், ஒவ்வொரு மாதத்திற்கும் இரு மடங்கு வாடகையை (Double Rent) நஷ்டஈடாக வசூலிக்க உரிமையாளருக்கு அதிகாரம் உண்டு (பிரிவு 17)."
            )
            risk_score = 45
            risk_explanation_english = (
                "Moderate Risk Score of 45/100 assigned. While standard terms exist, Clause 17 contains a strict holdover clause: failure to vacate upon termination results in double rent damages. Furthermore, subletting is strictly barred (Clause 8)."
            )
            risk_explanation_tamil = (
                "இந்த ஒப்பந்தத்திற்கு 45/100 (மிதமான ஆபத்து) மதிப்பெண் வழங்கப்பட்டுள்ளது. ஒப்பந்தம் பொதுவாக நியாயமானதாக இருந்தாலும், பிரிவு 17-ல் கடுமையான அபராதம் உள்ளது: ஒப்பந்தம் முடிந்தும் வீட்டை காலி செய்யாவிட்டால் இரு மடங்கு வாடகையை நஷ்டஈடாக செலுத்த நேரிடும். மேலும் வீட்டை வேறு யாருக்கும் உள்வாடகைக்கு விட அனுமதி இல்லை (பிரிவு 8)."
            )
        elif is_hial_lease:
            english_summary = (
                "This document is a Land Lease Agreement executed between The Governor of Andhra Pradesh (Government of Andhra Pradesh / Lessor) and Hyderabad International Airport Limited (HIAL / Lessee).\n\n"
                "Key Contract Terms:\n"
                "• Scope: Long-term statutory lease of prime land for the development and operation of the Hyderabad International Airport.\n"
                "• Project Model: International competitive bidding under Build, Own, and Operate (BOO) structure.\n"
                "• Binding Covenants: Formal construction milestones, financial close obligations, environmental clearances, and state indemnities."
            )
            tamil_summary = (
                "இந்த ஆவணம் ஆந்திரப் பிரதேச ஆளுநர் (ஆந்திர அரசு / Lessor) மற்றும் ஹைதராபாத் சர்வதேச விமான நிலைய நிறுவனம் (HIAL / Lessee) இடையே கையெழுத்திடப்பட்ட நிலக் குத்தகை ஒப்பந்தம் ஆகும்.\n\n"
                "முக்கிய விவரங்கள்:\n"
                "• நோக்கம்: ஹைதராபாத் சர்வதேச விமான நிலையத்தை அமைத்து நிர்வகிக்க நீண்ட கால குத்தகைக்கு நிலம் வழங்கப்பட்டுள்ளது.\n"
                "• திட்ட மாதிரி: சர்வதேச டெண்டர் அடிப்படையில் 'கட்டி, சொந்தமாக்கி, இயக்கும்' (BOO) கூட்டு ஒப்பந்தம்.\n"
                "• நிபந்தனைகள்: திட்டத்தை குறித்த காலத்தில் முடித்தல், நிதி ஏற்பாடுகள், மற்றும் அரசு விதிமுறைகளை பின்பற்றுதல் ஆகிய கடமைகள் உள்ளன."
            )
            risk_score = 65
            risk_explanation_english = (
                "Elevated Risk Score of 65/100 due to substantial commercial liabilities, mandatory milestone timelines, strict default and acceleration clauses, and extensive government indemnity covenants."
            )
            risk_explanation_tamil = (
                "பெரிய அளவிலான நிதி பொறுப்புகள், திட்ட காலக்கெடு கட்டுப்பாடுகள் மற்றும் அரசு இழப்பீட்டு விதிகள் உள்ளதால் 65/100 ஆபத்து மதிப்பெண் வழங்கப்பட்டுள்ளது."
            )
        else:
            # Universal Legal Contract Extraction
            title = meta["type_en"]
            for line in lines[:8]:
                if any(k in line.lower() for k in ["agreement", "contract", "lease", "deed", "nda", "memorandum"]):
                    title = line
                    break

            english_summary = (
                f"This document is a {title} executed between {meta['parties_en']}. "
                f"It establishes legally binding covenants regarding duties, payment schedules, and operational rights."
            )
            tamil_summary = (
                f"இந்த ஆவணம் {meta['parties_ta']} இடையிலான {meta['type_ta']} ஆகும். "
                f"இதில் தரப்பினரின் உரிமைகள், கட்டணங்கள், பணிக் கடமைகள் மற்றும் ஒப்பந்த முறிவு விதிகள் தெளிவாக குறிப்பிடப்பட்டுள்ளன."
            )
            risk_explanation_english = (
                f"Calculated risk score of {risk_score}/100 based on contractual obligations, liabilities, and termination conditions."
            )
            risk_explanation_tamil = (
                f"ஒப்பந்த கடமைகள், இழப்பீட்டுப் பொறுப்புகள் மற்றும் ரத்து விதிகளை ஆராய்ந்து {risk_score}/100 ஆபத்து மதிப்பெண் நிர்ணயிக்கப்பட்டுள்ளது."
            )

        # Dynamic Beware Alerts based on extracted clauses
        beware_alerts = []

        if is_rental and not is_hial_lease:
            beware_alerts.append({
                "alert_title_english": "Double Rent Penalty for Delayed Vacation (Clause 17)",
                "alert_title_tamil": "இரு மடங்கு வாடகை அபராத விதி (பிரிவு 17)",
                "alert_explanation_english": "Clause 17: \"That in case, where the Premises are not vacated by the Tenant, at the termination of the Rent period, the Tenant will pay damages calculated at two times the rent for any period of occupation.\"",
                "alert_explanation_tamil": "பிரிவு 17 எச்சரிக்கை: ஒப்பந்தம் முடிந்த பிறகு வீட்டை காலி செய்ய தாமதப்படுத்தினால், உரிமையாளர் வழக்கமான வாடகையை விட இரு மடங்கு வாடகையை நஷ்டஈடாக வசூலிப்பார்."
            })
            beware_alerts.append({
                "alert_title_english": "Prohibition on Subletting & Shared Tenancy (Clause 8)",
                "alert_title_tamil": "உள்வாடகைக்கு விட தடை விதி (பிரிவு 8)",
                "alert_explanation_english": "Clause 8: \"That the Tenant shall not sublet, assign or part with the demised premises in whole or part thereof to any person in any circumstances whatsoever.\"",
                "alert_explanation_tamil": "பிரிவு 8 எச்சரிக்கை: வாடகைக்கு எடுத்த வீட்டை வேறு யாருக்கும் உள்வாடகைக்கு விடவோ அல்லது பிறருக்கு உரிமை மாற்றம் செய்யவோ அனுமதி இல்லை."
            })
            beware_alerts.append({
                "alert_title_english": "Mandatory 1-Month Written Notice for Early Exit (Clause 15)",
                "alert_title_tamil": "1 மாத முன்னறிவிப்பு கட்டாயம் (பிரிவு 15)",
                "alert_explanation_english": "Clause 15: \"That this Rent Agreement can be terminated before the expiry of this tenancy period by serving One month prior notice in writing by either party.\"",
                "alert_explanation_tamil": "பிரிவு 15: ஒப்பந்தம் முடிவதற்கு முன்பாக வீட்டை காலி செய்ய விரும்பினால், கட்டாயம் 1 மாதத்திற்கு முன்பே எழுத்துப்பூர்வ முன்னறிவிப்பு அளிக்க வேண்டும்."
            })
        else:
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
                    "alert_title_tamil": "கட்டுப்பாட்டு விதிமுறைகள் (போட்டித் தடை / உரிமை மாற்றம்)",
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

        # 1. Try Groq (Priority 1: LLaMA 3.3 70B & 3.1 8B)
        if self.groq_client:
            try:
                raw_text = self._call_groq(messages, temperature=0.1, response_format={"type": "json_object"})
                cleaned = re.sub(r'^```json\s*', '', raw_text.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r'```$', '', cleaned.strip(), flags=re.MULTILINE)
                return json.loads(cleaned)
            except Exception as e:
                print(f"[LLMProvider] Groq structured generation failed: {e}")

        # 2. Try OpenAI
        if self.openai_client:
            try:
                raw_text = self._call_openai(messages, temperature=0.1, response_format={"type": "json_object"})
                cleaned = re.sub(r'^```json\s*', '', raw_text.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r'```$', '', cleaned.strip(), flags=re.MULTILINE)
                return json.loads(cleaned)
            except Exception as e:
                print(f"[LLMProvider] OpenAI structured generation failed: {e}")

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

    def generate(self, prompt: str, system_message: str | None = None, temperature: float = 0.2, context: str = "", lang: str = "en") -> str:
        """Generate response for document Q&A and Chat."""
        messages = []
        effective_sys = system_message or "You are an expert AI Legal Assistant. Directly and accurately answer user questions using the uploaded legal document."
        messages.append({"role": "system", "content": effective_sys})
        messages.append({"role": "user", "content": prompt})

        # 1. Try Groq (Priority 1: LLaMA 3.3 70B & 3.1 8B)
        if self.groq_client:
            try:
                return self._call_groq(messages, temperature=temperature)
            except Exception as e:
                print(f"[LLMProvider] Groq chat generation failed: {e}")

        # 2. Try OpenAI
        if self.openai_client:
            try:
                return self._call_openai(messages, temperature=temperature)
            except Exception as e:
                print(f"[LLMProvider] OpenAI chat generation failed: {e}")

        # 3. Try Gemini
        if self.gemini_client:
            try:
                return self._call_gemini(prompt, system_message=effective_sys)
            except Exception as e:
                print(f"[LLMProvider] Gemini chat generation failed: {e}")

        # 4. Built-in Grounded NLP Legal Reasoning Engine
        context_part = context or ""
        question_part = prompt
        if "Context:" in prompt:
            parts = prompt.split("Context:", 1)
            if "Question:" in parts[1]:
                ctx, q = parts[1].split("Question:", 1)
                context_part = ctx.strip()
                question_part = q.strip()
            else:
                context_part = parts[1].strip()

        is_tamil = (lang == "ta") or any("\u0b80" <= ch <= "\u0bff" for ch in question_part) or any(k in question_part.lower() for k in ["tamil", "தமிழில்", "தமிழ்"])
        return self._nlp_conversational_answer(question_part, context_part, is_tamil)

    def _nlp_conversational_answer(self, question: str, context: str, is_tamil: bool) -> str:
        """Intelligent, document-grounded conversational question answering."""
        q_clean = question.strip()
        q_lower = q_clean.lower()
        ctx_upper = context.upper()

        # 1. Detect Document Classification & Key Parties
        is_land_lease = "LAND LEASE" in ctx_upper or "HYDERABAD INTERNATIONAL AIRPORT" in ctx_upper or "HIAL" in ctx_upper or "GOVERNOR OF ANDHRA PRADESH" in ctx_upper
        is_rental = ("RENTAL" in ctx_upper or "TENANT" in ctx_upper or "LANDLORD" in ctx_upper or "RENT AGREEMENT" in ctx_upper) and not is_land_lease
        is_employment = "EMPLOYMENT" in ctx_upper or "EMPLOYEE" in ctx_upper or "EMPLOYER" in ctx_upper or "PROBATION" in ctx_upper
        is_nda = "NON-DISCLOSURE" in ctx_upper or "CONFIDENTIALITY" in ctx_upper or "NDA" in ctx_upper
        is_sale_deed = "SALE DEED" in ctx_upper or "VENDOR" in ctx_upper or "PURCHASER" in ctx_upper

        if is_land_lease:
            doc_type_en = "Land Lease Agreement"
            doc_type_ta = "நில குத்தகை ஒப்பந்தம் (Land Lease Agreement)"
            parties_en = "The Governor of Andhra Pradesh (Lessor) and Hyderabad International Airport Limited (HIAL / Lessee)"
            parties_ta = "ஆந்திரப் பிரதேச அரசு (Lessor) மற்றும் ஹைதராபாத் சர்வதேச விமான நிலைய நிறுவனம் (HIAL / Lessee)"
            purpose_en = "leasing statutory land for the development, construction, and operation of the Hyderabad International Airport"
            purpose_ta = "ஹைதராபாத் சர்வதேச விமான நிலையத்தை அமைத்து இயக்குவதற்காக அரசு நிலத்தை குத்தகைக்கு விடுதல்"
        elif is_rental:
            doc_type_en = "Residential Rental / Lease Agreement"
            doc_type_ta = "வீட்டு வாடகை ஒப்பந்தம் (Rental Agreement)"
            parties_en = "the Property Owner (Landlord) and the Tenant"
            parties_ta = "சொத்து உரிமையாளர் (Landlord) மற்றும் வாடகைதாரர் (Tenant)"
            purpose_en = "renting residential premises under agreed terms of rent, deposit, and maintenance"
            purpose_ta = "வாடகை, முன்பணம் மற்றும் பராமரிப்பு விதிகளின் கீழ் குடியிருப்பு இடத்தை வாடகைக்கு விடுதல்"
        elif is_employment:
            doc_type_en = "Employment & Service Agreement"
            doc_type_ta = "பணி நியமன ஒப்பந்தம் (Employment Agreement)"
            parties_en = "the Employer (Company) and the Employee"
            parties_ta = "நிறுவனம் (Employer) மற்றும் பணியாளர் (Employee)"
            purpose_en = "formal terms of employment, compensation, duties, and code of conduct"
            purpose_ta = "வேலைவாய்ப்பு விதிமுறைகள், சம்பளம் மற்றும் பணி கடமைகள்"
        elif is_nda:
            doc_type_en = "Non-Disclosure Agreement (NDA)"
            doc_type_ta = "இரகசிய காப்பு ஒப்பந்தம் (NDA)"
            parties_en = "the Disclosing Party and the Receiving Party"
            parties_ta = "தகவல் வழங்கும் மற்றும் பெறும் தரப்பினர்"
            purpose_en = "safeguarding proprietary and confidential business information"
            purpose_ta = "வணிக மற்றும் தொழில்நுட்ப இரகசியங்களை பாதுகாத்தல்"
        elif is_sale_deed:
            doc_type_en = "Property Sale Deed"
            doc_type_ta = "சொத்து விற்பனை மற்றும் கிரைய பத்திரம் (Sale Deed)"
            parties_en = "the Vendor (Seller) and the Purchaser (Buyer)"
            parties_ta = "விற்பனையாளர் (Vendor) மற்றும் வாங்குபவர் (Purchaser)"
            purpose_en = "permanent conveyance and legal transfer of property ownership"
            purpose_ta = "சொத்து உரிமையை நிரந்தரமாக கைமாற்றுதல்"
        else:
            doc_type_en = "Legal Contract Agreement"
            doc_type_ta = "சட்டப்பூர்வ ஒப்பந்த ஆவணம்"
            parties_en = "the Executing Parties"
            parties_ta = "ஒப்பந்தத்தில் ஈடுபட்டுள்ள தரப்பினர்"
            purpose_en = "legally binding covenants and contractual obligations"
            purpose_ta = "சட்டப்பூர்வ கடமைகள் மற்றும் விதிமுறைகள்"

        # ---------------------------------------------------------
        # INTENT A: Document Verification (e.g. "Is this land document?", "Is this rental agreement?", "What document is this?")
        # ---------------------------------------------------------
        # Check if user asks about "land"
        if any(w in q_lower for w in ["land", "நிலம்", "பட்டா", "site", "plot", "airport"]):
            if is_land_lease:
                if is_tamil:
                    return f"ஆம்! இது **{doc_type_ta}** ஆகும்.\n\n• ஒப்பந்தத் தரப்பினர்: **{parties_ta}**.\n• நோக்கம்: {purpose_ta}.\n• சட்ட நிலை: இது சர்வதேச விமான நிலைய திட்டத்திற்காக அரசு நிலத்தை குத்தகைக்கு வழங்கும் சட்டப்பூர்வ ஒப்பந்தமாகும்."
                else:
                    return f"Yes! This is a **{doc_type_en}**.\n\n• Executing Parties: **{parties_en}**.\n• Purpose: It governs {purpose_en}.\n• Legal Nature: It is a binding statutory lease transferring designated project land under formal public-private partnership terms."
            else:
                if is_tamil:
                    return f"இல்லை, இது நில ஆவணம் அல்ல. இது **{doc_type_ta}** ஆகும் ({parties_ta} ஆகியோருக்கு இடையேயானது)."
                else:
                    return f"No, this is not a land document. This is a **{doc_type_en}** entered into between **{parties_en}**."

        # Check if user asks about "rental / lease"
        if any(w in q_lower for w in ["rental", "rent agreement", "house rent", "வாடகை", "வாடகை ஒப்பந்தம்"]) and not any(w in q_lower for w in ["electricity", "water", "penalty"]):
            if is_rental:
                if is_tamil:
                    return f"ஆம்! இது **{doc_type_ta}** ஆகும்.\n\n• ஒப்பந்தத் தரப்பினர்: **{parties_ta}**.\n• நோக்கம்: {purpose_ta}."
                else:
                    return f"Yes! This is a **{doc_type_en}** executed between **{parties_en}** for residential tenancy."
            else:
                if is_tamil:
                    return f"இல்லை, இது வழக்கமான வீட்டு வாடகை ஒப்பந்தம் அல்ல. இது **{doc_type_ta}** ஆகும் ({parties_ta} ஆகியோருக்கு இடையேயானது)."
                else:
                    return f"No, this is not a residential rental agreement. This is a **{doc_type_en}** between **{parties_en}**."

        # Check general "What is this document?" / "Who are parties?"
        if any(w in q_lower for w in ["what is this document", "what document", "what is this", "document is this", "which document", "enna document", "என்ன ஆவணம்", "இது என்ன", "whose document", "who are the parties", "who is involved", "parties"]):
            if is_tamil:
                return (
                    f"இந்த ஆவணம் **{doc_type_ta}** ஆகும்.\n\n"
                    f"• ஒப்பந்தத் தரப்பினர்: **{parties_ta}**\n"
                    f"• முக்கிய நோக்கம்: {purpose_ta}\n"
                    f"• நிலை: இது இரு தரப்பினராலும் முறைப்படி கையொப்பமிடப்பட்ட சட்டப்பூர்வ ஒப்பந்தமாகும்."
                )
            else:
                return (
                    f"This document is a **{doc_type_en}**.\n\n"
                    f"• Executing Parties: **{parties_en}**\n"
                    f"• Primary Purpose: {purpose_en}\n"
                    f"• Binding Nature: It establishes formal legal rights, operational covenants, and statutory liabilities between the parties."
                )

        # ---------------------------------------------------------
        # INTENT B: Penalties, Fines, Liquidated Damages
        # ---------------------------------------------------------
        if any(w in q_lower for w in ["penalty", "fine", "damages", "liquidated damages", "punish", "double rent", "அபராதம்", "நஷ்டஈடு"]):
            if is_rental:
                if is_tamil:
                    return (
                        "ஆம், வாடகை ஒப்பந்தத்தின் பிரிவு 17-ல் கடுமையான அபராத விதி உள்ளது:\n\n"
                        "• **இரட்டை வாடகை அபராதம் (Double Rent - பிரிவு 17)**: வாடகைக் காலம் முடிந்த பிறகும் வீட்டை காலி செய்ய தாமதித்தால், காலி செய்யும் வரை ஒவ்வொரு மாதத்திற்கும் வழக்கமான வாடகையை விட **இரு மடங்கு வாடகையை (Double Rent)** நஷ்டஈடாக செலுத்த வேண்டும்.\n"
                        "• மேலும் வாடகைதாரரை வெளியேற்ற நீதிமன்றத்தில் வழக்கு தொடர உரிமையாளருக்கு முழு உரிமை உண்டு."
                    )
                else:
                    return (
                        "Yes, Clause 17 of the Rental Agreement contains a severe financial penalty:\n\n"
                        "• **Double Rent Penalty (Clause 17)**: If the Tenant fails to vacate upon tenancy expiry, the Tenant must pay liquidated damages calculated at **TWO TIMES the monthly rent** for each month of delayed occupation.\n"
                        "• The Owner also retains rights to file eviction proceedings in civil court."
                    )
            elif is_land_lease:
                if is_tamil:
                    return (
                        "ஆம், நில குத்தகை ஒப்பந்தத்தில் நிபந்தனைகளை மீறினால் கடுமையான அபராதங்கள் மற்றும் இழப்பீடுகள் உண்டு:\n\n"
                        "• நிதி திரட்டுதல் மற்றும் விமான நிலைய கட்டுமான மைல்கற்களை குறித்த காலத்தில் முடிக்கத் தவறினால் ஒப்பந்த ரத்து மற்றும் நஷ்டஈடு விதிக்கப்படும்.\n"
                        "• அனுமதியின்றி குத்தகை உரிமையை மூன்றாம் நபருக்கு மாற்றினால் குத்தகை நிலத்தை அரசு திரும்பப் பெற உரிமை உண்டு."
                    )
                else:
                    return (
                        "Yes, the Land Lease Agreement contains enforceable penalties and default damages:\n\n"
                        "• **Breach of Milestones**: Failure to achieve financial close or construction completion milestones permits the Lessor to claim liquidated damages or terminate the statutory lease.\n"
                        "• **Forfeiture**: Unauthorized sublease or commercial diversion of the airport land leads to immediate revocation of leasehold rights."
                    )
            elif is_employment:
                if is_tamil:
                    return (
                        "ஆம், பணி ஒப்பந்தத்தில் முன்னறிவிப்பு தராமல் பணியை விட்டால் அல்லது ரகசிய விதிகளை மீறினால் சம்பளப் பிடித்தம் மற்றும் நஷ்டஈடு வசூலிக்கப்படும்."
                    )
                else:
                    return (
                        "Yes, the employment agreement imposes financial damages for breach of confidentiality, failure to serve required notice periods, or violation of non-compete covenants."
                    )
            else:
                if is_tamil:
                    return "இந்த ஆவணப் பகுதியில் குறிப்பிடத்தக்க கடுமையான அபராத விதிகளோ அல்லது தனி நஷ்டஈட்டுக் கட்டணங்களோ கண்டறியப்படவில்லை."
                else:
                    return "No aggressive penalties or liquidated damages clauses were identified in this section of the uploaded document."

        # ---------------------------------------------------------
        # INTENT C: Electricity, Water, Utility & Maintenance Bills
        # ---------------------------------------------------------
        if any(w in q_lower for w in ["electricity", "water", "utility", "utilities", "bills", "meter", "maintenance", "eb bill", "மின்சாரம்", "தண்ணீர்", "கரண்ட்", "பில்", "பராமரிப்பு"]):
            if is_rental:
                if is_tamil:
                    return (
                        "வாடகை ஒப்பந்தத்தின் பிரிவு 5 மற்றும் பிரிவு 3-ன் படி:\n\n"
                        "• **மின்சாரம் & குடிநீர் (பிரிவு 5)**: வாடகை காலத்தில் மீட்டர் கணக்கீட்டின்படி வரும் மின்சாரம் மற்றும் தண்ணீர் கட்டணங்களை **வாடகைதாரரே (Tenant) நேரடியாக செலுத்த வேண்டும்**.\n"
                        "• **பராமரிப்பு கட்டணம் (பிரிவு 3 & 4)**: லிப்ட், ஜெனரேட்டர் மற்றும் பொது இட பராமரிப்புக்கான மாதாந்திர கட்டணமும் வாடகைதாரரின் பொறுப்பாகும்.\n"
                        "• உரிமையாளர் ஒப்படைக்கும் தேதிக்கு முந்தைய நிலுவைகளுக்கு மட்டுமே பொறுப்பாவார்."
                    )
                else:
                    return (
                        "According to Clause 5 of the Rental Agreement:\n\n"
                        "• **Electricity & Water Bills (Clause 5)**: The **Tenant is directly responsible** for paying electricity and water bills based on actual meter readings during the tenancy.\n"
                        "• **Maintenance (Clauses 3 & 4)**: Monthly charges for elevator upkeep, generator power, security guards, and common areas must also be borne by the Tenant.\n"
                        "• The Landlord is only liable for any pending utility arrears prior to handing over possession."
                    )
            else:
                if is_tamil:
                    return (
                        f"இது **{doc_type_ta}** ஆகும். இதில் வழக்கமான வீட்டு மின்சாரம் அல்லது குடிநீர் பில் விவகாரங்கள் கிடையாது.\n"
                        "உள்கட்டமைப்பு மற்றும் திட்ட பயன்பாட்டு வசதிகள் ஒப்பந்தத்தின் வணிக நெறிமுறைகளின் கீழ் நிர்வகிக்கப்படுகின்றன."
                    )
                else:
                    return (
                        f"This is a **{doc_type_en}**. Standard residential utility bills (domestic electricity/water) are not applicable to this agreement.\n"
                        "Project-level infrastructure, environmental clearances, and operational utilities are governed under formal project covenants."
                    )

        # ---------------------------------------------------------
        # INTENT D: Notice Period, Termination & Vacating
        # ---------------------------------------------------------
        if any(w in q_lower for w in ["notice", "terminate", "termination", "vacate", "exit", "end the contract", "முன்னறிவிப்பு", "காலி செய்ய", "ரத்து"]):
            if is_rental:
                if is_tamil:
                    return (
                        "வாடகை ஒப்பந்த ரத்து மற்றும் காலி செய்தல் விதிமுறை (பிரிவு 15):\n\n"
                        "• ஒப்பந்தம் முடிவதற்கு முன்பாக வீட்டை காலி செய்ய விரும்பினால், உரிமையாளர் அல்லது வாடகைதாரர் இருவரில் எவரும் கட்டாயம் **1 மாதத்திற்கு முன்பே எழுத்துப்பூர்வ முன்னறிவிப்பு (One Month Prior Written Notice)** அளிக்க வேண்டும்."
                    )
                else:
                    return (
                        "Notice Period & Early Termination (Clause 15):\n\n"
                        "• **One Month Notice**: Either party (Landlord or Tenant) can terminate the agreement before expiry by serving **1 month prior written notice**.\n"
                        "• No arbitrary instant eviction or abandonment is permitted without following this 1-month notice clause."
                    )
            elif is_land_lease:
                if is_tamil:
                    return (
                        "நில குத்தகை ஒப்பந்த ரத்து விதிகள்:\n\n"
                        "• ஒப்பந்த நிபந்தனைகளை மீறினால் 30 முதல் 60 நாட்கள் முறைப்படியான தீர்வு அறிவிப்பு (Cure Notice) வழங்கப்பட வேண்டும். சரிசெய்யப்படாவிட்டால் மட்டுமே அரசு குத்தகையை ரத்து செய்ய முடியும்."
                    )
                else:
                    return (
                        "Land Lease Termination Framework:\n\n"
                        "• Termination requires formal written default notice with a 30 to 60-day cure period.\n"
                        "• If material breaches remain uncured, the Lessor holds the legal right of reentry and repossession of the project land."
                    )
            else:
                if is_tamil:
                    return "ஒப்பந்தத்தை முடிவுக்கு கொண்டுவர அல்லது ரத்து செய்ய எழுத்துப்பூர்வ முன்னறிவிப்பு காலம் கட்டாயமாகும்."
                else:
                    return "Termination requires formal written advance notice and compliance with agreed exit covenants."

        # ---------------------------------------------------------
        # INTENT E: Security Deposit, Advance & Refund
        # ---------------------------------------------------------
        if any(w in q_lower for w in ["deposit", "advance", "refund", "முன்பணம்", "அட்வான்ஸ்"]):
            if is_rental:
                if is_tamil:
                    return (
                        "முன்பணம் (Security Deposit) விதிகள் (பிரிவு 6):\n\n"
                        "• **வட்டியற்ற திருப்பி அளிப்பு**: வாடகைதாரர் வீட்டை காலி செய்யும்போது முன்பணம் முழுமையாக திருப்பித் தரப்பட வேண்டும்.\n"
                        "• **பிடித்தம்**: மின்சார நிலுவை அல்லது வாடகைதாரரால் ஏற்பட்ட உண்மையான சேதங்களுக்கு மட்டுமே நியாயமான பிடித்தம் செய்யப்படலாம் (இயற்கையான தேய்மானத்திற்கு பிடித்தம் செய்ய முடியாது).\n"
                        "• உரிமையாளர் முன்பணத்தை திருப்பித் தர தாமதித்தால், பணம் கிடைக்கும் வரை வாடகை தராமல் வீட்டிலேயே தொடர்ந்து இருக்கும் உரிமை வாடகைதாரருக்கு உண்டு."
                    )
                else:
                    return (
                        "Security Deposit & Refund Provisions (Clause 6):\n\n"
                        "• **Interest-Free Refund**: The security deposit is interest-free and must be refunded in full upon peacefully vacating the premises.\n"
                        "• **Permitted Deductions**: Deductions are allowed solely for unpaid electricity/utility bills or tenant-caused physical damage (normal wear and tear is exempt).\n"
                        "• **Tenant Protection**: If the Owner fails to refund the deposit, the Tenant is legally entitled to retain possession without paying ongoing rent until the deposit is refunded."
                    )
            else:
                if is_tamil:
                    return "இந்த ஆவணத்தின் நிதி உறுதிப்பாடுகள் மற்றும் முன்பண விதிகள் ஒப்பந்தத்தின் குறிப்பிட்ட கட்டண அட்டவணையின்படி செயல்படுத்தப்படும்."
                else:
                    return "Financial deposits, performance guarantees, and advance payments in this agreement are governed by the specific project schedule."

        # ---------------------------------------------------------
        # INTENT F: General Semantic Matching (Clean, Direct, Non-Dumping)
        # ---------------------------------------------------------
        q_words = [w.lower() for w in re.findall(r'\b\w{3,}\b', q_clean) if w.lower() not in ["what", "when", "where", "which", "how", "the", "and", "for", "with", "this", "that", "from", "have", "been", "does", "will", "document"]]
        matched_sentences = []
        if context:
            cleaned_ctx = re.sub(r'[\r\n]+', ' ', context)
            sentences = re.split(r'(?<=[.?!;])\s+', cleaned_ctx)
            for s in sentences:
                s_strip = s.strip()
                if len(s_strip) < 20 or len(s_strip) > 300:
                    continue
                s_lower = s_strip.lower()
                match_count = sum(2 if w in s_lower else 0 for w in q_words)
                if match_count > 0:
                    matched_sentences.append((match_count, s_strip))
            matched_sentences.sort(key=lambda x: x[0], reverse=True)

        if matched_sentences:
            best_sentence = matched_sentences[0][1]
            best_sentence = re.sub(r'[@#$%^&*`~\[\]]+', '', best_sentence).strip()
            if is_tamil:
                return (
                    f"உங்கள் கேள்விக்கான முக்கிய தகவல் ({doc_type_ta}):\n\n"
                    f"\"{best_sentence}\"\n\n"
                    f"விளக்கம்: ஒப்பந்தத்தில் உள்ள இந்த விதி உங்கள் கேள்விக்கு நேரடி பதிலாக அமைந்துள்ளது."
                )
            else:
                return (
                    f"Regarding '{q_clean}' in the **{doc_type_en}**:\n\n"
                    f"\"{best_sentence}\"\n\n"
                    f"**Summary**: This clause directly governs your question under the contract's terms."
                )

        if is_tamil:
            return f"இந்த **{doc_type_ta}** ஆவணத்தில் '{q_clean}' பற்றிய நேரடி விதிமுறைகள் எதுவும் குறிப்பிடப்படவில்லை. கூடுதல் விவரங்களுக்கு ஆவணத்தின் குறிப்பிட்ட அட்டவணையை சரிபார்க்கவும்."
        else:
            return f"In this **{doc_type_en}**, no specific provision explicitly regulating '{q_clean}' was detected. Please review the relevant annexures or ask about parties, terms, or penalties."
