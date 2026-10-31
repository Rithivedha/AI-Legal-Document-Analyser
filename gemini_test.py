from dotenv import load_dotenv
import os
from google import genai

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")

print("KEY FOUND:", api_key[:10])

client = genai.Client(
    api_key=api_key
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Explain rental agreement in simple Tamil suitable for village people."
)

print("\nGEMINI RESPONSE:\n")
print(response.text)