import sys
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# Fix Windows console encoding for UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from services.sample_generator import SampleLectureGenerator
from services.pdf_processor import PDFProcessor
from services.rag_engine import rag_engine
from services.ai_service import AIService

def run_tests():
    print("=" * 60)
    print("Starting SmartNote AI End-to-End System Tests")
    print("=" * 60)

    # 1. Test Sample PDF Creation
    print("\n[Step 1] Generating sample lecture PDF...")
    sample_path = config.UPLOAD_DIR / "test_sample_dl.pdf"
    SampleLectureGenerator.create_sample_lecture_pdf(sample_path)
    assert sample_path.exists(), "Sample PDF was not created!"
    print(f"  [+] Sample PDF created at {sample_path} ({sample_path.stat().st_size:,} bytes)")

    # 2. Test PDF Extraction with PyMuPDF
    print("\n[Step 2] Extracting PDF content with PyMuPDF...")
    doc_data = PDFProcessor.extract_pdf_content(
        str(sample_path),
        doc_id="test-doc-1",
        original_filename="test_sample_dl.pdf"
    )
    assert doc_data["total_pages"] == 4, f"Expected 4 pages, got {doc_data['total_pages']}"
    assert doc_data["total_words"] > 500, f"Expected >500 words, got {doc_data['total_words']}"
    assert len(doc_data["chunks"]) > 0, "No chunks generated!"
    print(f"  [+] Extracted {doc_data['total_pages']} pages, {doc_data['total_words']:,} words, {len(doc_data['chunks'])} semantic chunks.")

    # 3. Test RAG Engine Indexing & Search
    print("\n[Step 3] Indexing chunks in RAG Engine & querying...")
    rag_engine.index_document("test-doc-1", doc_data["chunks"])
    
    query = "What is the formula for backpropagation and the chain rule?"
    results = rag_engine.search("test-doc-1", query, top_k=2)
    assert len(results) > 0, "RAG search returned 0 results"
    best = results[0]
    print(f"  [+] Query: '{query}'")
    print(f"  [+] Top Match: Page {best['page_num']} (Score: {best['score']})")
    print(f"  [+] Excerpt: {best['text'][:90]}...")

    # 4. Test Structured Notes Generation
    print("\n[Step 4] Testing Structured Notes Generation...")
    notes_res = AIService.generate_structured_notes(doc_data)
    assert "notes_markdown" in notes_res, "Notes missing 'notes_markdown' key"
    assert len(notes_res["notes_markdown"]) > 200, "Notes markdown too short"
    print(f"  [+] Generated structured notes using {notes_res.get('generated_by')}")
    print(f"  [+] Notes Preview:\n{notes_res['notes_markdown'][:180]}...\n")

    # 5. Test Important Topics Extraction
    print("\n[Step 5] Testing Important Topics Extraction...")
    topics_res = AIService.extract_important_topics(doc_data)
    assert "topics" in topics_res and len(topics_res["topics"]) > 0, "No topics extracted!"
    print(f"  [+] Extracted {len(topics_res['topics'])} topics using {topics_res.get('generated_by')}")
    for t in topics_res["topics"][:3]:
        print(f"    - [{t.get('importance', 'Topic')}] {t.get('title')} (Pages: {t.get('pages')})")

    # 6. Test Practice Questions Generation
    print("\n[Step 6] Testing Practice Hub Questions Generation...")
    practice_res = AIService.generate_practice_questions(doc_data)
    assert "mcqs" in practice_res, "Missing 'mcqs' key in practice response"
    assert "flashcards" in practice_res, "Missing 'flashcards' key in practice response"
    print(f"  [+] MCQs: {len(practice_res.get('mcqs', []))} questions")
    print(f"  [+] Flashcards: {len(practice_res.get('flashcards', []))} cards")
    print(f"  [+] Short Answer: {len(practice_res.get('short_answer', []))} questions")
    if practice_res.get("mcqs"):
        sample_q = practice_res["mcqs"][0]
        print(f"    Sample MCQ: {sample_q.get('question')} (Correct: {sample_q.get('options', [''])[sample_q.get('correct_index', 0)]})")

    # 7. Test Student Q&A using direct Gemini chat
    print("\n[Step 7] Testing Student Q&A with direct Gemini...")
    prompt_calls = []
    def fake_generate_content(**kwargs):
        prompt_calls.append(kwargs)
        return SimpleNamespace(text="ReLU helps reduce vanishing gradients in hidden layers.")

    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fake_generate_content)
    )
    with patch("services.ai_service.config.get_gemini_client", return_value=fake_client):
        qa_res = AIService.answer_question(
            "Why is ReLU preferred over Sigmoid in hidden layers?",
            [{"role": "user", "content": "What is a vanishing gradient?"}]
        )
    assert "answer" in qa_res and len(qa_res["answer"]) > 50, "Answer too short or missing"
    assert qa_res["citations"] == [], "General chat should not cite PDF chunks"
    assert "What is a vanishing gradient?" in prompt_calls[0]["contents"]
    assert "DOCUMENT EXCERPTS" not in prompt_calls[0]["contents"]
    print(f"  [+] Answer generated by: {qa_res.get('model')}")
    print("  [+] Verified conversation history is passed without PDF context.")
    print(f"  [+] Answer snippet:\n{qa_res['answer'][:200]}...")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
