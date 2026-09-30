"""
Complete LangGraph Orchestrator for Financial Hybrid Vector-Graph RAG.
Wires together:
1. Query Condenser
2. Intent Router
3. Unified Cypher Vector + Graph Retrieval
4. Cross-Reranker
5. Grounded Draft Generator
6. Deterministic Citation Checker Guardrail (Feedback Loop)
7. Hallucination Grader Guardrail (Feedback Loop)
8. Disclaimer Injector
9. Continuous Graph Refinement (Self-Healing)
"""

import logging
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
import ollama
from config import settings
from agent.state import AgentState
from agent.router import agent_router
from retrieval.unified_cypher import unified_retriever, RetrievedItem
from retrieval.reranker import reranker
from agent.generator import draft_generator
from guardrails.citation_checker import citation_checker
from guardrails.hallucination_grader import hallucination_grader
from guardrails.disclaimer_injector import inject_disclaimer
from agent.self_healing import self_healing_manager

logger = logging.getLogger(__name__)


# ── Node Definitions ──────────────────────────────────────────────────────────

def condense_node(state: AgentState) -> Dict[str, Any]:
    return agent_router.condense_query(state)


def router_node(state: AgentState) -> Dict[str, Any]:
    return agent_router.route_query(state)


def route_decision(state: AgentState) -> str:
    return state.get("route", "retrieval")


def conversational_node(state: AgentState) -> Dict[str, Any]:
    client = ollama.Client(host=settings.OLLAMA_BASE_URL)
    user_query = state.get("user_query", "")
    prompt = (
        "You are an AI financial document assistant specialized in Australian investment funds and ETF reports. "
        "Answer the user's conversational message politely, briefly, and professionally, "
        "and invite them to ask financial or document-specific questions.\n\n"
        f"User Message: {user_query}"
    )
    try:
        res = client.generate(
            model=settings.OLLAMA_LLM_MODEL,
            prompt=prompt,
            options={"num_predict": 96},
        )
        answer = res["response"].strip()
    except Exception:
        answer = "Hello! I am your Financial Document Analysis assistant. Ask me questions about Australian funds, performance, management fees, or report notes."
    
    return {"final_answer": answer, "draft_answer": answer}


def retrieval_node(state: AgentState) -> Dict[str, Any]:
    query = state.get("condensed_query") or state.get("user_query", "")
    candidates = unified_retriever.retrieve(query=query, top_k=5)
    return {"retrieved_candidates": candidates}


def rerank_node(state: AgentState) -> Dict[str, Any]:
    query = state.get("condensed_query") or state.get("user_query", "")
    candidates = state.get("retrieved_candidates", [])
    top_chunks = reranker.rerank(query=query, candidates=candidates, top_n=3)

    context_lines = []
    for c in top_chunks:
        header = f"--- [CHUNK_ID: {c.chunk_id}] (Document: {c.document_name}, Page: {c.page_numbers}) ---"
        facts = ""
        if c.traversed_graph_facts:
            facts = "Connected Graph Facts:\n" + "\n".join([f"  • {fact}" for fact in c.traversed_graph_facts]) + "\n"
        context_lines.append(f"{header}\n{facts}Text:\n{c.text}\n")

    return {
        "reranked_chunks": top_chunks,
        "context_string": "\n".join(context_lines),
    }


def generator_node(state: AgentState) -> Dict[str, Any]:
    return draft_generator.generate(state)


def citation_check_node(state: AgentState) -> Dict[str, Any]:
    return citation_checker.check(state)


def citation_decision(state: AgentState) -> str:
    """Evaluate citation check result: retry or proceed."""
    error = state.get("citation_error")
    iteration = state.get("iteration_count", 1)
    if error and iteration < 3:
        logger.info(f"Looping back to generator (attempt {iteration+1}): {error}")
        return "retry_generator"
    return "hallucination_grader"


def hallucination_grader_node(state: AgentState) -> Dict[str, Any]:
    return hallucination_grader.grade(state)


def hallucination_decision(state: AgentState) -> str:
    """Evaluate hallucination check result: retry or proceed."""
    error = state.get("hallucination_error")
    iteration = state.get("iteration_count", 1)
    if error and iteration < 3:
        logger.info(f"Looping back to generator for hallucination correction: {error}")
        return "retry_generator"
    return "disclaimer_injector"


def disclaimer_node(state: AgentState) -> Dict[str, Any]:
    return inject_disclaimer(state)


def self_healing_node(state: AgentState) -> Dict[str, Any]:
    self_healing_manager.refine_graph_async(state)
    return {}


# ── LangGraph Workflow Construction ───────────────────────────────────────────

def build_full_rag_graph() -> StateGraph:
    """Build and compile the complete closed-world RAG workflow with guardrails."""
    workflow = StateGraph(AgentState)

    # Register Nodes
    workflow.add_node("condenser", condense_node)
    workflow.add_node("router", router_node)
    workflow.add_node("conversational", conversational_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("citation_check", citation_check_node)
    workflow.add_node("hallucination_grader", hallucination_grader_node)
    workflow.add_node("disclaimer_injector", disclaimer_node)
    workflow.add_node("self_healing", self_healing_node)

    # Set Entry Point & Routing
    workflow.set_entry_point("condenser")
    workflow.add_edge("condenser", "router")

    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "conversational": "conversational",
            "retrieval": "retrieval",
        },
    )
    workflow.add_edge("conversational", END)

    # Retrieval & Generation Chain
    workflow.add_edge("retrieval", "rerank")
    workflow.add_edge("rerank", "generator")
    workflow.add_edge("generator", "citation_check")

    # Guardrail Feedback Loops
    workflow.add_conditional_edges(
        "citation_check",
        citation_decision,
        {
            "retry_generator": "generator",
            "hallucination_grader": "hallucination_grader",
        },
    )

    workflow.add_conditional_edges(
        "hallucination_grader",
        hallucination_decision,
        {
            "retry_generator": "generator",
            "disclaimer_injector": "disclaimer_injector",
        },
    )

    workflow.add_edge("disclaimer_injector", "self_healing")
    workflow.add_edge("self_healing", END)

    return workflow.compile()


financial_rag_app = build_full_rag_graph()
