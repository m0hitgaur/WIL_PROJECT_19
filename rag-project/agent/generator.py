"""
Draft Answer Generator Node.
Generates grounded responses from retrieved context using clean short chunk aliases ([C1], [C2]),
enforcing strict citation discipline while expanding token budget for complete generation.
"""

import logging
import re
from typing import Dict, Any, List
import ollama
from config import settings
from agent.state import AgentState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a specialized financial document assistant operating in a strict CLOSED-WORLD environment.
Your task is to answer the user's question accurately using ONLY the provided document context chunks.

CRITICAL COMPLIANCE RULES:
1. Every factual claim, number, percentage, fee, date, or metric MUST end with its source citation marker, e.g. [C1] or [C2].
   Example:
   "The Vanguard Australian Shares Index ETF reported a 1-year return of 12.1% [C1]. Its management fee is 0.07% p.a. [C2]."
2. If multiple chunks support the claim, you may cite them as [C1, C2] or [C1][C2].
3. DO NOT use outside financial knowledge or assumptions. If the provided context does not contain the answer, state clearly: "Based on the provided documents, this information is not available."
4. Keep the answer simple, quantitative but non-technical, and directly responsive to the non-expert user.
"""


class DraftGenerator:
    """Generates strictly grounded answers with chunk-level citations."""

    def __init__(self, model: str = None, client=None):
        self.model = model or settings.OLLAMA_LLM_MODEL
        self.client = client or ollama.Client(host=settings.OLLAMA_BASE_URL)

    def generate(self, state: AgentState) -> Dict[str, Any]:
        """Generate a draft answer based on reranked context chunks using short aliases."""
        query = state.get("condensed_query") or state.get("user_query", "")
        chunks = state.get("reranked_chunks", [])
        citation_error = state.get("citation_error")
        hallucination_error = state.get("hallucination_error")
        iteration = state.get("iteration_count", 0) + 1

        # Build alias map: C1 -> full_chunk_id, C2 -> full_chunk_id
        alias_map: Dict[str, str] = {}
        context_blocks: List[str] = []
        for i, chunk in enumerate(chunks, 1):
            alias = f"C{i}"
            alias_map[alias] = chunk.chunk_id
            alias_map[alias.lower()] = chunk.chunk_id

            header = f"[{alias}] (Document: {chunk.document_name}, Page: {chunk.page_numbers})"
            facts = ""
            if chunk.traversed_graph_facts:
                compact_facts = chunk.traversed_graph_facts[
                    :3
                ]  # Prune to top 3 facts to save tokens
                facts = (
                    "Key Relations:\n"
                    + "\n".join([f"  • {f}" for f in compact_facts])
                    + "\n"
                )
            context_blocks.append(f"{header}\n{facts}Text:\n{chunk.text.strip()}\n")

        context_string = "\n".join(context_blocks)
        available_aliases = [f"[{k}]" for k in alias_map if k.startswith("C")]

        prompt_parts = [
            f"Question: {query}\n",
            f"Provided Document Context:\n{context_string}\n",
            f"Available Citation Markers: {', '.join(available_aliases)}\n",
        ]

        if citation_error:
            prompt_parts.append(
                f"\nIMPORTANT CORRECTION: Your previous draft had citation issues: {citation_error}\n"
                f"Please ensure every factual sentence ends with one of {available_aliases}."
            )
        elif hallucination_error:
            prompt_parts.append(
                f"\nIMPORTANT CORRECTION: Your previous draft had grounding issues: {hallucination_error}\n"
                "Please rewrite relying STRICTLY on the document context provided above."
            )

        prompt_parts.append("\nAnswer with citations:")
        full_prompt = "\n".join(prompt_parts)

        try:
            combined_prompt = f"{SYSTEM_PROMPT}\n\n{full_prompt}"
            response = self.client.generate(
                model=self.model,
                prompt=combined_prompt,
                options={"temperature": 0.0, "num_predict": 1024},
                keep_alive=-1,
            )
            draft = response.get("response", "").strip()
            logger.info(
                f"Generated draft answer (length {len(draft)}): {draft[:120]}..."
            )
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            draft = ""

        # If retry produced empty string or error, recover previous content if present
        if not draft:
            prev_draft = state.get("draft_answer", "").strip()
            if prev_draft and "error occurred" not in prev_draft.lower():
                logger.info("Restoring previous non-empty draft after retry.")
                draft = prev_draft
            else:
                draft = "An error occurred while generating the answer from document context."

        return {
            "draft_answer": draft,
            "context_string": context_string,
            "alias_map": alias_map,
            "iteration_count": iteration,
            "citation_error": None,
            "hallucination_error": None,
        }


draft_generator = DraftGenerator()
