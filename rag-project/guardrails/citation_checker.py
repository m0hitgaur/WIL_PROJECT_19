"""
Deterministic Citation Checker Guardrail.
Scans drafted response using regex to verify that factual claims contain valid [Chunk_ID] citations
matching the retrieved chunks passed into the prompt.
Supports full IDs (e.g. [AU-Vanguard_ETFs_performance_summary_c10]), prefixes ([CHUNK_ID: ...]),
and shorthand references ([c10]).
"""

import re
import logging
from typing import Dict, Any, List, Set
from agent.state import AgentState

logger = logging.getLogger(__name__)

# Flexible regex supporting:
# [AU-Vanguard_ETFs_performance_summary_c10]
# [CHUNK_ID: AU-Vanguard_ETFs_performance_summary_c10]
# [c10]
CITATION_REGEX = re.compile(
    r"\[(?:CHUNK_ID:\s*)?([a-zA-Z0-9_\-\.]+_[cC]\d+|[a-zA-Z0-9_\-\.]+_table_\d+|[cC]\d+)\]",
    re.IGNORECASE,
)


class CitationChecker:
    """Verifies that generated responses include proper chunk citations."""

    def check(self, state: AgentState) -> Dict[str, Any]:
        """
        Evaluate the drafted response for citations.
        
        Returns:
            Dict updating citation_error (None if valid, error message if invalid).
        """
        draft = state.get("draft_answer", "").strip()
        reranked_chunks = state.get("reranked_chunks", [])
        
        # Build mapping of canonical chunk IDs and shorthand forms (e.g. 'c10')
        valid_chunk_ids: Set[str] = set()
        shorthand_map: Dict[str, str] = {}
        for c in reranked_chunks:
            valid_chunk_ids.add(c.chunk_id.lower())
            # Map shorthand e.g. 'c10' to full chunk_id
            parts = c.chunk_id.split("_")
            short_id = parts[-1].lower()  # 'c10'
            shorthand_map[short_id] = c.chunk_id.lower()

        # If answer states info not available, citations are not mandatory
        if "not available" in draft.lower() or "not provided" in draft.lower() or "does not contain" in draft.lower():
            return {"citation_error": None}

        # Extract citations
        raw_citations = CITATION_REGEX.findall(draft)

        if not raw_citations:
            sample_ids = [c.chunk_id for c in reranked_chunks[:2]]
            logger.warning("Citation check FAILED: No bracketed [Chunk_ID] found in response.")
            return {
                "citation_error": (
                    "No [Chunk_ID] citations detected in your draft. "
                    f"You must cite the source chunks (e.g. {sample_ids}) "
                    "at the end of every factual sentence."
                )
            }

        # Normalize and validate citations
        invalid_citations = []
        for cite in raw_citations:
            cite_clean = cite.strip().lower()
            if cite_clean in valid_chunk_ids:
                continue
            elif cite_clean in shorthand_map:
                continue
            else:
                invalid_citations.append(cite)

        if invalid_citations:
            logger.warning(f"Citation check FAILED: Referenced unknown chunk IDs: {invalid_citations}")
            return {
                "citation_error": (
                    f"The citations {invalid_citations} do not match any of the provided chunks: "
                    f"{[c.chunk_id for c in reranked_chunks]}. Only cite the provided Chunk IDs."
                )
            }

        logger.info(f"Citation check PASSED. Verified citations: {raw_citations}")
        return {"citation_error": None}


citation_checker = CitationChecker()
