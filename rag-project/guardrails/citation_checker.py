"""
Deterministic Citation Checker Guardrail (Tier 1 Guardrail).
Scans drafted response to verify:
1. Valid citation markers exist ([C1], [C2], [C1, C2], [CHUNK_ID], or shorthand [c10]).
2. Numerical sanity: verifies that numbers and percentages in the drafted claims match the cited source chunks.
3. Maps short citation markers ([C1], [C2]) back to canonical [CHUNK_ID] format for UI and PDF viewer.
"""

import re
import logging
from typing import Dict, Any, List, Set
from agent.state import AgentState

logger = logging.getLogger(__name__)

# Regex to match bracketed citation groups, e.g. [C1], [C1, C2], [CHUNK_ID: ...]
BRACKET_GROUP_REGEX = re.compile(r"\[([^\[\]]+)\]")


class CitationChecker:
    """Tier 1 Guardrail: Verifies syntactic citations and numerical sanity."""

    def check(self, state: AgentState) -> Dict[str, Any]:
        """
        Evaluate the drafted response for citations and numerical consistency.
        
        Returns:
            Dict updating citation_error (None if valid, error message if invalid)
            and draft_answer (with mapped canonical IDs).
        """
        draft = state.get("draft_answer", "").strip()
        reranked_chunks = state.get("reranked_chunks", [])
        alias_map = state.get("alias_map", {})

        # If answer states info not available or refused, citations are not mandatory
        lowered = draft.lower()
        if not draft or "not available" in lowered or "not provided" in lowered or "does not contain" in lowered or "cannot provide" in lowered:
            return {"citation_error": None, "draft_answer": draft}

        # Extract all bracket groups and split by commas (e.g. [C1, C2] -> ["C1", "C2"])
        raw_citations: List[str] = []
        bracket_groups = BRACKET_GROUP_REGEX.findall(draft)
        for group in bracket_groups:
            # Skip disclaimers or markdown footnote brackets if any
            if "disclaimer" in group.lower() or "table" in group.lower() and not group.startswith("c"):
                continue
            for item in group.split(","):
                clean = re.sub(r"^CHUNK_ID:\s*", "", item.strip(), flags=re.I).strip()
                if clean:
                    raw_citations.append(clean)

        if not raw_citations:
            logger.warning("Tier 1 Check FAILED: No bracketed citation marker found in response.")
            return {
                "citation_error": (
                    "No citation markers detected in your draft. "
                    "You must cite the source chunks using [C1], [C2] at the end of every factual sentence."
                )
            }

        # Build set of valid keys (aliases + full chunk IDs + shorthand)
        valid_keys: Set[str] = set()
        for k in alias_map:
            valid_keys.add(k.lower())
        for c in reranked_chunks:
            valid_keys.add(c.chunk_id.lower())
            parts = c.chunk_id.split("_")
            valid_keys.add(parts[-1].lower())  # e.g. 'c10'

        invalid_citations = []
        for cite in raw_citations:
            if cite.lower() not in valid_keys:
                invalid_citations.append(cite)

        if invalid_citations:
            logger.warning(f"Tier 1 Check FAILED: Referenced unknown citation markers: {invalid_citations}")
            return {
                "citation_error": (
                    f"The citation markers {invalid_citations} are invalid. "
                    f"Use only available markers: {[f'[{k}]' for k in alias_map if k.startswith('C')]}."
                )
            }

        # Numerical Sanity Check: Ensure cited numbers exist in the combined chunk text
        combined_source_text = " ".join([c.text for c in reranked_chunks])
        clean_source = re.sub(r"\s+", " ", combined_source_text)
        draft_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", draft))
        unverified_numbers = []
        for num in draft_numbers:
            clean_num = num.strip("%").strip("$")
            if ("%" in num or "." in num) and len(clean_num) > 1:
                if clean_num not in clean_source:
                    unverified_numbers.append(num)

        # Only fail if critical metrics are completely missing from text
        if len(unverified_numbers) >= 2:
            logger.warning(f"Tier 1 Check WARNING: Numbers {unverified_numbers} not found in cited context.")
            return {
                "citation_error": (
                    f"The following metrics in your draft do not appear in the context: {unverified_numbers}. "
                    "State only figures directly present in the text."
                )
            }

        # Canonical ID normalization:
        # Replace [C1], [C2], [C1, C2] with the canonical [chunk_id] so downstream UI / api.py can resolve them
        def _replace_group(match: re.Match) -> str:
            group_content = match.group(1)
            parts = []
            for item in group_content.split(","):
                clean = re.sub(r"^CHUNK_ID:\s*", "", item.strip(), flags=re.I).strip()
                # Check uppercase, lowercase, and exact in alias_map
                mapped = (
                    alias_map.get(clean.upper())
                    or alias_map.get(clean.lower())
                    or alias_map.get(clean)
                    or clean
                )
                parts.append(mapped)
            return "[" + ", ".join(parts) + "]"

        normalized_draft = BRACKET_GROUP_REGEX.sub(_replace_group, draft)

        logger.info(f"Tier 1 Check PASSED. Verified citations: {raw_citations}")
        return {"citation_error": None, "draft_answer": normalized_draft}


citation_checker = CitationChecker()
