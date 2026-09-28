"""
Re-ranker for Retrieved Candidate Pooling.
Scores retrieved chunks (initial vector hits + traversed graph context)
against the condensed query, filtering down to the top 3-4 most relevant chunks.
"""

from typing import List, Optional
import logging
from retrieval.unified_cypher import RetrievedItem

logger = logging.getLogger(__name__)


class CrossReranker:
    """Re-ranks retrieved items by combining vector score, graph topological connectivity, and semantic relevance."""

    def __init__(self, top_n: int = 4):
        self.top_n = top_n

    def rerank(
        self,
        query: str,
        candidates: List[RetrievedItem],
        top_n: Optional[int] = None,
    ) -> List[RetrievedItem]:
        """
        Re-score and filter candidate items.
        
        Args:
            query: The user's condensed query.
            candidates: Retrieved items from UnifiedCypherRetriever.
            top_n: Number of items to keep (defaults to self.top_n).
            
        Returns:
            Top-N re-ranked items.
        """
        if not candidates:
            return []

        limit = top_n or self.top_n
        query_words = set(query.lower().split())

        for item in candidates:
            # Base score from vector similarity (0.0 to 1.0)
            score = item.vector_score * 0.70

            # Graph topology bonus: reward chunks that have verified statutory citations or entity relations
            if item.traversed_graph_facts:
                score += min(len(item.traversed_graph_facts) * 0.05, 0.15)

            # Lexical keyword match bonus in text and headers
            combined_text = f"{item.section_header} {item.text}".lower()
            keyword_matches = sum(1 for w in query_words if len(w) > 3 and w in combined_text)
            score += min(keyword_matches * 0.03, 0.15)

            item.rerank_score = round(score, 4)

        # Sort descending by rerank_score
        reranked = sorted(candidates, key=lambda x: x.rerank_score or 0.0, reverse=True)
        return reranked[:limit]


reranker = CrossReranker()
