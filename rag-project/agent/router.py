"""
Router and Query Condenser Nodes for LangGraph.
Condenses multi-turn conversations into standalone queries and routes between
conversational chat and hybrid financial document retrieval.
"""

import json
import logging
from typing import Dict, Any, List
import ollama
from config import settings
from agent.state import AgentState

logger = logging.getLogger(__name__)


CONDENSE_PROMPT = """You are a financial query analyzer.
Given the conversation history and a user's latest follow-up question, rewrite the follow-up question into a single, standalone query that includes all necessary context (fund names, metrics, entities, dates).
If the question is already complete or is a greeting/conversational phrase (e.g. "hello", "thank you"), leave it unchanged.

Conversation History:
{history}

User Follow-Up: {query}

Standalone Query:"""

ROUTER_PROMPT = """Classify the following query into exactly one category:
1. 'conversational' - Greetings, pleasantries, small talk, questions about who you are.
2. 'retrieval' - Questions about financial funds, performance, metrics, reports, Vanguard, fees, holdings, dates, or documents.

Query: "{query}"

Output ONLY a JSON object:
{{"route": "conversational" | "retrieval"}}"""


class AgentRouter:
    """Manages query rewriting and intent classification."""

    def __init__(self, model: str = None, client=None):
        self.model = model or settings.OLLAMA_LLM_MODEL
        self.client = client or ollama.Client(host=settings.OLLAMA_BASE_URL)

    def condense_query(self, state: AgentState) -> Dict[str, Any]:
        """Condense user prompt using conversation history."""
        user_query = state.get("user_query", "").strip()
        history = state.get("messages", [])

        # If there's no history, standalone query is identical to user query
        if not history or len(history) <= 1:
            return {"condensed_query": user_query}

        # Build readable history string
        hist_str = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-4:]])
        prompt = CONDENSE_PROMPT.format(history=hist_str, query=user_query)

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.0, "num_predict": 64},
            )
            condensed = response["response"].strip()
            return {"condensed_query": condensed or user_query}
        except Exception as e:
            logger.warning(f"Query condensation failed: {e}")
            return {"condensed_query": user_query}

    def route_query(self, state: AgentState) -> Dict[str, Any]:
        """Determine whether to route to conversational LLM or hybrid retrieval."""
        condensed = state.get("condensed_query") or state.get("user_query", "")
        
        # Fast heuristic checks for basic conversational inputs
        lowered = condensed.lower().strip()
        greetings = {"hi", "hello", "hey", "good morning", "good evening", "thanks", "thank you", "who are you"}
        if lowered in greetings or len(lowered) < 4:
            return {"route": "conversational"}

        prompt = ROUTER_PROMPT.format(query=condensed)
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                format="json",
                options={"temperature": 0.0, "num_predict": 16},
            )
            data = json.loads(response["response"])
            route = data.get("route", "retrieval")
            if route not in ["conversational", "retrieval"]:
                route = "retrieval"
            return {"route": route}
        except Exception:
            return {"route": "retrieval"}


agent_router = AgentRouter()
