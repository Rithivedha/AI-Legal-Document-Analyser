import sys
from fastapi.testclient import TestClient

# Make sure the current directory is in sys.path
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app

client = TestClient(app)

def test_analyze_and_chat():
    print("Testing /analyze endpoint...")
    
    # Path to sample PDF in uploads
    pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "sample.pdf")
    if not os.path.exists(pdf_path):
        print(f"Error: Sample PDF not found at {pdf_path}")
        return

    # 1. Test /analyze
    with open(pdf_path, "rb") as f:
        response = client.post("/analyze", files={"file": ("sample.pdf", f, "application/pdf")})
    
    if response.status_code != 200:
        print(f"Analyze failed with status: {response.status_code}, response: {response.text}")
        return
    
    data = response.json()
    doc_id = data.get("doc_id")
    print(f"Analyze succeeded! Received doc_id: {doc_id}")

    # 2. Test /analysis/{doc_id}
    print("Testing /analysis/{doc_id} endpoint...")
    analysis_resp = client.get(f"/analysis/{doc_id}")
    if analysis_resp.status_code != 200:
        print(f"Get analysis failed: {analysis_resp.status_code}, response: {analysis_resp.text}")
        return
    
    analysis_data = analysis_resp.json().get("analysis")
    print("Analysis Keys received:")
    for k in analysis_data.keys():
        print(f"- {k}")
    
    # Verify expected keys
    expected_keys = [
        "english_summary",
        "tamil_summary",
        "risk_score",
        "risk_explanation_english",
        "risk_explanation_tamil",
        "beware_alerts",
        "legal_terms_explained"
    ]
    
    missing = [k for k in expected_keys if k not in analysis_data]
    if missing:
        print(f"FAIL: Missing expected keys: {missing}")
    else:
        print("PASS: All expected keys are present in the JSON response!")

    # 3. Test /chat
    print("Testing /chat endpoint...")
    chat_payload = {
        "doc_id": doc_id,
        "question": "What is the penalty for late payment?"
    }
    chat_resp = client.post("/chat", json=chat_payload)
    if chat_resp.status_code != 200:
        print(f"Chat failed: {chat_resp.status_code}, response: {chat_resp.text}")
        return
    
    chat_data = chat_resp.json()
    print("Chat answer received:")
    try:
        print(chat_data.get("answer"))
    except UnicodeEncodeError:
        print(chat_data.get("answer").encode("ascii", errors="replace").decode("ascii"))
    print("PASS: Chat responded successfully!")

if __name__ == "__main__":
    test_analyze_and_chat()
