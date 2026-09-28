"""
Ontology Schemas for Financial Knowledge Graph Extraction.
Defines strict node types, relationship types, and Pydantic validation models.
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    COMPANY = "Company"
    FUND = "Fund"
    SUBSIDIARY = "Subsidiary"
    FINANCIAL_METRIC = "Financial_Metric"
    TABLE = "Table"


class RelationType(str, Enum):
    OWNS = "OWNS"
    REPORTED = "REPORTED"
    CONTAINS_METRIC = "CONTAINS_METRIC"
    HAS_HOLDING = "HAS_HOLDING"
    REFERENCES = "REFERENCES"


class ExtractedEntity(BaseModel):
    """An entity extracted from financial text."""
    name: str = Field(description="Normalized name of the entity, e.g. 'Vanguard Australian Shares Index ETF'")
    type: EntityType = Field(description="Strict entity category")
    description: Optional[str] = Field(default=None, description="Brief description or context")


class ExtractedRelation(BaseModel):
    """A semantic relationship between two entities."""
    source_name: str = Field(description="Source entity name")
    source_type: EntityType
    relation: RelationType = Field(description="Strict relationship type")
    target_name: str = Field(description="Target entity name")
    target_type: EntityType
    context: Optional[str] = Field(default=None, description="Supporting sentence or numeric value")


class GraphExtractionResult(BaseModel):
    """The complete extraction result for a text chunk."""
    chunk_id: str
    entities: List[ExtractedEntity] = Field(default_factory=list)
    relationships: List[ExtractedRelation] = Field(default_factory=list)
