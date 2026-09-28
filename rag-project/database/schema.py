"""
Neo4j Schema and Native Vector Index Manager.
Sets up constraints, standard indexes, and native Vector Search Index on (:Chunk).
"""

import logging
from typing import Dict, Any, List
from config import settings
from database.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


class Neo4jSchemaManager:
    """Manages schema constraints and Vector Index definitions in Neo4j."""

    def __init__(self, client=None):
        self.client = client or neo4j_client

    def initialize_schema(self) -> Dict[str, Any]:
        """Create constraints and native vector index."""
        logger.info("Initializing Neo4j schema and vector indexes...")

        # 1. Unique Constraints
        constraints = [
            "CREATE CONSTRAINT unique_chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
            "CREATE CONSTRAINT unique_document_name IF NOT EXISTS FOR (d:Document) REQUIRE d.name IS UNIQUE",
            "CREATE CONSTRAINT unique_table_id IF NOT EXISTS FOR (t:Table) REQUIRE t.table_id IS UNIQUE",
            "CREATE CONSTRAINT unique_section_id IF NOT EXISTS FOR (s:Section) REQUIRE s.section_id IS UNIQUE",
        ]

        # 2. Native Vector Index
        vector_index_cypher = f"""
        CREATE VECTOR INDEX {settings.VECTOR_INDEX_NAME} IF NOT EXISTS
        FOR (c:Chunk) ON (c.embedding)
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {settings.EMBEDDING_DIM},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """

        created_constraints = []
        for c in constraints:
            try:
                self.client.execute_write(c)
                created_constraints.append(c.split("FOR")[0].strip())
            except Exception as e:
                logger.error(f"Error creating constraint: {e}")

        vector_index_created = False
        try:
            self.client.execute_write(vector_index_cypher)
            vector_index_created = True
            logger.info(f"Native Vector Index '{settings.VECTOR_INDEX_NAME}' ensured.")
        except Exception as e:
            logger.error(f"Error creating Vector Index: {e}")

        return {
            "constraints": created_constraints,
            "vector_index": vector_index_created,
            "dimensions": settings.EMBEDDING_DIM,
            "index_name": settings.VECTOR_INDEX_NAME,
        }

    def list_indexes(self) -> List[Dict[str, Any]]:
        """List all currently active indexes in Neo4j."""
        return self.client.execute_query("SHOW INDEXES YIELD name, type, entityType, properties, state")

    def reset_database(self) -> Dict[str, Any]:
        """CAUTION: Clear all nodes and relationships from the database."""
        logger.warning("Clearing entire Neo4j graph database...")
        res = self.client.execute_write("MATCH (n) DETACH DELETE n")
        return res


schema_manager = Neo4jSchemaManager()
