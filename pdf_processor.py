import fitz

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        import fitz
        pdf_document = fitz.open(pdf_path)
        for page in pdf_document:
            text += page.get_text()
        pdf_document.close()
        if text.strip():
            return text
    except Exception as e:
        print("PyMuPDF Error:", e)

    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        if text.strip():
            return text
    except Exception as e:
        print("pypdf Error:", e)

    return text if text.strip() else None

def get_representative_legal_text(text: str, max_chars: int = 18000) -> str:
    """Compile a representative subset of a long legal document to stay under API token limits.
    Grabs the beginning, end, and paragraphs containing critical risk and agreement keywords from the middle,
    scored by importance and sorted in their original document order to preserve context.
    """
    if not text or len(text) <= max_chars:
        return text

    # 1. Grab first 8,000 characters (covers parties, introductory terms, core parameters)
    first_part = text[:8000]
    
    # 2. Grab last 4,000 characters (covers signature blocks, schedules, execution clauses)
    last_part = text[-4000:]
    
    # 3. Find risk and key agreement related paragraphs from the middle section
    weights = {
        "penalty": 10,
        "terminate": 8,
        "termination": 8,
        "liability": 8,
        "indemnify": 8,
        "breach": 8,
        "default": 8,
        "fine": 6,
        "charges": 6,
        "rent": 5,
        "deposit": 5,
        "payment": 5,
        "interest": 5,
        "renewal": 5,
        "dispute": 4,
        "arbitration": 4,
        "jurisdiction": 4,
        "obligation": 3,
        "maintenance": 3,
        "sublease": 3,
    }
    
    paragraphs = text.split("\n")
    scored_paragraphs = []
    
    for idx, para in enumerate(paragraphs):
        para_strip = para.strip()
        if not para_strip:
            continue
        
        # Check if this paragraph is already fully contained in first_part or last_part
        if para_strip in first_part or para_strip in last_part:
            continue
            
        # Score paragraph based on keyword weights
        score = 0
        para_lower = para_strip.lower()
        for keyword, weight in weights.items():
            if keyword in para_lower:
                score += weight
                
        if score > 0:
            scored_paragraphs.append({
                "index": idx,
                "text": para_strip,
                "score": score
            })
            
    # Sort paragraphs by score in descending order to prioritize highest risk/value first
    scored_paragraphs.sort(key=lambda x: x["score"], reverse=True)
    
    # Select paragraphs up to the available budget (leaving a 1,500 character safety buffer)
    max_middle_chars = max_chars - len(first_part) - len(last_part) - 1500
    selected_paragraphs = []
    current_middle_chars = 0
    
    for item in scored_paragraphs:
        if current_middle_chars + len(item["text"]) < max_middle_chars:
            selected_paragraphs.append(item)
            current_middle_chars += len(item["text"])
        else:
            continue
            
    # Sort selected paragraphs back into their original document order to preserve semantic flow
    selected_paragraphs.sort(key=lambda x: x["index"])
    
    middle_part = "\n\n... [omitted middle section] ...\n\n".join([item["text"] for item in selected_paragraphs])
    
    representative_text = (
        f"--- START OF DOCUMENT (FIRST PAGES) ---\n"
        f"{first_part}\n\n"
        f"--- CRITICAL CLAUSES IDENTIFIED FROM MIDDLE SECTIONS ---\n"
        f"{middle_part}\n\n"
        f"--- END OF DOCUMENT (LAST PAGES) ---\n"
        f"{last_part}"
    )
    return representative_text