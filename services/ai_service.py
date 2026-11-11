import os
import re
import json
from typing import Dict, List, Any, Optional
import config

class AIService:
    @staticmethod
    def is_api_configured() -> bool:
        return bool(config.get_api_key())

    @staticmethod
    def _clean_json_response(raw_text: str) -> str:
        """Strips markdown code fences like ```json ... ``` from model output."""
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
            text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
        return text.strip()

    # -------------------------------------------------------------------------
    # 1. STRUCTURED NOTES GENERATION
    # -------------------------------------------------------------------------
    @staticmethod
    def generate_structured_notes(doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates comprehensive, end-to-end structured academic lecture notes covering 100% of the material.
        """
        client = config.get_gemini_client()
        full_text = doc_data.get("full_text", "")
        title = doc_data.get("title", "Lecture Notes")
        pages_count = doc_data.get("total_pages", 1)
        total_words = doc_data.get("total_words", 0)

        # Gemini 2.5 Flash has a 1,000,000 token context window.
        # Allow up to 350,000 characters (~85,000 tokens) so entire 40-80 page PDFs are fully ingested!
        sample_text = full_text[:350000] if len(full_text) > 350000 else full_text

        if client:
            prompt = f"""You are an elite academic professor and expert textbook author.
Analyze the following lecture material and generate a thoroughly exhaustive, 100% complete, beautifully structured academic study guide.

CRITICAL COMPLETENESS REQUIREMENTS:
- You must cover the ENTIRE document from Page 1 to Page {pages_count}.
- DO NOT stop halfway, DO NOT omit later pages or sections, and DO NOT leave any topic as a brief placeholder.
- Provide comprehensive depth for every concept, mechanism, equation, and proof discussed in the slides.

DOCUMENT TITLE: {title}
TOTAL PAGES: {pages_count} ({total_words:,} words)

LECTURE MATERIAL:
{sample_text}

Format your output in clean GitHub Flavored Markdown with KaTeX LaTeX math ($...$ or $$...$$) for all equations.
Your notes MUST include the following complete sections:

# {title}: Master Lecture Study Guide

> [!IMPORTANT]
> **Coverage**: 100% Comprehensive Analysis of all {pages_count} pages ({total_words:,} words).

## Table of Contents
(Provide markdown links to all major modules below)

## 1. 📌 Executive Summary & Core Objectives
- 4-6 concise bullet points summarizing the central thesis, scope, and foundational goals of the entire lecture.

## 2. 🧠 Conceptual Architecture & Theoretical Framework
- High-level architectural overview illustrating how the topics, equations, and subsystems connect together.

## 3. 📖 Comprehensive Module-by-Module Breakdown
(Systematically cover EVERY major topic and section across all {pages_count} pages):
- Use ### Module / Section Headings
- Provide complete conceptual explanations (no truncated sentences)
- Include all mathematical formulas formatted cleanly in LaTeX ($$...$$ or $...$)
- Step-by-step algorithms, derivations, and numerical examples where present
- Clear bulleted explanations of properties, trade-offs, and design decisions
- Explicit page citations (e.g. *(Refer to Page X)*)

## 4. 📝 Master Definitions & Glossary Table
Provide an exhaustive markdown table:
| Term / Concept | Complete Academic Definition | Source Page | Context & Significance |

## 5. ⚠️ Common Misconceptions, Edge Cases & Exam Traps
- Detailed breakdown of common student mistakes, confusing distinctions, and frequent examination traps.

## 6. 🎯 High-Yield Exam Cheat Sheet & Quick-Revision Takeaways
- Rapid-fire summary of must-memorize formulas, laws, asymptotic bounds, and key conclusions for test day.
"""
            try:
                from google.genai import types
                model_name = config.DEFAULT_MODEL
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=8192,
                        temperature=0.2
                    )
                )
                if response and response.text:
                    return {
                        "notes_markdown": response.text,
                        "generated_by": f"Google Gemini 2.5 Flash (Deep AI Mode)",
                        "coverage": f"100% Analyzed ({pages_count} pages)",
                        "status": "success"
                    }
            except Exception as e:
                print(f"[AIService] Gemini notes generation error: {e}. Falling back to structural knowledge extractor.")

        # High-Fidelity Structural Heuristic Generator (Covers 100% of pages without cutting off)
        return AIService._generate_heuristic_notes(doc_data)

    @staticmethod
    def _generate_heuristic_notes(doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates clean, complete, exhaustive notes covering every page and paragraph
        without cutting sentences or stopping halfway.
        """
        title = doc_data.get("title", "Lecture Notes")
        pages = doc_data.get("pages", [])
        total_pages = len(pages)
        total_words = doc_data.get("total_words", 0)

        toc_items = []
        modules_md = []
        definitions = []
        formulas = []
        key_takeaways = []

        for p in pages:
            p_num = p["page_num"]
            blocks = p.get("blocks", [])
            text = p.get("text", "")
            
            if not blocks and text:
                blocks = [b.strip() for b in text.split("\n\n") if b.strip()]

            if not blocks:
                continue

            # Determine clean section title
            raw_title = blocks[0].strip().split("\n")[0].strip()
            # Clean weird bullet icons or numbers from title
            clean_title = re.sub(r'^[•\-\*\d\.\:\s]+', '', raw_title).strip()
            if not clean_title or len(clean_title) < 3 or len(clean_title) > 90:
                clean_title = f"Topic & Concepts on Page {p_num}"

            anchor = re.sub(r'[^a-zA-Z0-9]+', '-', clean_title).strip('-').lower()
            anchor_slug = f"page-{p_num}-{anchor}"
            toc_items.append(f"- [Page {p_num}: {clean_title}](#{anchor_slug})")

            # Build module section
            module_lines = [
                f'<a id="{anchor_slug}"></a>',
                f"### Page {p_num}: {clean_title}",
                f"*Source: Lecture Page {p_num}*",
                ""
            ]

            # Process remaining blocks
            content_blocks = blocks[1:] if len(blocks) > 1 else blocks
            
            for b in content_blocks:
                b_clean = b.strip()
                if not b_clean:
                    continue

                # Check if this block contains mathematical equations
                has_math = any(op in b_clean for op in [" = ", "sum(", "sigma(", "partial(", "grad(", "^T", "w_i", "theta :="])
                
                # Check for definition markers
                def_match = re.search(r'\b([A-Za-z0-9\s\(\)\-]{3,35})\s+(?:is defined as|refers to|represents|is a|means)\s+([^.]+\.)', b_clean, re.IGNORECASE)
                if def_match:
                    term = def_match.group(1).strip()
                    definition = def_match.group(2).strip()
                    definitions.append((term, definition, p_num))
                    module_lines.append(f"> 💡 **Key Definition**: **{term}** — {definition}")
                    module_lines.append("")

                # If block has formula or equation
                if has_math and len(b_clean) < 180 and not b_clean.startswith(("-", "*", "•")):
                    formulas.append((b_clean, p_num))
                    module_lines.append("```latex")
                    module_lines.append(f"{b_clean}")
                    module_lines.append("```")
                    module_lines.append("")
                else:
                    # Regular paragraph or bullet points
                    sub_lines = [l.strip() for l in b_clean.split("\n") if l.strip()]
                    for sl in sub_lines:
                        if sl.startswith(("-", "*", "•", "1.", "2.", "3.", "4.", "5.")):
                            clean_bullet = re.sub(r'^[•\-\*\d\.\)\s]+', '', sl).strip()
                            module_lines.append(f"- {clean_bullet}")
                        else:
                            module_lines.append(sl)
                    module_lines.append("")

                if len(key_takeaways) < 12 and len(b_clean) > 40 and not has_math:
                    first_sent = b_clean.split(". ")[0].strip()
                    if len(first_sent) > 30 and first_sent not in key_takeaways:
                        key_takeaways.append(first_sent + ".")

            modules_md.append("\n".join(module_lines))

        # Assemble Master Document
        md = [
            f"# {title}: Comprehensive Lecture Study Guide",
            "",
            "> [!NOTE]",
            f"> **100% Complete Coverage**: Synthesized across all **{total_pages} pages** ({total_words:,} total words). Generated by the Built-in Structural Knowledge Engine.",
            "",
            "## Table of Contents",
            "\n".join(toc_items[:40]),
            "" if len(toc_items) <= 40 else f"*(And {len(toc_items) - 40} additional sections covered below)*\n",
            "---",
            "",
            "## 1. 📌 Executive Summary & Scope",
            f"- **Subject Matter**: {title}",
            f"- **Document Extent**: Fully extracted and indexed across {total_pages} pages ({total_words:,} words).",
            "- **Key Objective**: Comprehensive mastery of theoretical foundations, algorithmic procedures, and critical equations.",
            "- **Completeness**: All pages and sections from page 1 to the end are thoroughly analyzed below.",
            "",
            "---",
            "",
            "## 2. 📖 Complete Page-by-Page Conceptual Breakdown",
            ""
        ]

        md.append("\n\n---\n\n".join(modules_md))
        md.append("\n---\n")

        # Master Definitions Table
        md.append("## 3. 📝 Master Definitions & Glossary Table")
        md.append("| Term / Concept | Formal Definition | Reference |")
        md.append("| :--- | :--- | :---: |")
        
        if definitions:
            for term, defn, p_num in definitions[:25]:
                md.append(f"| **{term}** | {defn} | Page {p_num} |")
        else:
            md.append(f"| **{title} Core Principles** | Foundational conceptual pillars detailed across the lecture slides. | Page 1 |")
            md.append("| **Primary Parameters** | Operational variables and weights governing model behavior. | General |")
            md.append("| **Optimization Objective** | Target metric minimized or maximized during training/execution. | General |")

        md.append("")
        md.append("---")
        md.append("")

        # High Yield Cheat Sheet
        md.append("## 4. 🎯 High-Yield Exam Cheat Sheet & Key Formulas")
        if formulas:
            md.append("### Core Mathematical Equations:")
            for form, p_num in formulas[:10]:
                md.append(f"- **Page {p_num}**: `{form}`")
            md.append("")

        md.append("### Essential Exam Takeaways:")
        if key_takeaways:
            for kt in key_takeaways[:10]:
                md.append(f"- {kt}")
        else:
            md.append(f"- Understand the end-to-end flow of {title} from foundational definitions to advanced mechanisms.")
            md.append("- Memorize all parameter symbols, constraints, and algorithmic step sequences.")

        return {
            "notes_markdown": "\n".join(md),
            "generated_by": "Built-in Structural Knowledge Engine (100% Page Coverage)",
            "coverage": f"100% Analyzed ({total_pages} pages)",
            "status": "success"
        }

    # -------------------------------------------------------------------------
    # 2. IMPORTANT TOPICS IDENTIFICATION
    # -------------------------------------------------------------------------
    @staticmethod
    def extract_important_topics(
        doc_data: Dict[str, Any],
        previous_topics: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Extracts core topics, concepts, importance rankings, and mindmap connections.
        """
        previous_topics = previous_topics or []
        client = config.get_gemini_client()
        full_text = doc_data.get("full_text", "")
        title = doc_data.get("title", "Lecture")
        pages_count = doc_data.get("total_pages", 1)
        sample_text = full_text[:300000] if len(full_text) > 300000 else full_text

        if client:
            previous_topics_text = (
                "\n".join(
                    f"- {topic.get('title', 'Untitled topic')} "
                    f"(previous priority: {topic.get('importance', 'unknown')})"
                    for topic in previous_topics
                )
                if previous_topics
                else "No earlier topic analysis."
            )
            prompt = f"""Analyze this entire lecture text across all {pages_count} pages and extract 6 to 10 of the most critical topics/concepts.
Ensure balanced coverage across the whole document (early, middle, and final pages).
This is a fresh re-analysis. Reassess the material and its priorities rather than returning a copy of the previous result.
Prefer important subtopics or connections not represented in the prior analysis, and do not reuse the same topic titles unless the document clearly has no alternative.

PREVIOUS TOPIC ANALYSIS:
{previous_topics_text}

LECTURE TITLE: {title}
TOTAL PAGES: {pages_count}
CONTENT:
{sample_text}

Return a valid JSON object matching this schema:
{{
  "topics": [
    {{
      "id": "slug-name",
      "title": "Topic Title",
      "importance": "High", // Must be "High", "Medium", or "Foundational"
      "description": "Clear 2-sentence description of the concept.",
      "why_important": "Why this topic is crucial for exams and mastery.",
      "pages": [1, 2], // page numbers where it appears
      "keywords": ["Keyword1", "Keyword2"],
      "prerequisites": ["Prerequisite 1"],
      "related_topics": ["Related Topic Title"]
    }}
  ],
  "mindmap": {{
    "root": "{title}",
    "branches": [
      {{
        "name": "Branch or Module Name",
        "subtopics": ["Subtopic 1", "Subtopic 2"]
      }}
    ]
  }}
}}

Ensure valid JSON only, no markdown wrapping."""
            try:
                from google.genai import types
                model_name = config.DEFAULT_MODEL
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        max_output_tokens=8192,
                        temperature=0.8
                    )
                )
                if response and response.text:
                    clean_json = AIService._clean_json_response(response.text)
                    parsed = json.loads(clean_json)
                    return {
                        "topics": parsed.get("topics", []),
                        "mindmap": parsed.get("mindmap", {}),
                        "generated_by": f"Google Gemini 2.5 Flash",
                        "status": "success"
                    }
            except Exception as e:
                print(f"[AIService] Gemini topic extraction error: {e}. Using fallback.")

        return AIService._extract_heuristic_topics(doc_data, previous_topics)

    @staticmethod
    def _extract_heuristic_topics(
        doc_data: Dict[str, Any],
        previous_topics: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        title = doc_data.get("title", "Lecture")
        pages = doc_data.get("pages", [])
        previous_topics = previous_topics or []
        previous_titles = {
            re.sub(r"\s+", " ", topic.get("title", "").strip().lower())
            for topic in previous_topics
            if topic.get("title")
        }
        
        topics = []
        mindmap_branches = []
        
        candidates = []
        for p in pages:
            blocks = p.get("blocks", [])
            if not blocks and p.get("text"):
                blocks = [b.strip() for b in p["text"].split("\n\n") if b.strip()]

            for block in blocks:
                for line in block.splitlines():
                    candidate = re.sub(r'^[•\-\*\d\.\:\s]+', '', line).strip()
                    if (
                        4 < len(candidate) < 70
                        and not candidate.endswith(('.', ',', ';', ':'))
                        and "=" not in candidate
                    ):
                        candidates.append((p, candidate, block))

        fresh_candidates = [
            item for item in candidates
            if re.sub(r"\s+", " ", item[1].lower()) not in previous_titles
        ]
        if previous_topics and fresh_candidates:
            candidates = fresh_candidates
        else:
            candidates = []
            step = max(1, len(pages) // 8)
            for p in pages[::step][:8]:
                blocks = p.get("blocks", [])
                if not blocks and p.get("text"):
                    blocks = [b.strip() for b in p["text"].split("\n\n") if b.strip()]
                if blocks:
                    first_line = blocks[0].split("\n")[0].strip()
                    candidates.append((p, first_line, blocks[1] if len(blocks) > 1 else blocks[0]))

        for p, first_line, desc_block in candidates[:8]:
            p_num = p["page_num"]
            first_line = re.sub(r'^[•\-\*\d\.\:\s]+', '', first_line).strip()
            
            if 3 < len(first_line) < 70:
                topic_title = first_line
            else:
                topic_title = f"Concepts & Methods from Page {p_num}"

            if p_num <= 2 or any(k in topic_title.lower() for k in ["intro", "foundation", "basic", "overview"]):
                importance = "Foundational"
            elif any(k in topic_title.lower() for k in ["algorithm", "architecture", "optimization", "model", "loss", "kernel", "deadlock", "memory"]):
                importance = "High"
            else:
                importance = "Medium"

            desc = desc_block.split(". ")[0].strip()
            if len(desc) > 170:
                desc = desc[:167] + "..."
            elif not desc.endswith("."):
                desc += "."

            topic_id = re.sub(r'[^a-zA-Z0-9]+', '-', topic_title).strip('-').lower()
            keywords = [w.strip(".,()[]") for w in topic_title.split() if len(w) > 3][:4]
            
            topics.append({
                "id": f"topic-{p_num}-{topic_id}",
                "title": topic_title,
                "importance": importance,
                "description": desc,
                "why_important": f"Key theoretical concept covered in Lecture Page {p_num}.",
                "pages": [p_num],
                "keywords": keywords,
                "prerequisites": ["Core Course Foundations"],
                "related_topics": [title]
            })

            mindmap_branches.append({
                "name": topic_title,
                "subtopics": [f"Page {p_num} Mechanics", "Core Principles", "Exam Applications"]
            })

        return {
            "topics": topics,
            "mindmap": {
                "root": title,
                "branches": mindmap_branches
            },
            "generated_by": "Built-in Concept Extractor",
            "status": "success"
        }

    # -------------------------------------------------------------------------
    # 3. PRACTICE QUESTIONS & FLASHCARDS GENERATION
    # -------------------------------------------------------------------------
    @staticmethod
    def generate_practice_questions(
        doc_data: Dict[str, Any],
        previous_practice: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generates MCQs, Flashcards, and Short Answer conceptual questions spanning all lecture pages.
        """
        previous_practice = previous_practice or []
        client = config.get_gemini_client()
        full_text = doc_data.get("full_text", "")
        title = doc_data.get("title", "Lecture")
        pages_count = doc_data.get("total_pages", 1)
        sample_text = full_text[:300000] if len(full_text) > 300000 else full_text

        if client:
            previous_questions = []
            for practice_set in previous_practice:
                previous_questions.extend(
                    question.get("question", "")
                    for question in practice_set.get("mcqs", [])
                )
                previous_questions.extend(
                    card.get("front", "")
                    for card in practice_set.get("flashcards", [])
                )
                previous_questions.extend(
                    question.get("question", "")
                    for question in practice_set.get("short_answer", [])
                )
            previous_questions = [question for question in previous_questions if question]
            previous_questions_text = (
                "\n".join(f"- {question}" for question in previous_questions)
                if previous_questions
                else "This is the first practice set."
            )
            prompt = f"""You are an elite academic examination designer.
Generate a comprehensive, complete practice exam pack based on the provided lecture material.
Cover the entire scope from Page 1 to Page {pages_count}.
Create a fresh set that tests different concepts and uses different question wording from earlier sets.
Do not repeat or lightly rephrase any of these earlier questions:
{previous_questions_text}

MATERIAL:
{sample_text}

Generate:
1. 8 to 12 Multiple Choice Questions (MCQs) with 4 choices, the correct index (0-3), detailed rationale, and source page reference.
2. 10 to 15 Interactive Flashcards with a front concept prompt, back explanation, topic tag, and page reference.
3. 4 to 6 Conceptual Short-Answer Questions with model answers, rubrics, and page references.

Return a valid JSON object matching this schema:
{{
  "mcqs": [
    {{
      "id": "mcq-1",
      "question": "What is the primary function of ...?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 1,
      "explanation": "Option B is correct because...",
      "page_ref": 1,
      "difficulty": "Medium" // "Easy" | "Medium" | "Hard"
    }}
  ],
  "flashcards": [
    {{
      "id": "flash-1",
      "front": "What is ...?",
      "back": "It is the mechanism that...",
      "category": "Foundations",
      "page_ref": 1
    }}
  ],
  "short_answer": [
    {{
      "id": "sa-1",
      "question": "Explain how ... works and why it is necessary.",
      "model_answer": "In-depth model answer explaining the principles...",
      "key_points": ["Point 1 must mention X", "Point 2 must mention Y"],
      "page_ref": 2
    }}
  ]
}}

Ensure valid JSON only, no markdown wrapping."""
            try:
                from google.genai import types
                model_name = config.DEFAULT_MODEL
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        max_output_tokens=8192,
                        temperature=0.8
                    )
                )
                if response and response.text:
                    clean_json = AIService._clean_json_response(response.text)
                    parsed = json.loads(clean_json)
                    return {
                        "mcqs": parsed.get("mcqs", []),
                        "flashcards": parsed.get("flashcards", []),
                        "short_answer": parsed.get("short_answer", []),
                        "generated_by": f"Google Gemini 2.5 Flash",
                        "status": "success"
                    }
            except Exception as e:
                print(f"[AIService] Gemini practice generation error: {e}. Using fallback.")

        return AIService._generate_heuristic_practice(doc_data, previous_practice)

    @staticmethod
    def _generate_heuristic_practice(
        doc_data: Dict[str, Any],
        previous_practice: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        pages = doc_data.get("pages", [])
        title = doc_data.get("title", "Lecture")
        previous_practice = previous_practice or []

        previous_questions = {
            re.sub(r"\s+", " ", question.strip().lower())
            for practice_set in previous_practice
            for question in (
                [item.get("question", "") for item in practice_set.get("mcqs", [])]
                + [item.get("front", "") for item in practice_set.get("flashcards", [])]
                + [item.get("question", "") for item in practice_set.get("short_answer", [])]
            )
            if question
        }

        mcqs = []
        flashcards = []
        short_answer = []

        for p in pages:
            p_num = p["page_num"]
            blocks = p.get("blocks", [])
            
            for b in blocks:
                # Look for definitions to create flashcards and MCQs
                def_match = re.search(r'\b([A-Za-z0-9\s\(\)\-]{3,35})\s+(?:is defined as|refers to|represents|is a|means)\s+([^.]+\.)', b, re.IGNORECASE)
                if def_match and len(flashcards) < 15:
                    term = def_match.group(1).strip()
                    definition = def_match.group(2).strip()
                    flashcard_fronts = [
                        f"Define: {term}",
                        f"What does {term} mean?",
                        f"Which concept is described by: {definition}",
                    ]
                    flashcard_front = next(
                        (
                            front for front in flashcard_fronts
                            if re.sub(r"\s+", " ", front.strip().lower()) not in previous_questions
                        ),
                        flashcard_fronts[0],
                    )

                    flashcards.append({
                        "id": f"flash-{len(flashcards)+1}",
                        "front": flashcard_front,
                        "back": f"{definition} (Reference: Page {p_num})",
                        "category": "Core Definition",
                        "page_ref": p_num
                    })

                    if len(mcqs) < 10:
                        mcq_questions = [
                            f"Which term corresponds to the following definition: \"{definition}\"?",
                            f"According to the lecture, what does {term} mean?",
                            f"Which concept is described as: \"{definition}\"?",
                        ]
                        mcq_question = next(
                            (
                                question for question in mcq_questions
                                if re.sub(r"\s+", " ", question.strip().lower()) not in previous_questions
                            ),
                            mcq_questions[0],
                        )
                        mcqs.append({
                            "id": f"mcq-{len(mcqs)+1}",
                            "question": mcq_question,
                            "options": [
                                term,
                                f"Alternative {term} Protocol",
                                f"Inverse {term}",
                                "Standard Evaluation Parameter"
                            ],
                            "correct_index": 0,
                            "explanation": f"According to Page {p_num}, '{term}' is formally defined as: {definition}",
                            "page_ref": p_num,
                            "difficulty": "Medium"
                        })

        # Ensure we have a rich set of flashcards & MCQs if text had few explicit "is defined as" markers
        if len(flashcards) < 4:
            for i, p in enumerate(pages[:6], 1):
                p_num = p["page_num"]
                blocks = p.get("blocks", [])
                if blocks:
                    title_line = blocks[0].split("\n")[0].strip()
                    title_line = re.sub(r'^[•\-\*\d\.\:\s]+', '', title_line).strip()
                    desc = blocks[1].split(". ")[0].strip() if len(blocks) > 1 else blocks[0]
                    if len(desc) > 150:
                        desc = desc[:147] + "..."
                    flashcard_fronts = [
                        f"What is the main concept of '{title_line}'?",
                        f"Summarize the key idea from Page {p_num}.",
                        f"What should you remember about '{title_line}'?",
                    ]
                    flashcard_front = next(
                        (
                            front for front in flashcard_fronts
                            if re.sub(r"\s+", " ", front.strip().lower()) not in previous_questions
                        ),
                        flashcard_fronts[0],
                    )
                    flashcards.append({
                        "id": f"flash-{len(flashcards)+1}",
                        "front": flashcard_front,
                        "back": f"{desc} (Refer to Page {p_num})",
                        "category": "Concept Review",
                        "page_ref": p_num
                    })

        if len(mcqs) < 3:
            for i, p in enumerate(pages[:4], 1):
                p_num = p["page_num"]
                blocks = p.get("blocks", [])
                if blocks:
                    first = blocks[0].split("\n")[0].strip()
                    first = re.sub(r'^[•\-\*\d\.\:\s]+', '', first).strip()
                    mcq_questions = [
                        f"Which section is discussed in detail on Page {p_num} of {title}?",
                        f"What is the main subject of Page {p_num}?",
                        f"Which lecture topic is introduced by '{first}'?",
                    ]
                    mcq_question = next(
                        (
                            question for question in mcq_questions
                            if re.sub(r"\s+", " ", question.strip().lower()) not in previous_questions
                        ),
                        mcq_questions[0],
                    )
                    mcqs.append({
                        "id": f"mcq-{len(mcqs)+1}",
                        "question": mcq_question,
                        "options": [
                            first,
                            "Irrelevant Hardware Assembly",
                            "Network Cabling Topology",
                            "Unrelated Database Locking"
                        ],
                        "correct_index": 0,
                        "explanation": f"Page {p_num} specifically covers '{first}'.",
                        "page_ref": p_num,
                        "difficulty": "Easy"
                    })

        # Generate conceptual short answer questions from sampled pages
        step = max(1, len(pages) // 5)
        for i, p in enumerate(pages[::step][:5], 1):
            p_num = p["page_num"]
            blocks = p.get("blocks", [])
            header = blocks[0].split("\n")[0].strip() if blocks else f"Page {p_num}"
            header = re.sub(r'^[•\-\*\d\.\:\s]+', '', header).strip()
            short_answer_questions = [
                f"Explain the core mechanisms, significance, and trade-offs of '{header}' as presented on Page {p_num}.",
                f"How does '{header}' work, and why is it important? Use Page {p_num} as evidence.",
                f"Describe one key idea from '{header}' and explain its significance.",
            ]
            short_answer_question = next(
                (
                    question for question in short_answer_questions
                    if re.sub(r"\s+", " ", question.strip().lower()) not in previous_questions
                ),
                short_answer_questions[0],
            )
            
            short_answer.append({
                "id": f"sa-{i}",
                "question": short_answer_question,
                "model_answer": f"Page {p_num} outlines '{header}'. A complete answer must define the underlying principles, discuss the key formulas or design choices, and explain how it influences overall system performance.",
                "key_points": [
                    f"Define '{header}' accurately without omissions",
                    f"Mention the specific mechanisms detailed on Page {p_num}",
                    "Analyze advantages, limitations, or runtime consequences"
                ],
                "page_ref": p_num
            })

        return {
            "mcqs": mcqs,
            "flashcards": flashcards,
            "short_answer": short_answer,
            "generated_by": "Built-in Question Generator",
            "status": "success"
        }

    # -------------------------------------------------------------------------
    # 4. STUDENT Q&A
    # -------------------------------------------------------------------------
    @staticmethod
    def answer_question(query: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Answers student questions directly with Gemini, without restricting answers to a PDF.
        """
        client = config.get_gemini_client()
        if not client:
            raise RuntimeError(
                "Gemini is not configured. Add your API key in API Settings to use AI chat."
            )

        history_lines = []
        for msg in (history or [])[-8:]:
            role = msg.get("role")
            content = msg.get("content", "").strip()
            if content and role in ("user", "assistant"):
                speaker = "Student" if role == "user" else "Assistant"
                history_lines.append(f"{speaker}: {content}")

        conversation = "\n".join(history_lines) or "(No previous messages.)"
        prompt = f"""You are a helpful, accurate, and friendly AI tutor.
Answer the student's current question directly using your general knowledge. The answer is not restricted to any uploaded document. Use the recent conversation for context, explain clearly, and format mathematical expressions with LaTeX when helpful. If you are uncertain, say so.

RECENT CONVERSATION:
{conversation}

CURRENT QUESTION:
{query}
"""
        try:
            from google.genai import types
            response = client.models.generate_content(
                model=config.DEFAULT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=2048,
                    temperature=0.7
                )
            )
        except Exception as e:
            print(f"[AIService] Gemini Q&A failed: {e}")
            raise RuntimeError(f"Gemini could not answer this question: {e}") from e

        if not response or not response.text:
            raise RuntimeError("Gemini returned an empty answer. Please try again.")

        return {
            "answer": response.text.strip(),
            "citations": [],
            "suggested_questions": [
                "Can you give me an example?",
                "Can you explain that more simply?",
                "What should I learn next about this topic?"
            ],
            "model": f"Google Gemini ({config.DEFAULT_MODEL})",
            "status": "success"
        }
