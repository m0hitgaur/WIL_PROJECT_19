"""
Phase 4 Verification Tests: Knowledge Graph Extraction, Tier 2 Loading, and Tier 3 Cross-References.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from database.neo4j_client import neo4j_client
from kg.extractor import kg_extractor
from kg.tier2_loader import tier2_loader
from kg.cross_reference import cross_reference_linker


def test_phase4_pipeline():
    print("\n--- Running Phase 4 Verification ---")

    # 1. Test Citation Detection & Linking (Tier 3)
    print("\n1. Testing Citation Detection Unit Logic...")
    sample_text = (
        "The fund has invested in equities as detailed in Note 4. "
        "For management fees, refer to Section 2.1 and Table 3."
    )
    detected = cross_reference_linker.detect_citations(sample_text)
    print(f"✅ Citations detected: {detected}")
    assert any("Note 4" in c for c in detected), "Note 4 was not detected!"
    assert any("Section 2.1" in c for c in detected), "Section 2.1 was not detected!"

    # 2. Run Cross-Reference Linker on loaded document
    doc_name = "AU-Vanguard_ETFs_performance_summary"
    print(f"\n2. Running Cross-Reference Linker on '{doc_name}' in Neo4j...")
    xref_res = cross_reference_linker.link_document_citations(doc_name)
    print(f"✅ Cross-reference scan finished: {xref_res['links_created']} links created.")
    if xref_res["citations"]:
        for cite in xref_res["citations"][:3]:
            print(f"   [{cite['source']}] -[:REFERENCES]-> [{cite['target']}] ({cite['citation']})")

    # 3. Test Knowledge Graph Extraction with LLM (Tier 2)
    print(f"\n3. Testing LLM Entity & Relation Extraction with '{settings.OLLAMA_LLM_MODEL}'...")
    sample_financial_chunk = (
        "Vanguard Investments Australia Ltd is the responsible entity for Vanguard Australian Shares Index ETF (VAS). "
        "For the financial year ended 30 June 2024, VAS reported a 1-Year Return of 12.1% and a Management Fee of 0.07% p.a."
    )
    extract_result = kg_extractor.extract_from_chunk(
        chunk_id="AU-Vanguard_ETFs_performance_summary_c0",
        text=sample_financial_chunk,
    )
    print(f"✅ Extracted {len(extract_result.entities)} entities and {len(extract_result.relationships)} relationships:")
    for e in extract_result.entities:
        print(f"   Entity: [{e.type.value}] {e.name}")
    for r in extract_result.relationships:
        print(f"   Relation: ({r.source_name}) -[:{r.relation.value}]-> ({r.target_name})")

    # 4. Load Extracted Knowledge Graph into Neo4j
    print("\n4. Loading Extracted Knowledge Graph into Neo4j...")
    tier2_res = tier2_loader.load_extraction_results([extract_result])
    print(f"✅ Tier 2 load complete: {tier2_res}")

    # 5. Query the Traversal in Neo4j (:Chunk -> :MENTIONS -> :Entity -> :REPORTED -> :Metric)
    print("\n5. Verifying Multi-Hop Graph Traversal in Neo4j...")
    traversal_query = """
    MATCH (c:Chunk)-[:MENTIONS]->(e)-[r]->(target)
    RETURN c.chunk_id AS chunk_id, labels(e)[0] AS source_type, e.name AS source_entity, 
           type(r) AS rel_type, labels(target)[0] AS target_type, target.name AS target_entity
    LIMIT 5
    """
    records = neo4j_client.execute_query(traversal_query)
    print(f"✅ Traversed {len(records)} knowledge graph paths:")
    for row in records:
        print(f"   [{row['chunk_id']}] -> ({row['source_type']}: {row['source_entity']}) -[:{row['rel_type']}]-> ({row['target_type']}: {row['target_entity']})")

    print("\n--- Phase 4 Verification Completed Successfully! ---\n")


if __name__ == "__main__":
    test_phase4_pipeline()
