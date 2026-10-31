# AI-Legal-Document-Analyser ⚖️

An AI-powered Legal Document Analyzer that simplifies complex contracts (Rental & Lease Agreements, Employment Contracts, NDAs, Sale Deeds, Loan Agreements), generates **Tamil & English** summaries, highlights risky clauses, and enables interactive document Q&A using RAG (Retrieval-Augmented Generation) and LLMs.

---

## 🌟 Key Features

- **Multi-Provider LLM Architecture**:
  - **Groq API**: Blazing-fast inference with `llama-3.3-70b-versatile` & `llama-3.1-8b-instant`.
  - **Google Gemini API**: Native support for `gemini-2.5-flash`.
  - **OpenAI API**: Support for `gpt-4o` and `gpt-4o-mini`.
  - **Built-in Universal Legal Engine**: Fully functional offline fallback engine that accurately identifies contract categories, extracts verbatim clauses, and identifies non-legal documents without crashing.
- **RAG Document Chat**: Ask questions about your uploaded document in **English, Tamil, or Tanglish** (e.g. *"whose document is this?"*, *"is there any penalty?"*, *"ஆவணத்தில் அபராதம் ஏதும் உண்டா?"*).
- **Automated Risk Scoring**: 0–100 risk score breakdown highlighting restrictive covenants, penalty clauses, liquidated damages, and indemnity liabilities.
- **Bilingual Legal Glossary**: Side-by-side legal term definitions explained in simple English and spoken Tamil.
- **Zero 500 Errors**: Resilient exception handling and fallback mechanisms across all endpoints.

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Rithivedha/AI-Legal-Document-Analyser.git
cd AI-Legal-Document-Analyser
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your preferred key (Groq, Gemini, or OpenAI). The system also works offline with the built-in legal intelligence engine.

### 4. Run the Application
```bash
python main.py
```
Open your browser at **`http://localhost:8000`**.

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
