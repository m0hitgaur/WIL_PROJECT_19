"""
Table Extraction and VLM Transcription.
Extracts table bounding box image crops and sends them to a Vision-Language Model (VLM)
via Ollama for accurate structured Markdown table transcription and semantic summaries.
"""

import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from PIL import Image
import ollama
from docling_core.types.doc import DoclingDocument, TableItem
from config import settings

logger = logging.getLogger(__name__)


class ParsedTable(BaseModel):
    """Structured representation of an extracted financial table."""
    table_id: str = Field(description="Unique table identifier: {doc_name}_table_{idx}")
    document_name: str
    page_number: int
    image_path: Optional[str] = None
    markdown_content: str = Field(description="Structured Markdown table representation")
    summary: str = Field(description="Dense semantic summary of table contents, metrics, and entities")
    source: str = Field(description="Extraction source: 'vlm' or 'docling_native'")
    bounding_box: Optional[List[float]] = None


class TableExtractor:
    """Isolates tables, crops images, and coordinates VLM transcription."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        vlm_model: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
    ):
        self.output_dir = output_dir or settings.TABLE_IMAGE_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.vlm_model = vlm_model or settings.OLLAMA_VLM_MODEL
        self.client = ollama.Client(host=ollama_base_url or settings.OLLAMA_BASE_URL)

    def is_vlm_available(self) -> bool:
        """Check if the configured VLM model is currently available in Ollama."""
        try:
            models_response = self.client.list()
            # Handle both object and dict structures from ollama client
            models = getattr(models_response, "models", [])
            for m in models:
                name = getattr(m, "model", None) or getattr(m, "name", None) or str(m)
                if self.vlm_model in name:
                    return True
            return False
        except Exception as e:
            logger.warning(f"Could not verify VLM availability in Ollama: {e}")
            return False

    def _transcribe_with_vlm(self, image: Image.Image, table_id: str) -> Dict[str, str]:
        """Send cropped table image to Ollama VLM for structured transcription and summary."""
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        prompt = (
            "You are an expert financial analyst. Analyze this financial table image precisely.\n"
            "Task 1: Output the complete and exact data as a structured Markdown table, preserving all columns, rows, headers, and numeric values.\n"
            "Task 2: Provide a 2-3 sentence semantic summary of what financial metrics, funds, dates, and entities are reported in this table.\n\n"
            "Format your output strictly as follows:\n"
            "SUMMARY: <summary sentences>\n"
            "TABLE:\n<markdown table>"
        )

        response = self.client.chat(
            model=self.vlm_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [img_b64],
                }
            ],
        )
        content = response["message"]["content"]
        
        # Parse output format
        summary = ""
        table_md = ""
        if "TABLE:" in content:
            parts = content.split("TABLE:", 1)
            summary_part = parts[0].replace("SUMMARY:", "").strip()
            table_md = parts[1].strip()
            summary = summary_part
        else:
            table_md = content
            summary = f"Financial table data for {table_id}."

        return {"markdown": table_md, "summary": summary}

    def process_tables(
        self,
        doc: DoclingDocument,
        doc_name: str,
    ) -> List[ParsedTable]:
        """
        Extract all tables from a DoclingDocument, crop images, transcribe via VLM or fallback.
        
        Args:
            doc: Parsed DoclingDocument.
            doc_name: Name of the source PDF.
            
        Returns:
            List of ParsedTable objects.
        """
        parsed_tables: List[ParsedTable] = []
        vlm_ready = self.is_vlm_available()
        if not vlm_ready:
            logger.info(f"VLM model '{self.vlm_model}' not detected in Ollama. Using native Docling table export.")

        for idx, table in enumerate(doc.tables):
            table_id = f"{doc_name}_table_{idx}"
            page_no = 1
            bbox = None
            if table.prov and len(table.prov) > 0:
                page_no = table.prov[0].page_no
                if hasattr(table.prov[0], "bbox"):
                    bbox = [
                        table.prov[0].bbox.l,
                        table.prov[0].bbox.t,
                        table.prov[0].bbox.r,
                        table.prov[0].bbox.b,
                    ]

            # 1. Obtain table image crop
            img_path = None
            img = table.get_image(doc)
            if img:
                saved_path = self.output_dir / f"{table_id}.png"
                img.save(saved_path, format="PNG")
                img_path = str(saved_path)

            # 2. Transcribe via VLM if available, else native Docling
            if vlm_ready and img:
                try:
                    logger.info(f"Transcribing {table_id} via VLM '{self.vlm_model}'...")
                    vlm_res = self._transcribe_with_vlm(img, table_id)
                    markdown_content = vlm_res["markdown"]
                    summary = vlm_res["summary"]
                    source = "vlm"
                except Exception as e:
                    logger.warning(f"VLM transcription failed for {table_id} ({e}). Falling back to Docling export.")
                    markdown_content = table.export_to_markdown(doc=doc)
                    summary = f"Financial table on page {page_no} of {doc_name}."
                    source = "docling_native"
            else:
                markdown_content = table.export_to_markdown(doc=doc)
                summary = f"Financial table on page {page_no} of {doc_name}."
                source = "docling_native"

            parsed_tables.append(
                ParsedTable(
                    table_id=table_id,
                    document_name=doc_name,
                    page_number=page_no,
                    image_path=img_path,
                    markdown_content=markdown_content,
                    summary=summary,
                    source=source,
                    bounding_box=bbox,
                )
            )

        logger.info(f"Processed {len(parsed_tables)} tables from {doc_name}")
        return parsed_tables


# Singleton instance
table_extractor = TableExtractor()
