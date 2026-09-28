"""
Tier 2 Knowledge Graph Loader.
Loads extracted ontology entities and semantic relationships into Neo4j
and links them back to their origin (:Chunk) nodes via [:MENTIONS].
"""

from typing import List, Dict, Any
import logging
from database.neo4j_client import neo4j_client
from kg.schema import GraphExtractionResult

logger = logging.getLogger(__name__)


class Tier2Loader:
    """Writes extracted entities and relationships to Neo4j."""

    def __init__(self, client=None):
        self.client = client or neo4j_client

    def load_extraction_results(
        self,
        results: List[GraphExtractionResult],
    ) -> Dict[str, Any]:
        """
        Persist extracted entities, relationships, and chunk mention links to Neo4j.
        
        Args:
            results: List of GraphExtractionResult objects.
            
        Returns:
            Dictionary with counts of loaded nodes and edges.
        """
        total_entities = 0
        total_relationships = 0
        total_mentions = 0

        for res in results:
            if not res.entities and not res.relationships:
                continue

            # 1. Upsert Entities and link [:MENTIONS] from Chunk
            for ent in res.entities:
                label = ent.type.value
                cypher_entity = f"""
                MATCH (c:Chunk {{chunk_id: $chunk_id}})
                MERGE (e:`{label}` {{name: $name}})
                ON CREATE SET e.created_at = datetime(), e.description = $description
                MERGE (c)-[:MENTIONS]->(e)
                """
                self.client.execute_write(
                    cypher_entity,
                    {
                        "chunk_id": res.chunk_id,
                        "name": ent.name,
                        "description": ent.description or "",
                    },
                )
                total_entities += 1
                total_mentions += 1

            # 2. Upsert Semantic Relationships between Entities
            for rel in res.relationships:
                s_label = rel.source_type.value
                t_label = rel.target_type.value
                r_type = rel.relation.value

                cypher_rel = f"""
                MERGE (s:`{s_label}` {{name: $s_name}})
                MERGE (t:`{t_label}` {{name: $t_name}})
                MERGE (s)-[r:`{r_type}`]->(t)
                SET r.context = $context, r.updated_at = datetime()
                """
                self.client.execute_write(
                    cypher_rel,
                    {
                        "s_name": rel.source_name,
                        "t_name": rel.target_name,
                        "context": rel.context or "",
                    },
                )
                total_relationships += 1

        logger.info(
            f"Tier 2 Load complete: {total_entities} entities upserted, "
            f"{total_relationships} relations created, {total_mentions} chunk mentions linked."
        )

        return {
            "entities_processed": total_entities,
            "relationships_created": total_relationships,
            "chunk_mentions_linked": total_mentions,
        }


tier2_loader = Tier2Loader()
