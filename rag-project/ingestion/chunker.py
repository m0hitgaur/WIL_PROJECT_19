"""
Hierarchical and Hybrid Document Chunker.
Splits DoclingDocuments using HybridChunker while preserving heading hierarchies,
repeating table headers, and enriching table chunks with VLM transcriptions and summaries.
"""

from typing import List, Dict, Any, Optional
import logging
from pydantic import BaseModel, Field
from docling.chunking import HybridChunker
from docling_core.types.doc import DoclingDocument
from ingestion.table_extractor import ParsedTable
from config import settings

logger = logging.getLogger(__name__)


class DocumentChunk(BaseModel):
    """Normalized chunk model ready for embedding and Neo4j Tier 1 graph insertion."""
    chunk_id: str = Field(description="Unique deterministic ID: {doc_name}_c{idx}")
    document_name: str
    chunk_index: int
    text: str
    page_numbers: List[int]
    section_headers: List[str] = Field(default_factory=list, description="Hierarchical headers breadcrumb")
    is_table: bool = False
    table_id: Optional[str] = None
    table_summary: Optional[str] = None
    prev_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None
    embedding: Optional[List[float]] = None


class FinancialChunker:
    """Manages hierarchical chunking and table enrichment."""

    def __init__(self, max_tokens: Optional[int] = None):
        self.max_tokens = max_tokens or settings.CHUNK_SIZE
        self.chunker = HybridChunker(
            max_tokens=self.max_tokens,
            repeat_table_header=True,
            always_emit_headings=True,
        )

    def chunk_document(
        self,
        doc: DoclingDocument,
        doc_name: str,
        parsed_tables: Optional[List[ParsedTable]] = None,
    ) -> List[DocumentChunk]:
        """
        Generate structured chunks from a DoclingDocument.
        
        Args:
            doc: Parsed DoclingDocument.
            doc_name: Source document name.
            parsed_tables: Optional extracted & VLM-transcribed tables to enrich table chunks.
            
        Returns:
            List of DocumentChunk instances with sequential IDs and breadcrumbs.
        """
        # Map table_id to parsed table info for fast enrichment lookup
        table_map: Dict[int, ParsedTable] = {}
        if parsed_tables:
            for p_tab in parsed_tables:
                # docling table IDs typically match table index
                try:
                    t_idx = int(p_tab.table_id.split("_table_")[-1])
                    table_map[t_idx] = p_tab
                except ValueError:
                    pass

        raw_chunks = list(self.chunker.chunk(doc))
        document_chunks: List[DocumentChunk] = []

        logger.info(f"Generated {len(raw_chunks)} raw hybrid chunks from {doc_name}")

        for idx, rc in enumerate(raw_chunks):
            chunk_id = f"{doc_name}_c{idx}"
            text = rc.text

            # Extract headings breadcrumb
            headings = []
            if hasattr(rc, "meta") and hasattr(rc.meta, "headings") and rc.meta.headings:
                headings = [h.strip() for h in rc.meta.headings if h]

            # Extract page numbers from provenance
            page_numbers: List[int] = []
            is_table = False
            matched_table: Optional[ParsedTable] = None

            if hasattr(rc, "meta") and hasattr(rc.meta, "doc_items"):
                for item in rc.meta.doc_items:
                    if hasattr(item, "prov"):
                        for prov in item.prov:
                            if hasattr(prov, "page_no") and prov.page_no not in page_numbers:
                                page_numbers.append(prov.page_no)
                    
                    # Detect if chunk item is a table
                    label = getattr(item, "label", None) or getattr(item, "type", "")
                    if "table" in str(label).lower() or item.__class__.__name__ == "TableItem":
                        is_table = True

            if not page_numbers:
                page_numbers = [1]

            # If this is a table chunk and we have VLM transcriptions, enrich it
            table_id = None
            table_summary = None
            if is_table and parsed_tables:
                # Match to corresponding table by page or proximity
                for pt in parsed_tables:
                    if pt.page_number in page_numbers:
                        matched_table = pt
                        table_id = pt.table_id
                        table_summary = pt.summary
                        # Prepend the semantic table summary to the chunk text for dense semantic retrieval
                        if pt.summary and pt.summary not in text:
                            text = f"[Table Context: {pt.summary}]\n\n{text}"
                        break

            document_chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_name=doc_name,
                    chunk_index=idx,
                    text=text,
                    page_numbers=page_numbers,
                    section_headers=headings,
                    is_table=is_table,
                    table_id=table_id,
                    table_summary=table_summary,
                )
            )

        # Set sequential relationships: prev_chunk_id and next_chunk_id
        for i in range(len(document_chunks)):
            if i > 0:
                document_chunks[i].prev_chunk_id = document_chunks[i - 1].chunk_id
            if i < len(document_chunks) - 1:
                document_chunks[i].next_chunk_id = document_chunks[i + 1].chunk_id

        return document_chunks


# Singleton instance
financial_chunker = FinancialChunker()
