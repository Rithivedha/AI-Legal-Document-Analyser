import ollama

response = ollama.chat(
    model="llama3",
    messages=[
        {
            "role": "user",
            "content": """
            Explain in simple Tamil suitable for common people:

            The tenant shall pay rent before the 5th of every month.
            Failure to pay shall result in a penalty.
            """
        }
    ]
)

print(response["message"]["content"])