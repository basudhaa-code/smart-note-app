import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any
import fitz  # PyMuPDF

class PDFProcessor:
    @staticmethod
    def extract_pdf_content(file_path: str, doc_id: str, original_filename: str) -> Dict[str, Any]:
        """
        Extracts structured text, page metadata, clean paragraphs, and semantic chunks from a PDF.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        doc = fitz.open(file_path)
        total_pages = len(doc)
        
        pages_data = []
        full_text_list = []
        chunks = []
        chunk_idx = 0

        # Attempt to get title from metadata or fallback to clean filename
        doc_meta = doc.metadata or {}
        extracted_title = doc_meta.get("title", "").strip()
        if not extracted_title or len(extracted_title) < 3:
            extracted_title = path.stem
            # Clean up UUID prefix if present e.g. "82863e70_backpropagation_notes"
            if re.match(r'^[a-f0-9]{8}_', extracted_title):
                extracted_title = extracted_title[9:]
            extracted_title = extracted_title.replace("_", " ").replace("-", " ").title()

        total_word_count = 0

        for page_num in range(total_pages):
            page = doc[page_num]
            display_page_num = page_num + 1

            # Extract blocks rather than raw text to preserve paragraph structures
            blocks = page.get_text("blocks")
            cleaned_blocks = []
            detected_headings = []

            for b in blocks:
                # b = (x0, y0, x1, y1, text, block_no, block_type)
                # block_type 0 is text, 1 is image
                if len(b) > 4 and b[6] == 0:
                    raw_block_text = b[4]
                    clean_text = PDFProcessor._clean_block_text(raw_block_text)
                    if clean_text:
                        cleaned_blocks.append(clean_text)
                        # Check if first line of block looks like a heading
                        first_line = clean_text.split("\n")[0].strip()
                        if 3 < len(first_line) < 70 and not first_line.endswith(('.', ',', ';')):
                            detected_headings.append(first_line)

            page_text = "\n\n".join(cleaned_blocks)
            page_words = len(page_text.split())
            total_word_count += page_words

            pages_data.append({
                "page_num": display_page_num,
                "text": page_text,
                "blocks": cleaned_blocks,
                "headings": detected_headings,
                "word_count": page_words,
                "char_count": len(page_text)
            })

            if page_text:
                full_text_list.append(f"--- [Page {display_page_num}] ---\n{page_text}")

            # Generate chunks for this page
            page_chunks = PDFProcessor._create_page_chunks(page_text, display_page_num, chunk_idx)
            chunk_idx += len(page_chunks)
            chunks.extend(page_chunks)

        doc.close()

        if not chunks:
            chunks.append({
                "chunk_id": "chunk_0",
                "page_num": 1,
                "text": "No extractable text found in this document. It may consist of scanned images or protected content."
            })

        reading_time_minutes = max(1, round(total_word_count / 200))

        result = {
            "doc_id": doc_id,
            "filename": original_filename,
            "title": extracted_title,
            "total_pages": total_pages,
            "total_words": total_word_count,
            "reading_time_min": reading_time_minutes,
            "pages": pages_data,
            "chunks": chunks,
            "full_text": "\n\n".join(full_text_list)
        }
        
        return result

    @staticmethod
    def _clean_block_text(raw_text: str) -> str:
        """
        Cleans and reconstructs wrapped lines inside a block into coherent paragraphs,
        stripping non-printable Unicode bullet glyphs (e.g. \uf0d8).
        """
        if not raw_text:
            return ""

        # Remove common Private Use Area bullet icons used in Word/PowerPoint PDFs
        text = re.sub(r'[\uf000-\uf8ff]', '', raw_text)
        # Normalize newlines
        text = re.sub(r'\r\n|\r', '\n', text)

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return ""

        cleaned = []
        current_para = lines[0]

        for next_line in lines[1:]:
            # If line starts with a list marker, bullet, or number
            if re.match(r'^(?:[•\-\*]|\d+[\.\)])\s+', next_line):
                cleaned.append(current_para)
                current_para = next_line
            # If previous line ends with a continuation hyphen
            elif current_para.endswith('-') and not current_para.endswith(' -'):
                current_para = current_para[:-1] + next_line
            # If previous line does not end with sentence-ending punctuation, join with a space
            elif not re.search(r'[\.:;!?]$', current_para):
                current_para += " " + next_line
            else:
                cleaned.append(current_para)
                current_para = next_line

        cleaned.append(current_para)
        return "\n".join(cleaned).strip()

    @staticmethod
    def _create_page_chunks(text: str, page_num: int, start_idx: int, target_size: int = 800, overlap: int = 150) -> List[Dict[str, Any]]:
        """
        Breaks page text into overlapping semantic chunks with complete sentence preservation.
        """
        if not text:
            return []

        chunks = []
        idx = start_idx
        
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text]

        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < target_size:
                current_chunk = (current_chunk + "\n\n" + para).strip()
            else:
                if current_chunk:
                    chunks.append({
                        "chunk_id": f"chunk_{idx}",
                        "page_num": page_num,
                        "text": current_chunk
                    })
                    idx += 1
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else ""
                    current_chunk = (overlap_text + "\n" + para).strip()
                else:
                    sentences = re.split(r'(?<=[.?!])\s+', para)
                    temp_chunk = ""
                    for s in sentences:
                        if len(temp_chunk) + len(s) < target_size:
                            temp_chunk = (temp_chunk + " " + s).strip()
                        else:
                            if temp_chunk:
                                chunks.append({
                                    "chunk_id": f"chunk_{idx}",
                                    "page_num": page_num,
                                    "text": temp_chunk
                                })
                                idx += 1
                                temp_chunk = s
                            else:
                                chunks.append({
                                    "chunk_id": f"chunk_{idx}",
                                    "page_num": page_num,
                                    "text": s
                                })
                                idx += 1
                    current_chunk = temp_chunk

        if current_chunk:
            chunks.append({
                "chunk_id": f"chunk_{idx}",
                "page_num": page_num,
                "text": current_chunk
            })

        return chunks
