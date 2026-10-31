from risk_engine import calculate_risk

text = """
The tenant shall pay penalty.
Owner may terminate agreement.
Additional maintenance charges apply.
"""

score, risks = calculate_risk(text)

print("Risk Score:", score)
print("Risks:", risks)