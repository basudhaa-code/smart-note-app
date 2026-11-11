import sys
import io
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from main import app

def test_api():
    print("=" * 60)
    print("Testing FastAPI HTTP Endpoints with TestClient")
    print("=" * 60)
    
    client = TestClient(app)

    # 1. Test GET /
    print("\n[1] Testing GET / (Frontend Index)...")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "SmartNote AI" in res.text
    print("  [+] Index HTML served successfully.")

    # 2. Test GET /api/status
    print("\n[2] Testing GET /api/status...")
    res = client.get("/api/status")
    assert res.status_code == 200
    status_data = res.json()
    print(f"  [+] Status: gemini_configured={status_data['gemini_configured']}, model={status_data['active_model']}")

    # 3. Test POST /api/sample
    print("\n[3] Testing POST /api/sample (One-click sample lecture)...")
    res = client.post("/api/sample")
    assert res.status_code == 200
    sample_doc = res.json()
    doc_id = sample_doc["doc_id"]
    print(f"  [+] Sample loaded: doc_id='{doc_id}', title='{sample_doc['title']}', pages={sample_doc['total_pages']}")

    # 4. Test GET /api/document/{doc_id}
    print("\n[4] Testing GET /api/document/{doc_id}...")
    res = client.get(f"/api/document/{doc_id}")
    assert res.status_code == 200
    doc_detail = res.json()
    assert doc_detail["total_pages"] == 4
    print(f"  [+] Retrieved document detail: {len(doc_detail['pages'])} pages verified.")

    # 5. Test POST /api/generate-notes/{doc_id}
    print("\n[5] Testing POST /api/generate-notes/{doc_id}...")
    res = client.post(f"/api/generate-notes/{doc_id}")
    assert res.status_code == 200
    notes_data = res.json()
    assert "notes" in notes_data and len(notes_data["notes"]) > 100
    print(f"  [+] Generated notes length: {len(notes_data['notes'])} chars.")

    # 6. Test POST /api/generate-topics/{doc_id}
    print("\n[6] Testing POST /api/generate-topics/{doc_id}...")
    res = client.post(f"/api/generate-topics/{doc_id}")
    assert res.status_code == 200
    topics_data = res.json()
    assert len(topics_data["topics"]) > 0
    print(f"  [+] Generated {len(topics_data['topics'])} topics.")

    # 7. Test POST /api/generate-practice/{doc_id}
    print("\n[7] Testing POST /api/generate-practice/{doc_id}...")
    res = client.post(f"/api/generate-practice/{doc_id}")
    assert res.status_code == 200
    practice_data = res.json()
    assert "mcqs" in practice_data["practice"]
    print(f"  [+] Generated practice: {len(practice_data['practice']['mcqs'])} MCQs, {len(practice_data['practice']['flashcards'])} Flashcards.")

    # 8. Test POST /api/chat
    print("\n[8] Testing POST /api/chat (Interactive Q&A)...")
    prompt_calls = []
    def fake_generate_content(**kwargs):
        prompt_calls.append(kwargs)
        return SimpleNamespace(text="The vanishing gradient problem occurs when gradients become very small.")

    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fake_generate_content)
    )
    with patch("services.ai_service.config.get_gemini_client", return_value=fake_client):
        res = client.post("/api/chat", json={
            "query": "What is the vanishing gradient problem with the Sigmoid activation function?",
            "history": []
        })
    assert res.status_code == 200
    chat_data = res.json()
    assert "answer" in chat_data and len(chat_data["answer"]) > 20
    assert chat_data.get("citations", []) == []
    assert "DOCUMENT EXCERPTS" not in prompt_calls[0]["contents"]
    assert "CURRENT QUESTION:" in prompt_calls[0]["contents"]
    print(f"  [+] Q&A Answer: {chat_data['answer'][:120]}...")
    print("  [+] Verified Gemini was called directly without PDF excerpts.")

    with patch("services.ai_service.config.get_gemini_client", return_value=None):
        unavailable_res = client.post("/api/chat", json={"query": "A general question"})
    assert unavailable_res.status_code == 503

    # 9. Test GET /api/export/{doc_id}/markdown
    print("\n[9] Testing Export Markdown & HTML...")
    res_md = client.get(f"/api/export/{doc_id}/markdown")
    assert res_md.status_code == 200
    assert "attachment" in res_md.headers.get("content-disposition", "")

    res_html = client.get(f"/api/export/{doc_id}/html")
    assert res_html.status_code == 200
    assert "<!DOCTYPE html>" in res_html.text
    print("  [+] Markdown and HTML exports verified.")

    print("\n" + "=" * 60)
    print("ALL API ENDPOINT INTEGRATION TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_api()
