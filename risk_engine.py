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
    "penalty": 20,
    "terminate": 15,
    "termination": 15,
    "liability": 15,
    "indemnify": 15,
    "fee": 10,
    "charges": 10,
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
    """Calculate calibrated risk score for legal agreements.
    Non-legal documents receive 0.
    Standard commercial and statutory leases score 55-65 (Medium/Elevated Risk).
    Only predatory contracts with severe penalties (e.g. double rent, unlimited liability) score 75-90.
    """
    if not text:
        return 0, []

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

    # Check for extreme predatory penalties
    has_extreme_penalties = any(p in text_lower for p in [
        "double rent", "two times the rent", "without notice", 
        "sole discretion", "unlimited liability", "forfeit all deposit"
    ])

    if has_extreme_penalties:
        score = min(max(score, 75), 85)
    else:
        # Standard commercial, statutory, or residential lease is capped at 65 (Medium / Elevated Risk)
        score = min(max(score, 45), 65)

    return score, risks