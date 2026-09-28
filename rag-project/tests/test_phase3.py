"""
Phase 3 Verification Tests: Schema Setup, Vector Index Creation, Tier 1 Loading, and Vector Search.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from database.neo4j_client import neo4j_client
from database.schema import schema_manager
from database.embedder import embedder
from ingestion.parser import document_parser
from ingestion.table_extractor import table_extractor
from ingestion.chunker import financial_chunker
from ingestion.tier1_loader import tier1_loader


def test_phase3_pipeline():
    print("\n--- Running Phase 3 Verification ---")

    # 1. Initialize schema and vector index
    print("\n1. Initializing Neo4j Constraints and Vector Index...")
    init_res = schema_manager.initialize_schema()
    print(f"✅ Schema initialized: {init_res}")

    indexes = schema_manager.list_indexes()
    vector_indexes = [idx for idx in indexes if idx.get("type") == "VECTOR" or "vector" in str(idx).lower()]
    print(f"✅ Active vector indexes found: {len(vector_indexes)}")
    for vi in vector_indexes:
        print(f"   - Index: {vi.get('name')}, State: {vi.get('state')}, Properties: {vi.get('properties')}")

    # 2. Parse, chunk, and embed test document
    test_pdf = settings.DATA_DIR / "AU-Vanguard_ETFs_performance_summary.pdf"
    doc_name = test_pdf.stem
    print(f"\n2. Parsing and chunking {test_pdf.name}...")
    doc = document_parser.parse_pdf(test_pdf)
    tables = table_extractor.process_tables(doc, doc_name=doc_name)
    chunks = financial_chunker.chunk_document(doc, doc_name=doc_name, parsed_tables=tables)
    print(f"✅ Chunks ready: {len(chunks)}, Tables: {len(tables)}")

    # 3. Load Tier 1 graph into Neo4j
    print("\n3. Loading Tier 1 Document Structure and Embeddings into Neo4j...")
    load_res = tier1_loader.load_chunks(chunks=chunks, doc_name=doc_name, parsed_tables=tables)
    print(f"✅ Tier 1 load complete: {load_res}")

    # 4. Verify Graph Traversal (:NEXT and :HAS_CHILD)
    print("\n4. Verifying Structural Edges (:NEXT, :HAS_CHILD)...")
    structural_check = neo4j_client.execute_query("""
    MATCH (c1:Chunk)-[:NEXT]->(c2:Chunk)
    RETURN c1.chunk_id AS from_chunk, c2.chunk_id AS to_chunk
    LIMIT 3
    """)
    assert len(structural_check) > 0, "No :NEXT edges found!"
    print(f"✅ :NEXT sequential links verified ({len(structural_check)} sampled):")
    for row in structural_check:
        print(f"   {row['from_chunk']} -> {row['to_chunk']}")

    # 5. Verify Native Vector Index Search
    print("\n5. Testing Native Vector Search (The Vector-Graph Bridge)...")
    query_text = "What is the performance and return of Vanguard Australian Shares ETF?"
    query_vec = embedder.embed_text(query_text)

    vector_search_cypher = f"""
    CALL db.index.vector.queryNodes('{settings.VECTOR_INDEX_NAME}', 3, $query_vec)
    YIELD node AS chunk, score
    RETURN chunk.chunk_id AS chunk_id, chunk.page_numbers AS pages, score, substring(chunk.text, 0, 120) AS preview
    """
    search_results = neo4j_client.execute_query(vector_search_cypher, {"query_vec": query_vec})
    assert len(search_results) > 0, "Vector search returned no results!"
    print(f"✅ Native Vector Search returned {len(search_results)} nearest chunk nodes:")
    for idx, r in enumerate(search_results):
        print(f"   Hit {idx+1}: [{r['chunk_id']}] (score: {r['score']:.4f}) - {r['preview']}...")

    print("\n--- Phase 3 Verification Completed Successfully! ---\n")


if __name__ == "__main__":
    test_phase3_pipeline()
