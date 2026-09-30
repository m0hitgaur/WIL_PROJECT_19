"""
Draft Answer Generator Node.
Generates grounded responses from retrieved context, enforcing strict [Chunk_ID] citations.
"""

import logging
from typing import Dict, Any
import ollama
from config import settings
from agent.state import AgentState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a specialized financial document assistant operating in a strict CLOSED-WORLD environment.
Your task is to answer the user's question accurately using ONLY the provided document context chunks.

CRITICAL COMPLIANCE RULES:
1. Every factual statement, number, percentage, fee, date, or claim MUST be immediately followed by the exact [CHUNK_ID] from which it was extracted.
   Example:
   "The Vanguard Australian Shares Index ETF (VAS) reported a 1-year return of 12.1% [AU-Vanguard_ETFs_performance_summary_c10]. Its management fee is 0.07% p.a. [AU-Vanguard_ETFs_performance_summary_c12]."
2. DO NOT use any outside financial knowledge or assumptions. If the provided context does not contain the answer, state clearly: "Based on the provided documents, this information is not available."
3. If connected graph facts or tables are provided, use them to provide clear relational context.
4. Keep the answer professional, quantitative, and directly responsive to the user.
"""


class DraftGenerator:
    """Generates strictly grounded answers with chunk-level citations."""

    def __init__(self, model: str = None, client=None):
        self.model = model or settings.OLLAMA_LLM_MODEL
        self.client = client or ollama.Client(host=settings.OLLAMA_BASE_URL)

    def generate(self, state: AgentState) -> Dict[str, Any]:
        """Generate a draft answer based on reranked context chunks."""
        query = state.get("condensed_query") or state.get("user_query", "")
        context = state.get("context_string", "")
        citation_error = state.get("citation_error")
        hallucination_error = state.get("hallucination_error")
        iteration = state.get("iteration_count", 0) + 1
        available_chunk_ids = [
            chunk.chunk_id for chunk in state.get("reranked_chunks", [])
        ]

        prompt_parts = [
            f"Question: {query}\n",
            f"Provided Document Context:\n{context}\n",
            "Available citation IDs (use these exact IDs only): "
            f"{', '.join(available_chunk_ids)}\n",
        ]

        if citation_error:
            prompt_parts.append(
                f"\nIMPORTANT CORRECTION: Your previous draft had citation issues: {citation_error}\n"
                "Please rewrite your response ensuring that EVERY factual claim ends with its source [CHUNK_ID]."
            )
        elif hallucination_error:
            prompt_parts.append(
                f"\nIMPORTANT CORRECTION: Your previous draft contained unverified claims: {hallucination_error}\n"
                "Please rewrite your response relying STRICTLY on the text provided above."
            )

        prompt_parts.append("\nAnswer with citations:")
        full_prompt = "\n".join(prompt_parts)

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt},
                ],
                options={"temperature": 0.0, "num_predict": 160},
            )
            draft = response["message"]["content"].strip()
            logger.info(f"Generated draft answer (length {len(draft)}): {draft[:120]}...")
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            draft = "An error occurred while generating the answer from document context."

        return {
            "draft_answer": draft,
            "iteration_count": iteration,
            "citation_error": None,
            "hallucination_error": None,
        }


draft_generator = DraftGenerator()
