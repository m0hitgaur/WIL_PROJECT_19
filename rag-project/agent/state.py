"""
State Definition for Stateful LangGraph Agent.
Tracks multi-turn context, routing decisions, retrieval candidates, citations, and evaluation status.
"""

from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
import operator
from retrieval.unified_cypher import RetrievedItem


class AgentState(TypedDict):
    """The central state of the LangGraph agent."""
    messages: Annotated[List[Dict[str, str]], operator.add]
    user_query: str
    condensed_query: str
    route: str  # 'conversational' | 'retrieval' | 'advice_refusal'
    is_personal_advice: bool
    confidence: float
    retrieved_candidates: List[RetrievedItem]
    reranked_chunks: List[RetrievedItem]
    alias_map: Dict[str, str]  # e.g. {"C1": "AU-Vanguard_ETFs_performance_summary_c10"}
    context_string: str
    draft_answer: str
    citation_error: Optional[str]
    hallucination_error: Optional[str]
    iteration_count: int
    final_answer: str
