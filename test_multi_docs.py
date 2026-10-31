import os
import sys
from legal_analyzer import LegalAnalyzer

analyzer = LegalAnalyzer()

docs = {
    'Employment Agreement': '''EMPLOYMENT AGREEMENT
This Employment Agreement is entered into between Acme Tech Solutions Pvt Ltd ('Employer') and John Doe ('Employee').
1. Compensation: Annual base salary of INR 12,00,000.
2. Non-Compete: Employee agrees not to engage in competing business for 24 months post termination within India.
3. Liquidated Damages: Breach of confidentiality carries penalty of INR 5,00,000.
4. Termination: Either party may terminate with 30 days notice.''',

    'Non-Disclosure Agreement (NDA)': '''NON-DISCLOSURE AGREEMENT (MUTUAL NDA)
This Agreement is between Alpha Innovations ('Disclosing Party') and Beta Ventures ('Receiving Party').
1. Confidentiality Period: Information must remain confidential for 5 years.
2. Indemnity: Receiving party indemnifies disclosing party against any unauthorized disclosure.
3. Jurisdiction: Courts of Chennai, India shall have exclusive jurisdiction.''',

    'Sale Deed': '''DEED OF ABSOLUTE SALE
This Sale Deed executed between Mr. R. Sharma ('Vendor') and Ms. K. Priya ('Purchaser').
Property: Plot No. 45, Anna Nagar, Chennai.
Sale Consideration: Total price of INR 75,00,000 paid in full.
Indemnity: Vendor guarantees clear marketable title free of all encumbrances and agrees to indemnify purchaser against any prior claims.''',

    'Loan Agreement': '''LOAN AGREEMENT
Between Apex Finance Ltd ('Lender') and Horizon Logistics ('Borrower').
Principal Loan Amount: INR 25,00,000.
Interest Rate: 14% per annum.
Default & Penalty: Failure to pay monthly EMI attracts penalty interest of 24% per annum and immediate acceleration of entire loan amount.''',

    'Commercial Lease Agreement': '''COMMERCIAL LEASE AGREEMENT
Between Metro Properties ('Lessor') and Global Retailers ('Lessee').
Premises: Shop 12, Grand Mall.
Monthly Rent: INR 85,000 with 10% annual escalation.
Lock-in Period: 36 months mandatory lock-in period with no early exit allowed.
Security Deposit: INR 5,00,000 non-interest bearing deposit forfeit upon early breach.''',

    'Non-Legal: Resume / Job Description': '''SENIOR SOFTWARE ENGINEER JOB DESCRIPTION
Company: CloudScale Inc.
Location: Remote
Requirements: 5+ years experience in Python, FastAPI, React, and Machine Learning.
Responsibilities: Design backend systems, write clean code, mentor juniors. Benefits include health insurance and 401k match.'''
}

for name, text in docs.items():
    res = analyzer.analyze_text(text)
    print(f"=== {name} ===")
    print(f"Detected Type : {res.get('document_type')}")
    print(f"Risk Score    : {res.get('risk_score')}/100")
    print(f"Alerts Found  : {len(res.get('beware_clauses', []))}")
    if res.get('beware_clauses'):
        first_alert = res['beware_clauses'][0]
        print(f"Top Alert     : [{first_alert.get('risk_level')}] {first_alert.get('clause')[:70]}...")
    print(f"Summary (EN)  : {res.get('summary', '')[:110]}...")
    print()
