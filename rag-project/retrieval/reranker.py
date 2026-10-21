"""
Re-ranker for Retrieved Candidate Pooling.
Uses TypeSafe AI's Jev ("System 1" model) with the Score primitive to rank candidate chunks
along an ordered relevance rubric. Falls back to hybrid vector-graph heuristics if offline.
"""

from typing import List, Optional
import logging
from config import settings
from retrieval.unified_cypher import RetrievedItem

logger = logging.getLogger(__name__)

RELEVANCE_LEVELS = ["irrelevant", "partially_relevant", "relevant", "exact_answer"]


class CrossReranker:
    """Re-ranks retrieved items using Jev Score primitive or fallback heuristics."""

    def __init__(self, top_n: int = 2):
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

        # Attempt Jev System 1 Score primitive if API key is configured
        if settings.TYPESAFE_API_KEY:
            try:
                from typesafe_sdk import TypeSafeClient, Score

                client_kwargs = {"api_key": settings.TYPESAFE_API_KEY}
                if settings.TYPESAFE_MODEL:
                    client_kwargs["model"] = settings.TYPESAFE_MODEL

                # Pack candidates into state
                jev_state = {
                    "user_query": query,
                }
                questions = {}
                for i, c in enumerate(candidates):
                    # Truncate text to 600 chars to conserve input tokens
                    jev_state[f"chunk_{i}"] = (
                        f"Doc: {c.document_name} | Header: {c.section_header}\n"
                        f"Content: {c.text[:600]}"
                    )
                    questions[f"relevance_{i}"] = Score(
                        instructions=f"How directly does chunk_{i} contain information to answer the user query?",
                        criteria=RELEVANCE_LEVELS,
                    )

                with TypeSafeClient(**client_kwargs) as client:
                    response = client.system_one(state=jev_state, questions=questions)

                for i, c in enumerate(candidates):
                    ans = response.answers.get(f"relevance_{i}")
                    if ans:
                        # Normalize score (0.0 to 3.0 scale normalized to 0.0-1.0)
                        raw_score = float(ans.score)
                        normalized_score = round(raw_score / (len(RELEVANCE_LEVELS) - 1), 4)
                        # Blend 70% Jev score + 30% vector score
                        c.rerank_score = round((normalized_score * 0.70) + (c.vector_score * 0.30), 4)
                    else:
                        c.rerank_score = c.vector_score

                reranked = sorted(candidates, key=lambda x: x.rerank_score or 0.0, reverse=True)
                logger.info(
                    f"[Jev Reranker] Evaluated {len(candidates)} candidates. "
                    f"Top score: {reranked[0].rerank_score if reranked else 0.0}"
                )
                return reranked[:limit]

            except Exception as e:
                logger.warning(f"Jev reranking failed ({e}), falling back to hybrid heuristic.")

        # Fallback Engine: Vector + Graph Topology + Keyword matches
        query_words = set(query.lower().split())
        for item in candidates:
            score = item.vector_score * 0.70
            if item.traversed_graph_facts:
                score += min(len(item.traversed_graph_facts) * 0.05, 0.15)
            combined_text = f"{item.section_header} {item.text}".lower()
            keyword_matches = sum(1 for w in query_words if len(w) > 3 and w in combined_text)
            score += min(keyword_matches * 0.03, 0.15)
            item.rerank_score = round(score, 4)

        reranked = sorted(candidates, key=lambda x: x.rerank_score or 0.0, reverse=True)
        return reranked[:limit]


reranker = CrossReranker()
