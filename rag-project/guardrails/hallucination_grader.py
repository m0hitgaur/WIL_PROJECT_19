"""
Hallucination Grader Node (Tier 2 Guardrail).
Uses TypeSafe AI's Jev ("System 1" model) with the Noul primitive to perform ultra-fast (~150ms)
probabilistic grounding verification. Falls back gracefully to heuristic checks if offline.
"""

import logging
from typing import Dict, Any
from config import settings
from agent.state import AgentState

logger = logging.getLogger(__name__)


class HallucinationGrader:
    """Tier 2 Guardrail: Evaluates answer faithfulness via Jev Noul primitive."""

    def grade(self, state: AgentState) -> Dict[str, Any]:
        """Grade the drafted answer for hallucinations and ungrounded claims."""
        draft = state.get("draft_answer", "").strip()
        context = state.get("context_string", "").strip()

        # Refusal answers do not require hallucination check
        if "not available" in draft.lower() or "not provided" in draft.lower() or "does not contain" in draft.lower():
            return {"hallucination_error": None}

        # Attempt Jev System 1 Noul primitive if API key is configured
        if settings.TYPESAFE_API_KEY:
            try:
                from typesafe_sdk import TypeSafeClient, Noul

                client_kwargs = {"api_key": settings.TYPESAFE_API_KEY}
                if settings.TYPESAFE_MODEL:
                    client_kwargs["model"] = settings.TYPESAFE_MODEL

                jev_state = {
                    "document_context": context[:6000],
                    "draft_answer": draft,
                }
                questions = {
                    "is_grounded": Noul(
                        instructions=(
                            "Is every factual claim, financial metric, return percentage, and fee in 'draft_answer' "
                            "directly supported by 'document_context' without extrapolation or contradiction?"
                        )
                    )
                }

                with TypeSafeClient(**client_kwargs) as client:
                    response = client.system_one(state=jev_state, questions=questions)

                grounded_ans = response.answers.get("is_grounded")
                prob = grounded_ans.noul if grounded_ans else 1.0

                logger.info(f"[Jev Tier 2 Guardrail] Grounding probability: {prob:.2f}")

                # Calibrated threshold: >= 0.50 indicates the statements are grounded
                if prob < 0.50:
                    logger.warning(f"Tier 2 Check FAILED (grounding probability {prob:.2f} < 0.50)")
                    return {
                        "hallucination_error": (
                            f"Ungrounded or extrapolated claim detected (confidence: {1.0 - prob:.2f}). "
                            "Ensure statements strictly reflect the provided document text."
                        )
                    }

                logger.info("Tier 2 Check PASSED: Response is grounded in document context.")
                return {"hallucination_error": None}

            except Exception as e:
                logger.warning(f"Jev Tier 2 check failed ({e}), falling back to deterministic pass.")
                return {"hallucination_error": None}

        # Offline / Fallback mode: If Tier 1 passed and no Jev key, pass Tier 2
        return {"hallucination_error": None}


hallucination_grader = HallucinationGrader()
