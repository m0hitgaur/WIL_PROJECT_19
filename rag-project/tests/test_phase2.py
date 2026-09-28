"""
Phase 2 Verification Tests: Document Parsing, Table Extraction/Cropping, and Hybrid Chunking.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from ingestion.parser import DocumentParser
from ingestion.table_extractor import TableExtractor
from ingestion.chunker import FinancialChunker


def test_parsing_and_chunking():
    test_pdf = settings.DATA_DIR / "AU-Vanguard_ETFs_performance_summary.pdf"
    assert test_pdf.exists(), f"Test PDF does not exist at {test_pdf}"

    print(f"\n1. Parsing PDF: {test_pdf.name}...")
    parser = DocumentParser(generate_table_images=True)
    doc = parser.parse_pdf(test_pdf)
    assert doc is not None
    print(f"✅ Docling parsed document successfully. Tables detected: {len(doc.tables)}")

    print("\n2. Extracting Tables and Cropping Images...")
    extractor = TableExtractor()
    parsed_tables = extractor.process_tables(doc, doc_name=test_pdf.stem)
    print(f"✅ Extracted {len(parsed_tables)} tables.")
    for t in parsed_tables:
        print(f"   - {t.table_id} (Page {t.page_number}): image={t.image_path}, source={t.source}")
        if t.image_path:
            assert Path(t.image_path).exists(), f"Image file not found: {t.image_path}"

    print("\n3. Chunking Document with Table Enrichment...")
    chunker = FinancialChunker()
    chunks = chunker.chunk_document(doc, doc_name=test_pdf.stem, parsed_tables=parsed_tables)
    assert len(chunks) > 0, "No chunks generated!"
    print(f"✅ Generated {len(chunks)} chunks.")

    # Validate chunk properties
    first_chunk = chunks[0]
    last_chunk = chunks[-1]
    assert first_chunk.prev_chunk_id is None
    assert first_chunk.next_chunk_id is not None
    assert last_chunk.next_chunk_id is None
    print(f"✅ Verified sequential chunk linkage ({first_chunk.chunk_id} -> {first_chunk.next_chunk_id}).")

    table_chunks = [c for c in chunks if c.is_table]
    print(f"✅ Table chunks detected: {len(table_chunks)}")
    if table_chunks:
        print(f"   Sample table chunk ID: {table_chunks[0].chunk_id}")
        if table_chunks[0].table_summary:
            print(f"   Table summary snippet: {table_chunks[0].table_summary[:120]}...")

    print("\n--- Phase 2 Verification Completed Successfully! ---\n")


if __name__ == "__main__":
    test_parsing_and_chunking()
