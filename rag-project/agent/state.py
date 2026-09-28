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
    route: str  # 'conversational' | 'retrieval'
    retrieved_candidates: List[RetrievedItem]
    reranked_chunks: List[RetrievedItem]
    context_string: str
    draft_answer: str
    citation_error: Optional[str]
    hallucination_error: Optional[str]
    iteration_count: int
    final_answer: str
