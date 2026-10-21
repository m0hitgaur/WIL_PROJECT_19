"""
Router and Query Condenser Nodes for LangGraph.
Uses TypeSafe AI's Jev ("System 1" model) for high-speed (<150ms) intent routing and
strict detection of personalized financial advice (ASIC RG 244 compliance).
Includes graceful fallback if API key is not configured.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
import ollama
from config import settings
from agent.state import AgentState

logger = logging.getLogger(__name__)

# Fast keywords for fallback personal advice detection
ADVICE_PATTERNS = [
    r"\bshould\s+i\s+(buy|invest|sell|choose|pick)\b",
    r"\bwhat\s+should\s+i\s+(buy|invest|put\s+my\s+money)\b",
    r"\brecommend\s+(a\s+fund|an\s+etf|an\s+investment|stocks|shares)\b",
    r"\bwhich\s+(fund|etf)\s+(is\s+best\s+for\s+me|should\s+i\s+buy)\b",
    r"\bis\s+[a-z]{3,4}\s+good\s+for\s+(me|my\s+retirement|my\s+portfolio)\b",
    r"\bhow\s+should\s+i\s+allocate\s+my\s+(money|portfolio|savings)\b",
    r"\bpersonal(ized)?\s+financial\s+advice\b",
]
ADVICE_REGEX = re.compile("|".join(ADVICE_PATTERNS), re.IGNORECASE)

GREETINGS = {
    "hi", "hello", "hey", "good morning", "good evening", "good afternoon",
    "thanks", "thank you", "who are you", "what can you do", "help"
}

CONVERSATIONAL_PATTERNS = [
    r"^(hi|hello|hey|good\s+(morning|afternoon|evening|day))[\s!.,?]*$",
    r"^(hi|hello|hey)\s+(there|assistant|bot|clarifi)[\s!.,?]*$",
    r"^(who\s+are\s+you|what\s+can\s+you\s+do|how\s+are\s+you|what\s+is\s+your\s+name)[\s!.,?]*$",
    r"^(thanks|thank\s+you|cheers|bye|goodbye|see\s+you)[\s!.,?]*$",
]
CONVERSATIONAL_REGEX = re.compile("|".join(CONVERSATIONAL_PATTERNS), re.IGNORECASE)

CONDENSE_PROMPT = """You are a financial query analyzer.
Given the conversation history and a user's latest follow-up question, rewrite the follow-up question into a single, standalone query that includes all necessary context (fund names, metrics, entities, dates).
If the question is already complete or is a greeting/conversational phrase (e.g. "hello", "thank you"), leave it unchanged.

Conversation History:
{history}

User Follow-Up: {query}

Standalone Query:"""


ETF_EXPANSIONS = [
    (r"\bVAS\b", "Vanguard Australian Shares Index ETF (VAS)"),
    (r"\bVGS\b", "Vanguard MSCI Index International Shares ETF (VGS)"),
    (r"\bVAP\b", "Vanguard Australian Property Securities Index ETF (VAP)"),
    (r"\bVHY\b", "Vanguard Australian Shares High Yield ETF (VHY)"),
    (r"\bVLC\b", "Vanguard MSCI Australian Large Companies Index ETF (VLC)"),
    (r"\bVSO\b", "Vanguard MSCI Australian Small Companies Index ETF (VSO)"),
]


def _expand_tickers(text: str) -> str:
    expanded = text
    for pattern, full_name in ETF_EXPANSIONS:
        expanded = re.sub(pattern, full_name, expanded)
    return expanded


class AgentRouter:
    """Manages query rewriting and intent classification via Jev System 1 with fallback."""

    def __init__(self, model: str = None, client=None):
        self.model = model or settings.OLLAMA_LLM_MODEL
        self.ollama_client = client or ollama.Client(host=settings.OLLAMA_BASE_URL)

    def condense_query(self, state: AgentState) -> Dict[str, Any]:
        """Condense user prompt using conversation history and ETF ticker expansion."""
        user_query = state.get("user_query", "").strip()
        history = state.get("messages", [])

        # If there's no history or short greeting, expand tickers directly
        if not history or len(history) <= 1 or user_query.lower() in GREETINGS:
            return {"condensed_query": _expand_tickers(user_query)}

        # Build readable history string
        hist_str = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-4:]])
        prompt = CONDENSE_PROMPT.format(history=hist_str, query=user_query)

        try:
            response = self.ollama_client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.0, "num_predict": 64},
                keep_alive=-1,
            )
            condensed = response["response"].strip()
            return {"condensed_query": _expand_tickers(condensed or user_query)}
        except Exception as e:
            logger.warning(f"Query condensation failed: {e}")
            return {"condensed_query": _expand_tickers(user_query)}

    def route_query(self, state: AgentState) -> Dict[str, Any]:
        """
        Determine whether to route to:
        - 'advice_refusal': User asks for personal financial advice (ASIC RG 244 disclaimer)
        - 'conversational': Greeting, chit-chat, or general capability question
        - 'retrieval': Hybrid vector + graph financial document retrieval
        """
        query = state.get("condensed_query") or state.get("user_query", "")
        cleaned = query.strip()
        lowered = cleaned.lower()

        # Fast path 1: Immediate greeting and conversational query check (<1ms)
        if (lowered in GREETINGS or len(cleaned) < 4 or CONVERSATIONAL_REGEX.search(cleaned)) and not ADVICE_REGEX.search(cleaned):
            return {
                "route": "conversational",
                "is_personal_advice": False,
                "confidence": 1.0,
            }

        # Try Jev System 1 model if API key is configured
        if settings.TYPESAFE_API_KEY:
            try:
                from typesafe_sdk import TypeSafeClient, Choice, Noul

                client_kwargs = {"api_key": settings.TYPESAFE_API_KEY}
                if settings.TYPESAFE_MODEL:
                    client_kwargs["model"] = settings.TYPESAFE_MODEL

                with TypeSafeClient(**client_kwargs) as client:
                    jev_state = {
                        "user_query": cleaned,
                    }
                    questions = {
                        "intent": Choice(
                            instructions="Classify the user intent into exactly one category.",
                            criteria={
                                "retrieval": "User is asking for factual numbers, returns, fees, fund details, or information from Vanguard reports.",
                                "conversational": "User is greeting, thanking, asking who you are, or general conversational pleasantries.",
                                "advice_refusal": "User is asking for personal financial advice, recommendations on what to buy/sell/invest in, or personal allocation strategies.",
                            },
                        ),
                        "is_personal_advice": Noul(
                            instructions="Is the user asking for personal financial advice or asking what they personally should invest in, buy, or sell?"
                        ),
                    }
                    response = client.system_one(state=jev_state, questions=questions)

                intent_ans = response.answers.get("intent")
                advice_ans = response.answers.get("is_personal_advice")

                selected_intent = intent_ans.choice if intent_ans else "retrieval"
                advice_prob = advice_ans.noul if advice_ans else 0.0
                confidence = intent_ans.confidence if intent_ans else 0.8

                logger.info(
                    f"[Jev Router] Selected intent: '{selected_intent}' (conf: {confidence:.2f}), "
                    f"personal advice prob: {advice_prob:.2f}"
                )

                if selected_intent == "advice_refusal" or advice_prob >= 0.65:
                    return {
                        "route": "advice_refusal",
                        "is_personal_advice": True,
                        "confidence": max(confidence, advice_prob),
                    }

                if selected_intent == "conversational":
                    return {
                        "route": "conversational",
                        "is_personal_advice": False,
                        "confidence": confidence,
                    }

                return {
                    "route": "retrieval",
                    "is_personal_advice": False,
                    "confidence": confidence,
                }

            except Exception as e:
                logger.warning(f"Jev routing failed ({e}), falling back to heuristic engine.")

        # Fallback Engine: Regex + Heuristic
        if ADVICE_REGEX.search(cleaned):
            logger.info(f"[Fallback Router] Query matched personal financial advice regex: '{cleaned}'")
            return {
                "route": "advice_refusal",
                "is_personal_advice": True,
                "confidence": 0.95,
            }

        return {
            "route": "retrieval",
            "is_personal_advice": False,
            "confidence": 0.85,
        }


agent_router = AgentRouter()
