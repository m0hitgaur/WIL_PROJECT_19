"""
Phase 6 Verification Tests: Answer Generation, Citation Guardrail, Hallucination Grader, Disclaimer, and Self-Healing.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.state import AgentState
from guardrails.citation_checker import citation_checker
from guardrails.disclaimer_injector import inject_disclaimer, DISCLAIMER_TEXT
from agent.graph import financial_rag_app
from retrieval.unified_cypher import RetrievedItem


def test_guardrails_unit():
    print("\n1. Testing Citation Checker Unit Logic...")
    fake_chunk = RetrievedItem(
        chunk_id="AU-Vanguard_ETFs_performance_summary_c10",
        document_name="AU-Vanguard_ETFs_performance_summary",
        text="Sample text",
        vector_score=0.88,
    )

    # Valid draft
    valid_state = {
        "draft_answer": "The VAS return was 12.1% [AU-Vanguard_ETFs_performance_summary_c10].",
        "reranked_chunks": [fake_chunk],
    }
    res_valid = citation_checker.check(valid_state)
    assert res_valid["citation_error"] is None, "Valid draft failed citation check!"
    print("✅ Valid citation passed.")

    # Missing citation draft
    missing_state = {
        "draft_answer": "The VAS return was 12.1% without citation.",
        "reranked_chunks": [fake_chunk],
    }
    res_missing = citation_checker.check(missing_state)
    assert res_missing["citation_error"] is not None, "Missing citation was not caught!"
    print("✅ Missing citation correctly flagged.")

    # Unknown citation draft
    unknown_state = {
        "draft_answer": "The VAS return was 12.1% [invalid_chunk_c999].",
        "reranked_chunks": [fake_chunk],
    }
    res_unknown = citation_checker.check(unknown_state)
    assert res_unknown["citation_error"] is not None, "Unknown citation was not caught!"
    print("✅ Unknown chunk citation correctly flagged.")

    # Disclaimer injection
    print("\n2. Testing Statutory Disclaimer Injector...")
    disc_res = inject_disclaimer({"draft_answer": "Factual answer."})
    assert "Disclaimer:" in disc_res["final_answer"]
    print("✅ Disclaimer properly appended.")


def test_full_rag_execution():
    print("\n3. Testing End-to-End Financial RAG Application with Real Query...")
    query = "What is the return performance for Vanguard Australian Shares Index ETF (VAS)?"
    
    initial_state = {
        "messages": [],
        "user_query": query,
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

    print(f"Executing query: '{query}'...")
    final_state = financial_rag_app.invoke(initial_state)

    print("\n" + "=" * 60)
    print("FINAL RAG RESPONSE:")
    print("=" * 60)
    print(final_state.get("final_answer"))
    print("=" * 60)

    # Verification assertions
    final_text = final_state.get("final_answer", "")
    assert len(final_text) > 0, "Empty response generated!"
    assert "Disclaimer:" in final_text, "Disclaimer was missing!"
    print("\n--- Phase 6 Verification Completed Successfully! ---\n")


if __name__ == "__main__":
    print("\n--- Running Phase 6 Verification ---")
    test_guardrails_unit()
    test_full_rag_execution()
