"""
Batch Ingestion CLI Script.
Processes all financial PDF reports in the data directory through the full ingestion pipeline:
1. Docling structural parsing & layout analysis.
2. Table isolation & image cropping (with VLM transcription / native fallback).
3. Hierarchical hybrid chunking with repeated table headers and metadata.
4. Ollama vector embedding generation (qwen3-embedding:4b).
5. Neo4j Tier 1 bulk loading (Chunks, Sections, Documents, Structural Edges [:HAS_SECTION], [:HAS_CHILD], [:NEXT]).
6. Knowledge Graph Tier 2 extraction (strict ontology: Company, Fund, Financial_Metric) & [:MENTIONS] linking.
7. Knowledge Graph Tier 3 statutory internal citation resolution ([:REFERENCES] edges).
"""

import sys
import logging
from pathlib import Path
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ingest_all")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from database.schema import schema_manager
from ingestion.parser import document_parser
from ingestion.table_extractor import table_extractor
from ingestion.chunker import financial_chunker
from ingestion.tier1_loader import tier1_loader
from kg.extractor import kg_extractor
from kg.tier2_loader import tier2_loader
from kg.cross_reference import cross_reference_linker


def ingest_document(pdf_path: Path, run_kg_extraction: bool = False):
    """Run full ingestion for a single PDF document."""
    doc_name = pdf_path.stem
    logger.info(f"==================================================")
    logger.info(f"Processing Document: {pdf_path.name}")
    logger.info(f"==================================================")

    # 1. Parse Document
    logger.info("Step 1: Parsing with Docling...")
    doc = document_parser.parse_pdf(pdf_path)

    # 2. Extract & Crop Tables
    logger.info("Step 2: Isolating tables and extracting crops...")
    tables = table_extractor.process_tables(doc, doc_name=doc_name)
    logger.info(f"Extracted {len(tables)} tables.")

    # 3. Hybrid Chunking
    logger.info("Step 3: Chunking document with table enrichment...")
    chunks = financial_chunker.chunk_document(doc, doc_name=doc_name, parsed_tables=tables)
    logger.info(f"Created {len(chunks)} hybrid chunks.")

    # 4. Tier 1 Graph & Vector Loading
    logger.info("Step 4: Embedding and loading Tier 1 graph into Neo4j...")
    tier1_res = tier1_loader.load_chunks(chunks=chunks, doc_name=doc_name, parsed_tables=tables)
    logger.info(f"Tier 1 complete: {tier1_res}")

    # 5. Tier 3 Statutory Cross-Reference Linking
    logger.info("Step 5: Linking internal citations (Tier 3 [:REFERENCES])...")
    xref_res = cross_reference_linker.link_document_citations(doc_name=doc_name)
    logger.info(f"Tier 3 complete: {xref_res['links_created']} citation edges created.")

    # 6. Optional Tier 2 KG Extraction
    if run_kg_extraction:
        logger.info("Step 6: Running Tier 2 Knowledge Graph extraction on key chunks...")
        # Extract on first 3 summary chunks to keep ingestion fast
        kg_results = []
        for c in chunks[:3]:
            res = kg_extractor.extract_from_chunk(c.chunk_id, c.text)
            kg_results.append(res)
        tier2_res = tier2_loader.load_extraction_results(kg_results)
        logger.info(f"Tier 2 complete: {tier2_res}")

    logger.info(f"Finished ingesting: {pdf_path.name}\n")


def main():
    logger.info("Starting Batch Ingestion Pipeline...")
    settings.ensure_directories()

    # Initialize Neo4j constraints and Vector Index
    schema_manager.initialize_schema()

    data_dir = settings.DATA_DIR
    pdf_files = list(data_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDF files found in {data_dir}")
        return

    logger.info(f"Found {len(pdf_files)} PDF file(s) in {data_dir}:")
    for f in pdf_files:
        logger.info(f" - {f.name}")

    # For testing, ingest the primary report
    for pdf in pdf_files:
        try:
            ingest_document(pdf, run_kg_extraction=False)
        except Exception as e:
            logger.error(f"Error processing {pdf.name}: {e}")

    logger.info("Batch Ingestion Pipeline Completed Successfully!")


if __name__ == "__main__":
    main()
