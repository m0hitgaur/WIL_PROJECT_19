"""
Knowledge Graph Extractor using LLM.
Extracts financial entities and relationships from chunks according to a strict ontology.
"""

import json
import logging
from typing import Optional, List
import ollama
from config import settings
from kg.schema import EntityType, RelationType, ExtractedEntity, ExtractedRelation, GraphExtractionResult

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT = """You are a financial knowledge graph extraction assistant.
Extract entities and relationships from the provided financial text strictly following this ontology.

Allowed Entity Types:
- Company (e.g. "Vanguard Investments Australia Ltd", "BHP Group")
- Fund (e.g. "Vanguard Australian Shares Index ETF", "VAS", "Vanguard Diversified Balanced Fund")
- Subsidiary (e.g. "Vanguard Group Inc", "Responsible Entity")
- Financial_Metric (e.g. "Management Fee", "1-Year Return", "Net Asset Value", "Distribution Yield", "AUM")
- Table (e.g. "Performance Summary Table", "Fee Schedule")

Allowed Relationship Types:
- OWNS (e.g. Company OWNS Subsidiary)
- REPORTED (e.g. Fund REPORTED Financial_Metric)
- CONTAINS_METRIC (e.g. Table CONTAINS_METRIC Financial_Metric)
- HAS_HOLDING (e.g. Fund HAS_HOLDING Company)

Output MUST be a valid JSON object matching this schema:
{
  "entities": [
    {"name": "<entity name>", "type": "Company | Fund | Subsidiary | Financial_Metric | Table", "description": "<optional context>"}
  ],
  "relationships": [
    {
      "source_name": "<source entity>",
      "source_type": "<source type>",
      "relation": "OWNS | REPORTED | CONTAINS_METRIC | HAS_HOLDING",
      "target_name": "<target entity>",
      "target_type": "<target type>",
      "context": "<value or excerpt>"
    }
  ]
}

Text to extract:
"""


class KnowledgeGraphExtractor:
    """Extracts ontology-conforming entities and relationships from financial text."""

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model or settings.OLLAMA_LLM_MODEL
        self.client = ollama.Client(host=base_url or settings.OLLAMA_BASE_URL)

    def extract_from_chunk(self, chunk_id: str, text: str) -> GraphExtractionResult:
        """
        Extract entities and relationships from a single chunk of financial text.
        
        Args:
            chunk_id: Unique chunk identifier.
            text: Text content of the chunk.
            
        Returns:
            GraphExtractionResult with validated entities and relations.
        """
        if not text.strip():
            return GraphExtractionResult(chunk_id=chunk_id)

        prompt = EXTRACTION_PROMPT + f"\n\"\"\"\n{text}\n\"\"\"\n"

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                format="json",
                options={"temperature": 0.0},
            )
            raw_json = response["message"]["content"]
            parsed_data = json.loads(raw_json)

            # Validate entities
            valid_entities: List[ExtractedEntity] = []
            for item in parsed_data.get("entities", []):
                try:
                    e_type = EntityType(item.get("type"))
                    e_name = item.get("name", "").strip()
                    if e_name:
                        valid_entities.append(
                            ExtractedEntity(
                                name=e_name,
                                type=e_type,
                                description=item.get("description"),
                            )
                        )
                except ValueError:
                    continue

            # Validate relationships
            valid_relationships: List[ExtractedRelation] = []
            for item in parsed_data.get("relationships", []):
                try:
                    r_type = RelationType(item.get("relation"))
                    s_type = EntityType(item.get("source_type"))
                    t_type = EntityType(item.get("target_type"))
                    s_name = item.get("source_name", "").strip()
                    t_name = item.get("target_name", "").strip()
                    if s_name and t_name:
                        valid_relationships.append(
                            ExtractedRelation(
                                source_name=s_name,
                                source_type=s_type,
                                relation=r_type,
                                target_name=t_name,
                                target_type=t_type,
                                context=item.get("context"),
                            )
                        )
                except ValueError:
                    continue

            return GraphExtractionResult(
                chunk_id=chunk_id,
                entities=valid_entities,
                relationships=valid_relationships,
            )

        except Exception as e:
            logger.warning(f"Entity extraction failed for {chunk_id}: {e}")
            return GraphExtractionResult(chunk_id=chunk_id)


# Singleton instance
kg_extractor = KnowledgeGraphExtractor()
