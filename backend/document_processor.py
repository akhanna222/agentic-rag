"""
Document Processor using OpenAI Vision API
Handles PDF, JSON, Images, and Markdown files
"""
import base64
import json
import io
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF for PDF processing
from PIL import Image
from openai import OpenAI

from config import (
    OPENAI_API_KEY,
    VISION_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SUPPORTED_EXTENSIONS
)


class DocumentProcessor:
    """Process various document types into text chunks for RAG"""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def process_document(self, file_path: Path, file_content: bytes = None) -> Dict[str, Any]:
        """
        Process a document and return extracted text with metadata

        Args:
            file_path: Path to the document
            file_content: Optional bytes content (for uploaded files)

        Returns:
            Dict with 'text', 'chunks', 'metadata'
        """
        extension = file_path.suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {extension}")

        # Extract text based on file type
        if extension == ".pdf":
            text = self._process_pdf(file_path, file_content)
        elif extension == ".json":
            text = self._process_json(file_path, file_content)
        elif extension in {".png", ".jpg", ".jpeg", ".gif"}:
            text = self._process_image(file_path, file_content)
        elif extension in {".md", ".txt"}:
            text = self._process_text(file_path, file_content)
        else:
            raise ValueError(f"Unsupported file type: {extension}")

        # Create chunks
        chunks = self._create_chunks(text)

        return {
            "text": text,
            "chunks": chunks,
            "metadata": {
                "filename": file_path.name,
                "extension": extension,
                "chunk_count": len(chunks)
            }
        }

    def _process_pdf(self, file_path: Path, file_content: bytes = None) -> str:
        """Process PDF using PyMuPDF and OpenAI Vision for images"""
        all_text = []

        if file_content:
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
        else:
            pdf_document = fitz.open(file_path)

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]

            # Extract text directly
            text = page.get_text()

            # If page has images or text extraction is poor, use Vision API
            images = page.get_images()

            if images or len(text.strip()) < 50:
                # Render page as image and use Vision API
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for clarity
                img_bytes = pix.tobytes("png")

                vision_text = self._extract_text_from_image(img_bytes)
                if vision_text:
                    text = f"[Page {page_num + 1}]\n{vision_text}"
            else:
                text = f"[Page {page_num + 1}]\n{text}"

            all_text.append(text)

        pdf_document.close()
        return "\n\n".join(all_text)

    def _process_json(self, file_path: Path, file_content: bytes = None) -> str:
        """Process JSON file into readable text"""
        if file_content:
            data = json.loads(file_content.decode('utf-8'))
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

        # Convert JSON to structured text
        text = self._json_to_text(data)
        return text

    def _json_to_text(self, data: Any, prefix: str = "") -> str:
        """Recursively convert JSON to readable text"""
        lines = []

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._json_to_text(value, prefix + "  "))
                else:
                    lines.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}Item {i + 1}:")
                    lines.append(self._json_to_text(item, prefix + "  "))
                else:
                    lines.append(f"{prefix}- {item}")
        else:
            lines.append(f"{prefix}{data}")

        return "\n".join(lines)

    def _process_image(self, file_path: Path, file_content: bytes = None) -> str:
        """Process image using OpenAI Vision API"""
        if file_content:
            img_bytes = file_content
        else:
            with open(file_path, 'rb') as f:
                img_bytes = f.read()

        return self._extract_text_from_image(img_bytes)

    def _process_text(self, file_path: Path, file_content: bytes = None) -> str:
        """Process text/markdown files"""
        if file_content:
            return file_content.decode('utf-8')
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

    def _extract_text_from_image(self, image_bytes: bytes) -> str:
        """Use OpenAI Vision API to extract text from image"""
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        try:
            response = self.client.chat.completions.create(
                model=VISION_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a precise document parser. Extract ALL text content from this image exactly as it appears.

Instructions:
- Extract all visible text, including headers, paragraphs, tables, lists, and captions
- Preserve the structure and formatting as much as possible
- For tables, format them clearly with separators
- For medical/scientific documents, pay special attention to:
  - Drug names, dosages, and instructions
  - Medical terminology and abbreviations
  - References and citations
  - Charts, graphs, and their labels
- If there are handwritten notes, transcribe them with [handwritten] marker
- Do not summarize - extract the complete text"""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Vision API error: {e}")
            return ""

    def _create_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks with metadata"""
        chunks = []

        # Split by paragraphs first to maintain context
        paragraphs = text.split('\n\n')
        current_chunk = ""
        chunk_id = 0

        for para in paragraphs:
            # If adding this paragraph exceeds chunk size
            if len(current_chunk) + len(para) > CHUNK_SIZE:
                if current_chunk:
                    chunks.append({
                        "id": chunk_id,
                        "text": current_chunk.strip(),
                        "char_count": len(current_chunk.strip())
                    })
                    chunk_id += 1

                    # Keep overlap from end of current chunk
                    overlap_start = max(0, len(current_chunk) - CHUNK_OVERLAP)
                    current_chunk = current_chunk[overlap_start:] + "\n\n" + para
                else:
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "id": chunk_id,
                "text": current_chunk.strip(),
                "char_count": len(current_chunk.strip())
            })

        return chunks


# Singleton instance
_processor = None

def get_processor() -> DocumentProcessor:
    """Get or create document processor instance"""
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor
