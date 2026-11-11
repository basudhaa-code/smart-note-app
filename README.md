# SmartNote AI 🧠📚
### Intelligent Lecture Material Analysis & Academic Study Assistant

**SmartNote AI** is an advanced AI-powered system designed for students, researchers, and educators. It ingests lecture materials uploaded in PDF format and automatically:
1. **Generates Structured Academic Notes** with executive summaries, hierarchical conceptual modules, LaTeX math equations, and key definition glossaries.
2. **Identifies & Ranks Important Topics** with exam priority tags (High / Medium / Foundational), prerequisites, and interactive concept mindmaps.
3. **Generates Practice Questions** including real-time scored Multiple Choice Quizzes (MCQs), interactive 3D flippable Flashcards, and conceptual short-answer questions with grading rubrics.
4. **Enables Conversational Student Q&A** powered directly by Gemini, with conversation history and answers that are not restricted to an uploaded PDF.

---

## 🌟 Key Features

### 1. High-Performance PDF Processing
- Built on **PyMuPDF (`fitz`)** for lightning-fast text extraction, layout understanding, and page boundary preservation.
- Sentence-aware semantic chunking with page metadata tracking.
- PDF generation helper used by the automated system tests.

### 2. Deep Structured Notes
- Executive Summary & Lecture Thesis
- In-depth Conceptual Modules & Architectural Breakdowns
- Full **KaTeX LaTeX math rendering** (e.g. \(z = W^T x + b\), \(\mathcal{L}(y, \hat{y})\))
- Markdown table of definitions & terminology glossary
- Common pitfalls, gotchas, and high-yield exam cheat sheets
- 1-click **Export as Markdown (.md)** or **Printable HTML / PDF**.

### 3. Important Topics & Mindmap
- Ranks concepts by examination priority (*High*, *Medium*, *Foundational*).
- Detailed explanations of *why* examiners test each concept.
- Relational concept tree and interactive mindmap visualization.

### 4. Interactive Practice Hub
- **Multiple Choice Quiz (MCQs)**: Real-time scoring, instant color-coded visual feedback (green/red), explanations for correct/incorrect answers, and celebratory confetti upon test mastery!
- **Interactive 3D Flashcards**: Realistic 3D card-flip animations, keyboard shortcuts (`Space` to flip, `←`/`→` arrows to navigate), "Mark as Mastered" progress tracker, and card shuffling.
- **Conceptual Short Answer Questions**: Deep problems with model answers and grading rubrics.

### 5. Conversational Gemini Q&A
- Sends questions and recent conversation history directly to Gemini.
- Answers general questions without restricting the assistant to uploaded PDF excerpts.
- Works independently of PDF upload; requires a configured Gemini API key.
- Provides suggested follow-up questions.

### 6. Dual-Engine Architecture
- **Gemini Engine**: Seamless integration with **Google Gemini 2.5 Flash** via `google-genai` SDK.
- **Offline / Heuristic Fallback Engine**: Document analysis remains available without an API key; conversational Gemini Q&A requires a configured API key.

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- Modern Web Browser (Chrome, Edge, Firefox, Safari)

### 2. Clone and install
Clone the repository (replace `<repository-url>` with its Git URL):
```bash
git clone <repository-url>
cd smart-note
```

Install dependencies:
```bash
python -m pip install -r requirements.txt
```

### 3. Launch the application
```bash
python main.py
```

Open your browser at:
👉 **`http://localhost:8000`**

Document analysis also works without a Gemini API key using its local fallback engine. Gemini chat requires an API key. Uploaded PDFs and generated document data are cleared when the server starts.

---

## ⚙️ Configuration (Gemini API)

You can set your Gemini API key in two convenient ways:

1. **Directly from the Web UI**:
   - Click the **API Settings** button (gear icon or status badge) in the top-right navbar.
   - Paste your key from [Google AI Studio](https://aistudio.google.com/app/apikey).
   - Click **Save & Verify Key**.

2. **Via `.env` file**:
   - Copy `.env.example` to `.env`:
     ```env
     GEMINI_API_KEY=your_actual_key_here
     DEFAULT_MODEL=gemini-3.8-flash
     PORT=8000
     ```

*(If no key is configured, the system automatically runs in offline heuristic mode with full functionality!)*

---

## 🏛️ System Architecture

```
[ Uploaded PDF ] ──> [ PDF Analysis / Study Materials ]
       │
       ▼
[ PyMuPDF Text Extractor ] ──> Page Parsing & Semantic Chunking
       │
       ▼
[ AI Service (Gemini 2.5 Flash / Fallback) ] ──> [ Notes, Topics, Practice ]
       │
       └── [ Gemini Chat + Conversation History ] ──> [ Interactive Student Q&A ]
       │
       ├───> 📝 Structured Academic Notes (LaTeX, Modules, Glossaries)
       ├───> 🎯 Important Topics & Relational Mindmap
       └───> 🧪 Practice Hub (MCQs, 3D Flashcards, Rubric Checks)
```

---

## 📂 Project Directory Structure

```
smart-note/
├── main.py                  # FastAPI server & REST API routes
├── config.py                # Environment configuration & Gemini client
├── requirements.txt         # Project dependencies
├── .env.example             # Example environment configuration
├── services/
│   ├── __init__.py
│   ├── pdf_processor.py     # PyMuPDF extraction & semantic chunker
│   ├── rag_engine.py        # TF-IDF & vector retrieval engine
│   ├── ai_service.py        # Gemini 2.5 Flash + Fallback NLP generator
│   └── sample_generator.py  # Test fixture PDF generator
├── static/
│   ├── index.html           # Modern Single Page Application
│   ├── app.js               # Frontend state, quiz engine, 3D flashcards, chat
│   └── style.css            # Custom styling & 3D perspective animations
├── uploads/                 # Uploaded PDFs storage
└── data/                    # Document states & cached analyses
```

Uploaded PDFs and processed document JSON files are cleared each time the server starts. Documents are not restored automatically after a restart, and a browser refresh never auto-selects a document.

---

## 🧪 Automated Testing

A dedicated test suite `test_system.py` is included to verify all components:
```bash
python test_system.py
```
This tests:
- PDF generation
- Page extraction
- RAG retrieval & similarity scoring
- Structured notes synthesis
- Topic identification
- Practice quiz & flashcard generation
- Student Q&A with page citations
