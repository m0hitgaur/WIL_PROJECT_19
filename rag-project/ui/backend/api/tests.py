from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.urls import reverse

from api.views import _resolve_citations
from agent.generator import draft_generator


class PdfCitationTests(TestCase):
    @patch("api.views.settings.OLLAMA_LLM_MODEL", "llama3.2:1b")
    @patch("api.views.settings.OLLAMA_EMBED_MODEL", "all-minilm")
    @patch("api.views.settings.EMBEDDING_DIM", 384)
    @patch("api.views.settings.OLLAMA_VLM_MODEL", "qwen2.5-vl:7b")
    @patch("api.views.neo4j_client.execute_query")
    @patch(
        "api.views.neo4j_client.check_connection",
        return_value={
            "connected": True,
            "server_agent": "Neo4j/5.x",
            "apoc_installed": True,
        },
    )
    def test_system_stats_returns_live_status_and_graph_metrics(
        self, _check_connection, execute_query
    ):
        execute_query.return_value = [
            {"docs": 1, "chunks": 49, "tables": 2, "rels": 12}
        ]

        response = self.client.get(reverse("system-stats"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "neo4j": {
                    "connected": True,
                    "server_agent": "Neo4j/5.x",
                    "apoc_installed": True,
                },
                "models": {
                    "llm": "llama3.2:1b",
                    "embeddings": "all-minilm",
                    "embedding_dim": 384,
                    "vlm": "qwen2.5-vl:7b",
                },
                "metrics": {
                    "documents": 1,
                    "chunks": 49,
                    "tables": 2,
                    "edges": 12,
                },
            },
        )

    @patch(
        "api.views.neo4j_client.check_connection",
        side_effect=RuntimeError("Neo4j unavailable"),
    )
    def test_system_stats_reports_database_failure(self, _check_connection):
        response = self.client.get(reverse("system-stats"))

        self.assertEqual(response.status_code, 503)
        self.assertIn("Neo4j unavailable", response.json()["error"])

    def test_generator_uses_retrieved_ids_and_bounded_output(self):
        chunk_id = "report_c12"
        chunk = SimpleNamespace(chunk_id=chunk_id)
        with patch.object(
            draft_generator.client,
            "chat",
            return_value={"message": {"content": f"Answer [{chunk_id}]."}},
        ) as chat:
            result = draft_generator.generate(
                {
                    "user_query": "What is the fee?",
                    "reranked_chunks": [chunk],
                    "context_string": "The fee is 0.07%.",
                    "iteration_count": 0,
                }
            )

        self.assertEqual(result["draft_answer"], f"Answer [{chunk_id}].")
        prompt = chat.call_args.kwargs["messages"][1]["content"]
        self.assertIn(f"Available citation IDs (use these exact IDs only): {chunk_id}", prompt)
        self.assertEqual(chat.call_args.kwargs["options"]["num_predict"], 160)

    def test_resolves_only_retrieved_citations_to_pdf_pages(self):
        chunk_id = "report_c12"
        chunks = [
            SimpleNamespace(
                chunk_id=chunk_id,
                page_numbers=[4, 2],
                text="The management fee is 0.07%.",
            )
        ]
        request = RequestFactory().post("/api/chat/")

        with patch(
            "api.views.neo4j_client.execute_query",
            return_value=[{"name": "report"}],
        ):
            citations = _resolve_citations(
                f"The fee is 0.07% [{chunk_id}]. [not-retrieved_c99]",
                chunks,
                request,
            )

        self.assertEqual(
            citations,
            [
                {
                    "chunk_id": chunk_id,
                    "doc_title": "report",
                    "page": 2,
                    "quote": "The management fee is 0.07%.",
                    "pdf_url": (
                        "http://testserver/api/pdf/report/#page=2"
                    ),
                }
            ],
        )

    @patch(
        "api.views.neo4j_client.execute_query",
        return_value=[{"blob": b"%PDF-1.4 test", "path": None}],
    )
    def test_pdf_route_serves_document_blob(self, _execute_query):
        response = self.client.get(reverse("pdf", kwargs={"doc_name": "report"}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("inline", response["Content-Disposition"])
        self.assertEqual(response.content, b"%PDF-1.4 test")
