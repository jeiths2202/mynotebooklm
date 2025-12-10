import re
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

import PyPDF2
from docx import Document as DocxDocument

from app.config import settings


@dataclass
class TextChunk:
    """Represents a chunk of text from a document"""
    text: str
    metadata: Dict[str, Any]


class DocumentProcessor:
    """Processes documents (PDF, TXT, DOCX) and splits into chunks"""

    def __init__(
        self,
        chunk_size: int = settings.chunk_size,
        chunk_overlap: int = settings.chunk_overlap
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_file(self, file_path: Path, document_id: str) -> List[TextChunk]:
        """Process a file and return list of text chunks"""
        file_type = file_path.suffix.lower()

        if file_type == ".pdf":
            text = self._extract_pdf(file_path)
        elif file_type == ".docx":
            text = self._extract_docx(file_path)
        elif file_type == ".txt":
            text = self._extract_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        return self._chunk_text(text, document_id, file_path.name)

    def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file"""
        text_parts = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {page_num + 1}]\n{page_text}")
        return "\n\n".join(text_parts)

    def _extract_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file"""
        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    def _extract_txt(self, file_path: Path) -> str:
        """Extract text from TXT file"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _chunk_text(
        self,
        text: str,
        document_id: str,
        filename: str
    ) -> List[TextChunk]:
        """Split text into overlapping chunks"""
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()

        if not text:
            return []

        chunks = []
        words = text.split()

        start = 0
        chunk_index = 0

        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            chunks.append(TextChunk(
                text=chunk_text,
                metadata={
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": chunk_index,
                }
            ))

            chunk_index += 1
            start += self.chunk_size - self.chunk_overlap

            # Prevent infinite loop for small texts
            if end >= len(words):
                break

        return chunks
