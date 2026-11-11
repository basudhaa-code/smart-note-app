import os
import uuid
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, HTMLResponse
from pydantic import BaseModel

import config
from services.pdf_processor import PDFProcessor
from services.ai_service import AIService

app = FastAPI(
    title="SmartNote AI - Lecture Analysis & Study System",
    description="Intelligent system for structured notes, key topics, practice questions, and conversational AI Q&A.",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Memory store for active sessions: { doc_id: doc_dict }
documents_store: Dict[str, Dict[str, Any]] = {}

def get_doc_path(doc_id: str) -> Path:
    return config.DATA_DIR / f"{doc_id}.json"

def save_doc_to_disk(doc_id: str, data: Dict[str, Any]):
    doc_path = get_doc_path(doc_id)
    try:
        with open(doc_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Store] Error saving {doc_id} to disk: {e}")

def load_doc_from_disk(doc_id: str) -> Optional[Dict[str, Any]]:
    doc_path = get_doc_path(doc_id)
    if doc_path.exists():
        try:
            with open(doc_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                documents_store[doc_id] = data
                return data
        except Exception as e:
            print(f"[Store] Error loading {doc_id} from disk: {e}")
    return None

def clear_saved_documents():
    """Remove uploaded PDFs and processed document data from the previous run."""
    for file in config.UPLOAD_DIR.glob("*.pdf"):
        file.unlink()
    for file in config.DATA_DIR.glob("*.json"):
        file.unlink()


@app.on_event("startup")
async def start_with_empty_document_store():
    clear_saved_documents()

# -----------------------------------------------------------------------------
# Request / Response Models
# -----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = []

class KeyConfigRequest(BaseModel):
    api_key: str
    persist: Optional[bool] = True

# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/status")
async def get_system_status():
    """Returns AI configuration status, current model, and active documents."""
    is_configured = AIService.is_api_configured()
    return {
        "gemini_configured": is_configured,
        "active_model": config.DEFAULT_MODEL if is_configured else "Local Extractive Engine",
        "doc_count": len(documents_store),
        "documents": [
            {
                "doc_id": doc["doc_id"],
                "title": doc.get("title", "Untitled"),
                "total_pages": doc.get("total_pages", 0),
                "total_words": doc.get("total_words", 0),
                "has_notes": bool(doc.get("notes")),
                "has_topics": bool(doc.get("topics")),
                "has_practice": bool(doc.get("practice"))
            }
            for doc in documents_store.values()
        ]
    }

@app.post("/api/config/key")
async def configure_api_key(req: KeyConfigRequest):
    """Sets the Gemini API Key dynamically at runtime."""
    new_key = req.api_key.strip()
    if not new_key:
        raise HTTPException(status_code=400, detail="API Key cannot be blank.")
    
    config.set_api_key(new_key, persist=req.persist)
    
    # Test key with a fast verification
    client = config.get_gemini_client()
    if client:
        try:
            test_resp = client.models.generate_content(
                model=config.DEFAULT_MODEL,
                contents="Ping. Respond with 'Pong'."
            )
            return {
                "status": "success",
                "message": f"Gemini API Key validated successfully using {config.DEFAULT_MODEL}!",
                "active_model": config.DEFAULT_MODEL
            }
        except Exception as e:
            return {
                "status": "warning",
                "message": f"Key stored, but verification call returned: {str(e)}",
                "active_model": config.DEFAULT_MODEL
            }
    
    return {"status": "success", "message": "API Key saved."}

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Uploads and analyzes a lecture PDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF document.")
    
    doc_id = str(uuid.uuid4())[:8]
    save_filename = f"{doc_id}_{file.filename}"
    file_path = config.UPLOAD_DIR / save_filename
    
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")
    
    with open(file_path, "wb") as f:
        f.write(content)
        
    try:
        doc_data = PDFProcessor.extract_pdf_content(str(file_path), doc_id, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

    # Store in memory & disk
    documents_store[doc_id] = doc_data
    save_doc_to_disk(doc_id, doc_data)
    
    return {
        "status": "success",
        "doc_id": doc_id,
        "title": doc_data["title"],
        "total_pages": doc_data["total_pages"],
        "total_words": doc_data["total_words"],
        "reading_time_min": doc_data["reading_time_min"],
        "chunks_count": len(doc_data["chunks"])
    }

@app.get("/api/document/{doc_id}")
async def get_document(doc_id: str):
    """Retrieves document overview, pages, and cached analyses."""
    doc = documents_store.get(doc_id) or load_doc_from_disk(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    return {
        "doc_id": doc["doc_id"],
        "title": doc.get("title", "Lecture Notes"),
        "filename": doc.get("filename", ""),
        "total_pages": doc.get("total_pages", 0),
        "total_words": doc.get("total_words", 0),
        "reading_time_min": doc.get("reading_time_min", 1),
        "pages": doc.get("pages", []),
        "has_notes": bool(doc.get("notes")),
        "has_topics": bool(doc.get("topics")),
        "has_practice": bool(doc.get("practice")),
        "notes": doc.get("notes"),
        "notes_meta": doc.get("notes_meta"),
        "topics": doc.get("topics"),
        "mindmap": doc.get("mindmap"),
        "practice": doc.get("practice")
    }

@app.post("/api/generate-notes/{doc_id}")
async def generate_notes(doc_id: str):
    """Generates comprehensive structured notes from the uploaded PDF."""
    doc = documents_store.get(doc_id) or load_doc_from_disk(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    res = AIService.generate_structured_notes(doc)
    doc["notes"] = res["notes_markdown"]
    doc["notes_meta"] = {"generated_by": res.get("generated_by", "AI Engine")}
    save_doc_to_disk(doc_id, doc)
    
    return {
        "status": "success",
        "notes": doc["notes"],
        "generated_by": res.get("generated_by")
    }

@app.post("/api/generate-topics/{doc_id}")
async def generate_topics(doc_id: str):
    """Identifies important topics and generates a concept mindmap."""
    doc = documents_store.get(doc_id) or load_doc_from_disk(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    res = AIService.extract_important_topics(doc, doc.get("topics", []))
    doc["topics"] = res.get("topics", [])
    doc["mindmap"] = res.get("mindmap", {})
    doc["topics_meta"] = {"generated_by": res.get("generated_by", "AI Engine")}
    save_doc_to_disk(doc_id, doc)
    
    return {
        "status": "success",
        "topics": doc["topics"],
        "mindmap": doc["mindmap"],
        "generated_by": res.get("generated_by")
    }

@app.post("/api/generate-practice/{doc_id}")
async def generate_practice(doc_id: str):
    """Generates MCQs, Flashcards, and Conceptual questions."""
    doc = documents_store.get(doc_id) or load_doc_from_disk(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    previous_practice = doc.get("practice_history", [])
    if doc.get("practice"):
        previous_practice = previous_practice + [doc["practice"]]
    previous_practice = previous_practice[-5:]

    res = AIService.generate_practice_questions(doc, previous_practice)
    doc["practice"] = {
        "mcqs": res.get("mcqs", []),
        "flashcards": res.get("flashcards", []),
        "short_answer": res.get("short_answer", [])
    }
    doc["practice_history"] = previous_practice
    doc["practice_meta"] = {"generated_by": res.get("generated_by", "AI Engine")}
    save_doc_to_disk(doc_id, doc)
    
    return {
        "status": "success",
        "practice": doc["practice"],
        "generated_by": res.get("generated_by")
    }

@app.post("/api/generate-all/{doc_id}")
async def generate_all(doc_id: str):
    """Generates structured notes, important topics, and practice questions in one step."""
    doc = documents_store.get(doc_id) or load_doc_from_disk(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # 1. Notes
    notes_res = AIService.generate_structured_notes(doc)
    doc["notes"] = notes_res["notes_markdown"]
    doc["notes_meta"] = {"generated_by": notes_res.get("generated_by")}

    # 2. Topics
    topics_res = AIService.extract_important_topics(doc, doc.get("topics", []))
    doc["topics"] = topics_res.get("topics", [])
    doc["mindmap"] = topics_res.get("mindmap", {})
    doc["topics_meta"] = {"generated_by": topics_res.get("generated_by")}

    # 3. Practice
    previous_practice = doc.get("practice_history", [])
    if doc.get("practice"):
        previous_practice = previous_practice + [doc["practice"]]
    previous_practice = previous_practice[-5:]

    practice_res = AIService.generate_practice_questions(doc, previous_practice)
    doc["practice"] = {
        "mcqs": practice_res.get("mcqs", []),
        "flashcards": practice_res.get("flashcards", []),
        "short_answer": practice_res.get("short_answer", [])
    }
    doc["practice_history"] = previous_practice
    doc["practice_meta"] = {"generated_by": practice_res.get("generated_by")}

    save_doc_to_disk(doc_id, doc)

    return {
        "status": "success",
        "notes": doc["notes"],
        "topics": doc["topics"],
        "mindmap": doc["mindmap"],
        "practice": doc["practice"]
    }

@app.post("/api/chat")
async def chat_with_gemini(req: ChatRequest):
    """Answers student questions directly with Gemini, independently of uploaded PDFs."""
    try:
        return AIService.answer_question(req.query, req.history)
    except RuntimeError as e:
        status_code = 503 if "not configured" in str(e) else 502
        raise HTTPException(status_code=status_code, detail=str(e)) from e

@app.get("/api/export/{doc_id}/markdown")
async def export_markdown(doc_id: str):
    """Exports generated notes as a downloadable Markdown (.md) file."""
    doc = documents_store.get(doc_id) or load_doc_from_disk(doc_id)
    if not doc or not doc.get("notes"):
        raise HTTPException(status_code=404, detail="Notes not generated yet.")
    
    clean_title = "".join(c for c in doc.get("title", "Lecture_Notes") if c.isalnum() or c in (' ', '_', '-')).strip()
    clean_title = clean_title.replace(" ", "_")
    filename = f"{clean_title}_Notes.md"
    
    return PlainTextResponse(
        content=doc["notes"],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/api/export/{doc_id}/html")
async def export_html(doc_id: str):
    """Exports printable HTML document."""
    doc = documents_store.get(doc_id) or load_doc_from_disk(doc_id)
    if not doc or not doc.get("notes"):
        raise HTTPException(status_code=404, detail="Notes not generated yet.")
    
    title = doc.get("title", "Lecture Notes")
    notes_md = doc["notes"].replace("`", "\\`")
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title} - Study Notes</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 860px; margin: 40px auto; padding: 20px; line-height: 1.6; color: #1e293b; }}
        h1, h2, h3 {{ color: #0f172a; margin-top: 1.5em; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1.5em 0; }}
        th, td {{ border: 1px solid #cbd5e1; padding: 10px 14px; text-align: left; }}
        th {{ background-color: #f1f5f9; }}
        code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
        pre {{ background: #0f172a; color: #f8fafc; padding: 16px; border-radius: 8px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #6366f1; margin: 0; padding-left: 16px; color: #475569; }}
        @media print {{ body {{ margin: 0; padding: 0; }} }}
    </style>
</head>
<body>
    <div id="content"></div>
    <script>
        const md = `{notes_md}`;
        document.getElementById('content').innerHTML = marked.parse(md);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)

# Mount static folder
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    return FileResponse(config.STATIC_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
