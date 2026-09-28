"""
Unified Cypher Retrieval: Native Vector Search + Multi-Hop Graph Traversal.
Performs native vector similarity search on Neo4j chunk_embeddings, then traverses outward
along [:REFERENCES], [:NEXT], [:HAS_CHILD], and [:MENTIONS] edges to pull connected financial facts.
"""

from typing import List, Dict, Any, Optional
import logging
from pydantic import BaseModel, Field
from database.neo4j_client import neo4j_client
from database.embedder import embedder
from config import settings

logger = logging.getLogger(__name__)


class RetrievedItem(BaseModel):
    """Normalized retrieval candidate containing chunk text and traversed graph context."""
    chunk_id: str
    document_name: str
    text: str
    vector_score: float
    page_numbers: List[int] = Field(default_factory=list)
    section_header: str = ""
    is_table: bool = False
    table_id: Optional[str] = None
    traversed_graph_facts: List[str] = Field(default_factory=list)
    rerank_score: Optional[float] = None


class UnifiedCypherRetriever:
    """Executes single-round unified vector search and graph traversal in Neo4j."""

    def __init__(self, client=None, embedding_client=None):
        self.client = client or neo4j_client
        self.embedder = embedding_client or embedder

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        traverse_depth: int = 1,
    ) -> List[RetrievedItem]:
        """
        Embed query, execute vector index search, and traverse graph relationships.
        
        Args:
            query: User's condensed query string.
            top_k: Number of entry-point vector chunks to return.
            traverse_depth: Graph traversal depth (1 or 2 hops).
            
        Returns:
            List of RetrievedItem objects with vector scores and translated graph facts.
        """
        query_vec = self.embedder.embed_text(query)

        # Single Unified Cypher query:
        # 1. Vector index search on chunk_embeddings
        # 2. Graph pattern matching along REFERENCES, NEXT, MENTIONS, CONTAINS_TABLE
        cypher_query = f"""
        CALL db.index.vector.queryNodes('{settings.VECTOR_INDEX_NAME}', $top_k, $query_vec)
        YIELD node AS start_chunk, score
        
        // Optional traversal 1: Statutory cross-references (:REFERENCES)
        OPTIONAL MATCH (start_chunk)-[ref:REFERENCES]->(ref_target:Chunk)
        
        // Optional traversal 2: Mentioned Entities and relationships
        OPTIONAL MATCH (start_chunk)-[:MENTIONS]->(ent)
        OPTIONAL MATCH (ent)-[rel]->(target_ent)
        
        // Optional traversal 3: Sequential next chunk
        OPTIONAL MATCH (start_chunk)-[:NEXT]->(next_chunk:Chunk)
        
        // Optional traversal 4: Linked Table
        OPTIONAL MATCH (start_chunk)-[:CONTAINS_TABLE]->(tab:Table)

        RETURN 
            start_chunk.chunk_id AS chunk_id,
            start_chunk.document_name AS document_name,
            start_chunk.text AS text,
            start_chunk.page_numbers AS page_numbers,
            start_chunk.section_header AS section_header,
            start_chunk.is_table AS is_table,
            start_chunk.table_id AS table_id,
            score AS vector_score,
            collect(DISTINCT CASE 
                WHEN ref_target IS NOT NULL THEN 'References Note/Section in chunk [' + ref_target.chunk_id + ']'
                ELSE null END) AS ref_facts,
            collect(DISTINCT CASE 
                WHEN ent IS NOT NULL AND target_ent IS NOT NULL 
                THEN '(' + labels(ent)[0] + ': ' + ent.name + ') ' + type(rel) + ' (' + labels(target_ent)[0] + ': ' + target_ent.name + ')'
                WHEN ent IS NOT NULL 
                THEN 'Mentions ' + labels(ent)[0] + ' (' + ent.name + ')'
                ELSE null END) AS kg_facts,
            collect(DISTINCT CASE
                WHEN tab IS NOT NULL THEN 'Contains Table [' + tab.table_id + ']: ' + coalesce(tab.summary, '')
                ELSE null END) AS table_facts
        ORDER BY score DESC
        """

        records = self.client.execute_query(
            cypher_query,
            {"top_k": top_k, "query_vec": query_vec},
        )

        results: List[RetrievedItem] = []
        for r in records:
            # Combine all traversed facts into clean sentences
            facts = []
            for f in r.get("ref_facts", []):
                if f: facts.append(f)
            for f in r.get("kg_facts", []):
                if f: facts.append(f)
            for f in r.get("table_facts", []):
                if f: facts.append(f)

            results.append(
                RetrievedItem(
                    chunk_id=r["chunk_id"],
                    document_name=r.get("document_name") or "",
                    text=r["text"],
                    vector_score=float(r["vector_score"]),
                    page_numbers=r.get("page_numbers") or [],
                    section_header=r.get("section_header") or "",
                    is_table=bool(r.get("is_table", False)),
                    table_id=r.get("table_id"),
                    traversed_graph_facts=facts,
                )
            )

        logger.info(f"Retrieved {len(results)} candidate chunks for query: '{query[:50]}...'")
        return results


unified_retriever = UnifiedCypherRetriever()
