from pdf_processor import extract_text_from_pdf

from pdf_chat_engine import (
    store_document,
    ask_pdf
)

pdf_text = extract_text_from_pdf(
    "uploads/sample.pdf"
)

store_document(pdf_text)

while True:

    question = input("\nAsk Question: ")

    answer = ask_pdf(question)

    print("\nAnswer:\n")

    print(answer)