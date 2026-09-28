"""
Tier 1 Graph Loader: Document Structure and Native Vector Indexing.
Loads DocumentChunks, embeds them with Qwen3-Embedding, and writes (:Document), (:Section),
(:Chunk), and (:Table) nodes along with [:HAS_SECTION], [:HAS_CHILD], and [:NEXT] edges into Neo4j.
"""

from typing import List, Dict, Any, Optional
import logging
from config import settings
from database.neo4j_client import neo4j_client
from database.embedder import embedder
from ingestion.chunker import DocumentChunk
from ingestion.table_extractor import ParsedTable

logger = logging.getLogger(__name__)


class Tier1Loader:
    """Loads document hierarchy and embedded chunks into Neo4j."""

    def __init__(self, client=None, embedding_client=None):
        self.client = client or neo4j_client
        self.embedder = embedding_client or embedder

    def load_chunks(
        self,
        chunks: List[DocumentChunk],
        doc_name: str,
        parsed_tables: Optional[List[ParsedTable]] = None,
    ) -> Dict[str, Any]:
        """
        Embed and write chunks, sections, tables, and structural edges into Neo4j.
        
        Args:
            chunks: List of DocumentChunk instances.
            doc_name: Document name.
            parsed_tables: Optional list of ParsedTable instances.
            
        Returns:
            Dictionary with creation metrics and status.
        """
        if not chunks:
            logger.warning("No chunks provided to Tier1Loader.")
            return {"status": "empty", "chunks_loaded": 0}

        logger.info(f"Generating embeddings for {len(chunks)} chunks in {doc_name}...")
        texts_to_embed = [c.text for c in chunks]
        embeddings = self.embedder.embed_batch(texts_to_embed)

        for c, emb in zip(chunks, embeddings):
            c.embedding = emb

        logger.info(f"Persisting Tier 1 nodes and edges to Neo4j for {doc_name}...")

        # 1. Ensure Document root node
        self.client.execute_write(
            "MERGE (d:Document {name: $doc_name}) ON CREATE SET d.created_at = datetime()",
            {"doc_name": doc_name},
        )

        # 2. Insert or Merge Chunks with their native embeddings
        chunk_params = []
        for c in chunks:
            primary_header = c.section_headers[-1] if c.section_headers else "General"
            section_id = f"{doc_name}_{primary_header}".replace(" ", "_")
            chunk_params.append({
                "chunk_id": c.chunk_id,
                "document_name": c.document_name,
                "chunk_index": c.chunk_index,
                "text": c.text,
                "page_numbers": c.page_numbers,
                "section_header": primary_header,
                "section_id": section_id,
                "is_table": c.is_table,
                "table_id": c.table_id or "",
                "table_summary": c.table_summary or "",
                "embedding": c.embedding,
                "next_chunk_id": c.next_chunk_id or "",
            })

        # Bulk upsert chunks
        cypher_upsert_chunks = """
        UNWIND $chunks AS cp
        MERGE (c:Chunk {chunk_id: cp.chunk_id})
        SET c.document_name = cp.document_name,
            c.chunk_index = cp.chunk_index,
            c.text = cp.text,
            c.page_numbers = cp.page_numbers,
            c.section_header = cp.section_header,
            c.is_table = cp.is_table,
            c.table_id = cp.table_id,
            c.table_summary = cp.table_summary,
            c.embedding = cp.embedding
        
        // Link to parent Document
        WITH c, cp
        MATCH (d:Document {name: cp.document_name})
        MERGE (d)-[:HAS_CHUNK]->(c)

        // Merge Section and link
        MERGE (s:Section {section_id: cp.section_id})
        ON CREATE SET s.title = cp.section_header, s.document_name = cp.document_name
        MERGE (d)-[:HAS_SECTION]->(s)
        MERGE (s)-[:HAS_CHILD]->(c)
        """
        summary_chunks = self.client.execute_write(cypher_upsert_chunks, {"chunks": chunk_params})

        # 3. Create [:NEXT] sequential relationships between chunks
        cypher_next_links = """
        UNWIND $chunks AS cp
        WITH cp WHERE cp.next_chunk_id <> ''
        MATCH (curr:Chunk {chunk_id: cp.chunk_id})
        MATCH (nxt:Chunk {chunk_id: cp.next_chunk_id})
        MERGE (curr)-[:NEXT]->(nxt)
        """
        summary_next = self.client.execute_write(cypher_next_links, {"chunks": chunk_params})

        # 4. Insert Table nodes if present
        table_count = 0
        if parsed_tables:
            table_params = []
            for t in parsed_tables:
                table_params.append({
                    "table_id": t.table_id,
                    "document_name": t.document_name,
                    "page_number": t.page_number,
                    "markdown_content": t.markdown_content,
                    "summary": t.summary,
                    "source": t.source,
                    "image_path": t.image_path or "",
                })

            cypher_upsert_tables = """
            UNWIND $tables AS tp
            MERGE (t:Table {table_id: tp.table_id})
            SET t.document_name = tp.document_name,
                t.page_number = tp.page_number,
                t.markdown_content = tp.markdown_content,
                t.summary = tp.summary,
                t.source = tp.source,
                t.image_path = tp.image_path

            // Link Table to Chunk that contains it
            WITH t, tp
            MATCH (c:Chunk {chunk_id: tp.document_name + '_table_' + split(tp.table_id, '_table_')[1]})
            MERGE (c)-[:CONTAINS_TABLE]->(t)
            """
            self.client.execute_write(cypher_upsert_tables, {"tables": table_params})
            table_count = len(parsed_tables)

        logger.info(f"Successfully loaded {len(chunks)} chunks and {table_count} tables into Neo4j for {doc_name}")
        return {
            "status": "success",
            "document": doc_name,
            "chunks_loaded": len(chunks),
            "tables_loaded": table_count,
            "nodes_created": summary_chunks["nodes_created"],
            "relationships_created": summary_chunks["relationships_created"] + summary_next["relationships_created"],
        }


tier1_loader = Tier1Loader()
