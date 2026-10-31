import re

NON_LEGAL_PATTERNS = [
    r"\bjob\s+description\b",
    r"\binternship\b",
    r"\bcurriculum\s+vitae\b",
    r"\bresume\b",
    r"\bsyllabus\b",
    r"\bcourse\s+overview\b",
    r"\breceipt\b",
    r"\buser\s+manual\b",
    r"\bacademic\s+calendar\b"
]

LEGAL_INDICATORS = [
    r"\bagreement\b",
    r"\bcontract\b",
    r"\blease\b",
    r"\btenant\b",
    r"\blandlord\b",
    r"\bby\s+and\s+between\b",
    r"\bwitnesseth\b",
    r"\bwhereas\b",
    r"\bdemised\s+premises\b",
    r"\bindemnify\b",
    r"\bcovenants\b",
    r"\bterms\s+and\s+conditions\b"
]

RISK_KEYWORDS = {
    "penalty": 25,
    "terminate": 20,
    "termination": 20,
    "liability": 20,
    "indemnify": 20,
    "fee": 15,
    "charges": 15,
    "fine": 15,
    "obligation": 10
}

def is_legal_document(text: str) -> bool:
    """Determine if a document is an actual legal contract/agreement."""
    if not text:
        return False
    text_lower = text.lower()

    # Check for strong non-legal signals
    non_legal_matches = sum(1 for pat in NON_LEGAL_PATTERNS if re.search(pat, text_lower))
    legal_matches = sum(1 for pat in LEGAL_INDICATORS if re.search(pat, text_lower))

    if non_legal_matches >= 1 and legal_matches < 3:
        return False

    return legal_matches >= 2

def calculate_risk(text: str):
    """Calculate risk score only for real legal agreements.
    Non-legal documents (e.g. Job Descriptions, Resumes) receive a score of 0.
    """
    if not text:
        return 0, []

    # If document is not a legal contract, risk score is 0
    if not is_legal_document(text):
        return 0, []

    score = 0
    risks = []
    text_lower = text.lower()

    for keyword, weight in RISK_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
            score += weight
            if keyword not in risks:
                risks.append(keyword)

    score = min(score, 100)
    return score, risks