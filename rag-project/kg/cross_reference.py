"""
Tier 3 Graph Enrichment: Two-Pass Cross-Reference Linker.
Detects statutory internal citations (e.g., "Note 4", "refer to Note 2", "Section 3.1"),
resolves the referenced destination chunks via header matching or vector search,
and writes deterministic [:REFERENCES] edges into Neo4j.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from database.neo4j_client import neo4j_client
from database.embedder import embedder
from config import settings

logger = logging.getLogger(__name__)


# Citation regex patterns
CITATION_PATTERNS = [
    re.compile(r"(?:refer\s+to\s+|see\s+|detailed\s+in\s+|as\s+set\s+out\s+in\s+|in\s+)?(Note\s+\d+[a-zA-Z]?)", re.IGNORECASE),
    re.compile(r"(?:refer\s+to\s+|see\s+)?(Section\s+\d+(?:\.\d+)*)", re.IGNORECASE),
    re.compile(r"(?:refer\s+to\s+|see\s+)?(Table\s+\d+)", re.IGNORECASE),
]


class CrossReferenceLinker:
    """Detects internal citations and connects chunks via [:REFERENCES] edges."""

    def __init__(self, client=None, embedding_client=None):
        self.client = client or neo4j_client
        self.embedder = embedding_client or embedder

    def detect_citations(self, text: str) -> List[str]:
        """Extract explicit citation targets from text using regex patterns."""
        citations = set()
        for pattern in CITATION_PATTERNS:
            matches = pattern.findall(text)
            for m in matches:
                clean_cite = m.strip()
                # Normalize "note 4" -> "Note 4"
                parts = clean_cite.split()
                if len(parts) == 2:
                    normalized = f"{parts[0].capitalize()} {parts[1]}"
                    citations.add(normalized)
                else:
                    citations.add(clean_cite)
        return list(citations)

    def find_target_chunk(
        self,
        citation: str,
        document_name: str,
    ) -> Optional[str]:
        """
        Locate the destination chunk corresponding to an internal citation.
        First tries exact/substring match on Section or Chunk text within the same document,
        then falls back to vector similarity search.
        """
        # Pass 2A: Search by Section header or text prefix within the document
        cypher_exact = """
        MATCH (c:Chunk {document_name: $document_name})
        WHERE c.section_header CONTAINS $citation
           OR c.text STARTS WITH $citation
           OR c.text CONTAINS ('# ' + $citation)
           OR c.text CONTAINS ('## ' + $citation)
        RETURN c.chunk_id AS chunk_id
        ORDER BY c.chunk_index ASC
        LIMIT 1
        """
        records = self.client.execute_query(
            cypher_exact,
            {"document_name": document_name, "citation": citation},
        )
        if records and records[0].get("chunk_id"):
            return records[0]["chunk_id"]

        # Pass 2B: Fallback to vector search for the citation query
        try:
            query_vec = self.embedder.embed_text(f"{document_name} {citation}")
            cypher_vector = f"""
            CALL db.index.vector.queryNodes('{settings.VECTOR_INDEX_NAME}', 1, $query_vec)
            YIELD node AS c, score
            WHERE c.document_name = $document_name AND score > 0.75
            RETURN c.chunk_id AS chunk_id
            """
            v_records = self.client.execute_query(
                cypher_vector,
                {"document_name": document_name, "query_vec": query_vec},
            )
            if v_records and v_records[0].get("chunk_id"):
                return v_records[0]["chunk_id"]
        except Exception as e:
            logger.debug(f"Vector lookup failed for citation '{citation}': {e}")

        return None

    def link_document_citations(self, document_name: str) -> Dict[str, Any]:
        """
        Scan all chunks for a document, resolve citations, and create [:REFERENCES] edges.
        
        Args:
            document_name: Name of the document in Neo4j.
            
        Returns:
            Summary of detected citations and created links.
        """
        logger.info(f"Scanning document '{document_name}' for internal citations...")

        # Fetch all chunks for this document
        cypher_get_chunks = """
        MATCH (c:Chunk {document_name: $document_name})
        RETURN c.chunk_id AS chunk_id, c.text AS text
        """
        chunks = self.client.execute_query(cypher_get_chunks, {"document_name": document_name})
        
        links_created = 0
        citation_details: List[Dict[str, str]] = []

        for row in chunks:
            chunk_id = row["chunk_id"]
            text = row["text"]
            citations = self.detect_citations(text)

            for citation in citations:
                target_id = self.find_target_chunk(citation, document_name)
                if target_id and target_id != chunk_id:
                    # Create [:REFERENCES] edge
                    cypher_link = """
                    MATCH (src:Chunk {chunk_id: $src_id})
                    MATCH (tgt:Chunk {chunk_id: $tgt_id})
                    MERGE (src)-[r:REFERENCES {citation: $citation}]->(tgt)
                    ON CREATE SET r.created_at = datetime()
                    """
                    self.client.execute_write(
                        cypher_link,
                        {"src_id": chunk_id, "tgt_id": target_id, "citation": citation},
                    )
                    links_created += 1
                    citation_details.append({
                        "source": chunk_id,
                        "target": target_id,
                        "citation": citation,
                    })

        logger.info(f"Created {links_created} [:REFERENCES] edges for {document_name}.")
        return {
            "document": document_name,
            "total_chunks_scanned": len(chunks),
            "links_created": links_created,
            "citations": citation_details,
        }


cross_reference_linker = CrossReferenceLinker()
