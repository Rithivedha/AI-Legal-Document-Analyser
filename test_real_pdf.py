from pdf_processor import extract_text_from_pdf
from legal_analyzer import analyze_document

pdf_path = "uploads/sample.pdf"

document_text = extract_text_from_pdf(
    pdf_path
)

print("PDF Extracted Successfully")

result = analyze_document(
    document_text
)

print("\n\nANALYSIS RESULT:\n")

try:
    print(result)
except UnicodeEncodeError:
    print(result.encode("ascii", errors="replace").decode("ascii"))