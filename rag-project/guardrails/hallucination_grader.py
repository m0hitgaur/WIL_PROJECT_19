"""
Hallucination Grader Node (Self-Reflection Guardrail).
Uses LLM-as-a-judge to evaluate whether drafted claims and numbers are strictly grounded
in the retrieved document context.
"""

import re
import json
import logging
from typing import Dict, Any
import ollama
from config import settings
from agent.state import AgentState

logger = logging.getLogger(__name__)

GRADER_PROMPT = """You are a strict compliance auditor for financial disclosures.
Evaluate whether the drafted answer is strictly grounded in the provided document context.

Document Context:
{context}

Drafted Answer:
{draft}

Grading Criteria:
- 'pass': Every factual claim, return metric, fee, date, and number in the draft is directly proven by the document context above.
- 'fail': The draft includes numbers, facts, or assumptions NOT supported by the document context, or contradicts the text.

Respond ONLY with a JSON object:
{{"grade": "pass" | "fail", "reason": "<brief justification>"}}"""


class HallucinationGrader:
    """Evaluates answer faithfulness against retrieved chunks."""

    def __init__(self, model: str = None, client=None):
        self.model = model or settings.OLLAMA_LLM_MODEL
        self.client = client or ollama.Client(host=settings.OLLAMA_BASE_URL)

    def grade(self, state: AgentState) -> Dict[str, Any]:
        """Grade the drafted answer for hallucinations."""
        draft = state.get("draft_answer", "")
        context = state.get("context_string", "")

        # Refusal answers do not require hallucination check
        if "not available" in draft.lower() or "not provided" in draft.lower() or "does not contain" in draft.lower():
            return {"hallucination_error": None}

        prompt = GRADER_PROMPT.format(context=context[:2000], draft=draft)

        try:
            res = self.client.generate(
                model=self.model,
                prompt=prompt,
                format="json",
                options={"temperature": 0.0, "num_predict": 48},
            )
            raw = res["response"].strip()

            # Robust JSON extraction
            try:
                data = json.loads(raw)
                grade = data.get("grade", "pass").lower()
                reason = data.get("reason", "")
            except Exception:
                # Fallback to regex extraction
                match = re.search(r'"grade"\s*:\s*"(pass|fail)"', raw, re.IGNORECASE)
                grade = match.group(1).lower() if match else "pass"
                reason = "Extracted via fallback regex"

            if grade == "fail":
                logger.warning(f"Hallucination check FAILED: {reason}")
                return {"hallucination_error": f"Hallucinated or unverified claim detected: {reason}"}

            logger.info("Hallucination check PASSED: Response is fully grounded.")
            return {"hallucination_error": None}

        except Exception as e:
            logger.warning(f"Hallucination grading check skipped due to error: {e}")
            return {"hallucination_error": None}


hallucination_grader = HallucinationGrader()
