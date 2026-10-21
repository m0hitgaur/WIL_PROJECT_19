"""
Continuous Graph Refinement (Topological Synthesis / Self-Healing).
Detects when a relational query was satisfied by vector search where a graph relationship was absent,
synthesizes the missing relationship via LLM in a non-blocking background thread, and writes an UPDATE edge to Neo4j.
"""

import json
import logging
import threading
from typing import Dict, Any, List
import ollama
from config import settings
from database.neo4j_client import neo4j_client
from agent.state import AgentState

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """Analyze this query and supporting text chunk.
User Query: {query}
Chunk Text: {text}

Did the chunk answer a relationship between two entities (e.g. Fund and Metric, or Company and Fund) that should be connected?
If yes, output a single JSON object:
{{
  "has_relationship": true,
  "source_entity": "<entity 1>",
  "source_type": "Fund | Company | Financial_Metric",
  "relation": "REPORTED | OWNS | CONTAINS_METRIC | HAS_HOLDING",
  "target_entity": "<entity 2>",
  "target_type": "Fund | Company | Financial_Metric",
  "context": "<supporting snippet>"
}}

If no clear relational edge exists, output:
{{"has_relationship": false}}"""


class SelfHealingGraphManager:
    """Dynamically heals graph gaps based on query-chunk pairs asynchronously."""

    def __init__(self, client=None):
        self.client = client or neo4j_client

    def _background_worker(self, query: str, top_chunk_id: str, chunk_text: str):
        """Worker executing dynamic edge synthesis off the critical user path."""
        try:
            logger.info(f"[Background Self-Healing] Starting synthesis for chunk {top_chunk_id}")
            prompt = SYNTHESIS_PROMPT.format(query=query, text=chunk_text[:1000])
            client = ollama.Client(host=settings.OLLAMA_BASE_URL)
            res = client.generate(
                model=settings.OLLAMA_LLM_MODEL,
                prompt=prompt,
                format="json",
                options={"temperature": 0.0},
            )
            data = json.loads(res["response"])
            if data.get("has_relationship"):
                s_name = data.get("source_entity")
                s_type = data.get("source_type", "Fund")
                r_type = data.get("relation", "REPORTED")
                t_name = data.get("target_entity")
                t_type = data.get("target_type", "Financial_Metric")
                context = data.get("context", "")

                if s_name and t_name:
                    cypher = f"""
                    MERGE (s:`{s_type}` {{name: $s_name}})
                    MERGE (t:`{t_type}` {{name: $t_name}})
                    MERGE (s)-[r:`{r_type}`]->(t)
                    ON CREATE SET r.source = 'self_healing', r.context = $context, r.created_at = datetime()
                    """
                    self.client.execute_write(cypher, {"s_name": s_name, "t_name": t_name, "context": context})
                    logger.info(f"[Background Self-Healing] Synthesized edge: ({s_name})-[:{r_type}]->({t_name})")

        except Exception as e:
            logger.debug(f"[Background Self-Healing] Refinement completed with note: {e}")

    def refine_graph_async(self, state: AgentState) -> Dict[str, Any]:
        """Trigger background graph refinement thread if top chunk had 0 traversed facts."""
        query = state.get("condensed_query", "")
        reranked = state.get("reranked_chunks", [])
        if not reranked:
            return {"self_healing_status": "skipped_no_chunks"}

        top_chunk = reranked[0]
        # Trigger condition: query was answered by vector text, but has 0 traversed graph facts
        if len(top_chunk.traversed_graph_facts) > 0:
            return {"self_healing_status": "graph_already_connected"}

        # Launch worker in daemon thread - non-blocking
        worker = threading.Thread(
            target=self._background_worker,
            args=(query, top_chunk.chunk_id, top_chunk.text),
            daemon=True,
        )
        worker.start()
        logger.info(f"Self-healing worker dispatched in background for {top_chunk.chunk_id}")
        return {"self_healing_status": "dispatched_async"}


self_healing_manager = SelfHealingGraphManager()
