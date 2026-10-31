from document_chat import ask_document

question = input("Ask Question: ")

answer = ask_document(question)

print("\nAnswer:\n")

print(answer)