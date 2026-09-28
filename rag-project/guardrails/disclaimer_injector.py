"""
Disclaimer Injector Guardrail.
Appends standard statutory financial disclaimer to the final answer payload.
"""

from typing import Dict, Any
from agent.state import AgentState

DISCLAIMER_TEXT = "\n\n---\n*Disclaimer: This information is extracted directly from the provided financial documents for informational purposes and does not constitute financial advice.*"


def inject_disclaimer(state: AgentState) -> Dict[str, Any]:
    """Append standard financial disclaimer to the drafted answer."""
    draft = state.get("draft_answer", "").strip()
    if DISCLAIMER_TEXT.strip() not in draft:
        final_answer = draft + DISCLAIMER_TEXT
    else:
        final_answer = draft

    return {"final_answer": final_answer}
