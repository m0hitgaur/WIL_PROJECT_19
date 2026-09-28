"""
Document Parser using Docling.
Extracts structural text, hierarchical markdown headers, page numbers, and tables.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import logging
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc import DoclingDocument
from config import settings

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parses PDF documents into structured DoclingDocument representations."""

    def __init__(self, generate_table_images: bool = True):
        self.pipeline_options = PdfPipelineOptions()
        self.pipeline_options.do_ocr = False  # Fast digital extraction for vector financial PDFs
        self.pipeline_options.generate_page_images = True
        self.pipeline_options.generate_table_images = generate_table_images

        self.converter = DocumentConverter(
            format_options={
                "pdf": PdfFormatOption(pipeline_options=self.pipeline_options)
            }
        )

    def parse_pdf(self, file_path: Path) -> DoclingDocument:
        """
        Convert a PDF file into a DoclingDocument.
        
        Args:
            file_path: Path to the target PDF file.
            
        Returns:
            DoclingDocument containing structural elements, hierarchy, and tables.
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found at: {path}")

        logger.info(f"Parsing PDF document: {path.name}")
        result = self.converter.convert(path)
        return result.document

    def export_markdown(self, doc: DoclingDocument) -> str:
        """Export the parsed document to structured Markdown with headers."""
        return doc.export_to_markdown()


# Singleton parser instance
document_parser = DocumentParser()
