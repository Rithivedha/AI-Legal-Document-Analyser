from pdf_processor import extract_text_from_pdf

pdf_path = "uploads/sample.pdf"

text = extract_text_from_pdf(pdf_path)

print(text)