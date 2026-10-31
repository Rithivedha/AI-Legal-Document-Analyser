from legal_analyzer import analyze_document

sample_document = """
The tenant shall pay rent before the 5th of every month.

Failure to pay rent shall result in a penalty.

The landlord may terminate the agreement if payment is delayed.
"""

result = analyze_document(sample_document)

try:
    print(result)
except UnicodeEncodeError:
    print(result.encode("ascii", errors="replace").decode("ascii"))