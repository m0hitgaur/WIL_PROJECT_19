"""
Phase 5 Verification Tests: LangGraph Routing, Unified Cypher Retrieval, and Reranking.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.graph import retrieval_agent
from agent.state import AgentState
from retrieval.unified_cypher import unified_retriever
from retrieval.reranker import reranker


def test_phase5_pipeline():
    print("\n--- Running Phase 5 Verification ---")

    # 1. Test Conversational Routing via LangGraph
    print("\n1. Testing Conversational Routing ('Hello there!')...")
    conv_input = {
        "messages": [],
        "user_query": "Hello there!",
        "condensed_query": "",
        "route": "",
        "retrieved_candidates": [],
        "reranked_chunks": [],
        "context_string": "",
        "draft_answer": "",
        "citation_error": None,
        "hallucination_error": None,
        "iteration_count": 0,
        "final_answer": "",
    }
    conv_res = retrieval_agent.invoke(conv_input)
    print(f"✅ Route chosen: {conv_res.get('route')}")
    print(f"✅ Conversational answer: {conv_res.get('final_answer')[:120]}...")
    assert conv_res.get("route") == "conversational"

    # 2. Test Unified Vector + Graph Retrieval
    print("\n2. Testing Unified Cypher Retrieval (Vector Match + Graph Facts)...")
    query = "What is the 1-year return and performance for Vanguard Australian Shares Index ETF?"
    candidates = unified_retriever.retrieve(query, top_k=4)
    assert len(candidates) > 0, "No candidates retrieved!"
    print(f"✅ Retrieved {len(candidates)} candidates:")
    for idx, c in enumerate(candidates):
        facts_preview = f" (Facts: {len(c.traversed_graph_facts)})" if c.traversed_graph_facts else ""
        print(f"   Hit {idx+1}: [{c.chunk_id}] score={c.vector_score:.4f}{facts_preview}")
        for fact in c.traversed_graph_facts:
            print(f"     ↳ Traversed Fact: {fact}")

    # 3. Test Reranker Filtering
    print("\n3. Testing Candidate Reranker...")
    reranked = reranker.rerank(query=query, candidates=candidates, top_n=2)
    assert len(reranked) == 2
    print(f"✅ Kept top {len(reranked)} reranked chunks:")
    for r in reranked:
        print(f"   [{r.chunk_id}] composite_score={r.rerank_score}")

    # 4. Test End-to-End LangGraph Flow for Financial Query
    print("\n4. Testing Full LangGraph Retrieval Workflow...")
    rag_input = {
        "messages": [
            {"role": "user", "content": "I want to look at Vanguard Australian ETFs."},
            {"role": "assistant", "content": "Sure, I can help you with Vanguard Australian ETFs."},
        ],
        "user_query": "What is the return for VAS?",
        "condensed_query": "",
        "route": "",
        "retrieved_candidates": [],
        "reranked_chunks": [],
        "context_string": "",
        "draft_answer": "",
        "citation_error": None,
        "hallucination_error": None,
        "iteration_count": 0,
        "final_answer": "",
    }
    rag_res = retrieval_agent.invoke(rag_input)
    print(f"✅ Condensed Query: '{rag_res.get('condensed_query')}'")
    print(f"✅ Route: '{rag_res.get('route')}'")
    print(f"✅ Top Chunks: {len(rag_res.get('reranked_chunks', []))}")
    assert rag_res.get("route") == "retrieval"
    assert len(rag_res.get("reranked_chunks", [])) > 0
    print(f"✅ Context String Preview:\n{rag_res.get('context_string')[:250]}...\n")

    print("\n--- Phase 5 Verification Completed Successfully! ---\n")


if __name__ == "__main__":
    test_phase5_pipeline()
