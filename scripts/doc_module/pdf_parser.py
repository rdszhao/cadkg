"""PDF document parser for extracting text and structure from technical documentation."""

import os
from typing import Dict, List, Any
import pymupdf  # PyMuPDF


class PDFParser:
    """Extract text, structure, and metadata from PDF documents."""

    def __init__(self, pdf_path: str):
        """Initialize PDF parser.

        Args:
            pdf_path: Path to PDF file
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        self.pdf_path = pdf_path
        self.doc = pymupdf.open(pdf_path)
        self.metadata = self.doc.metadata

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close PDF document."""
        if self.doc:
            self.doc.close()

    def get_text_by_page(self) -> List[Dict[str, Any]]:
        """Extract text content organized by page.

        Returns:
            List of page dictionaries with text and metadata
        """
        pages = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            pages.append({
                "page_number": page_num + 1,
                "text": page.get_text("text"),
                "width": page.rect.width,
                "height": page.rect.height
            })
        return pages

    def get_full_text(self) -> str:
        """Extract all text from PDF as single string.

        Returns:
            Complete text content
        """
        text_parts = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text_parts.append(page.get_text("text"))
        return "\n\n".join(text_parts)

    def get_structured_text(self) -> List[Dict[str, Any]]:
        """Extract text with structural information (blocks, lines).

        Returns:
            List of structured text elements
        """
        structured_data = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        line_text = " ".join([
                            span["text"] for span in line.get("spans", [])
                        ])
                        if line_text.strip():
                            structured_data.append({
                                "page": page_num + 1,
                                "text": line_text.strip(),
                                "bbox": line.get("bbox"),
                                "type": "text_line"
                            })

        return structured_data

    def get_tables(self) -> List[Dict[str, Any]]:
        """Extract tables from PDF using layout analysis.

        Returns:
            List of detected tables
        """
        tables = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            # Simple table detection based on text positioning
            # This is a basic implementation - could be enhanced with proper table detection
            tabs = page.find_tables()
            for tab in tabs:
                try:
                    table_data = tab.extract()
                    if table_data:
                        tables.append({
                            "page": page_num + 1,
                            "data": table_data,
                            "bbox": tab.bbox
                        })
                except Exception as e:
                    print(f"Warning: Could not extract table on page {page_num + 1}: {e}")

        return tables

    def get_metadata(self) -> Dict[str, Any]:
        """Get PDF metadata.

        Returns:
            Dictionary of metadata fields
        """
        return {
            "title": self.metadata.get("title", ""),
            "author": self.metadata.get("author", ""),
            "subject": self.metadata.get("subject", ""),
            "keywords": self.metadata.get("keywords", ""),
            "creator": self.metadata.get("creator", ""),
            "producer": self.metadata.get("producer", ""),
            "creation_date": self.metadata.get("creationDate", ""),
            "modification_date": self.metadata.get("modDate", ""),
            "page_count": len(self.doc)
        }

    def get_toc(self) -> List[Dict[str, Any]]:
        """Extract table of contents if available.

        Returns:
            List of TOC entries
        """
        toc = self.doc.get_toc()
        return [
            {
                "level": item[0],
                "title": item[1],
                "page": item[2]
            }
            for item in toc
        ]

    def extract_all(self) -> Dict[str, Any]:
        """Extract all available information from PDF.

        Returns:
            Complete extraction results
        """
        return {
            "metadata": self.get_metadata(),
            "toc": self.get_toc(),
            "pages": self.get_text_by_page(),
            "full_text": self.get_full_text(),
            "structured_text": self.get_structured_text(),
            "tables": self.get_tables()
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics about the PDF.

        Returns:
            Summary information
        """
        full_text = self.get_full_text()
        word_count = len(full_text.split())
        char_count = len(full_text)

        return {
            "file_path": self.pdf_path,
            "page_count": len(self.doc),
            "word_count": word_count,
            "character_count": char_count,
            "has_toc": len(self.get_toc()) > 0,
            "table_count": len(self.get_tables()),
            "metadata": self.get_metadata()
        }


def parse_pdf(pdf_path: str) -> Dict[str, Any]:
    """Convenience function to parse PDF and return all data.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Complete extraction results
    """
    with PDFParser(pdf_path) as parser:
        return parser.extract_all()
