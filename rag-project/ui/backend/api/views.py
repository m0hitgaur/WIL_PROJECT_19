import sys
from pathlib import Path
import re

from django.http import Http404, HttpResponse
from django.urls import reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


# ---------------------------------------------------------
# TEAM RAG LOCATION
# ---------------------------------------------------------

RAG_PROJECT_DIR = Path(__file__).resolve().parents[3]

# Allow Django to import the existing team RAG project.
# This does NOT modify any RAG files.
if str(RAG_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_PROJECT_DIR))


# Import the existing LangGraph application exactly as supplied.
from agent.graph import financial_rag_app
from config import settings
from database.neo4j_client import neo4j_client


CITATION_RE = re.compile(r"\[([^\[\]]+)\]")


def _doc_for_chunk(chunk_id):
    rows = neo4j_client.execute_query(
        "MATCH (c:Chunk {chunk_id: $cid})--(d:Document) RETURN d.name AS name LIMIT 1",
        {"cid": chunk_id},
    )
    return rows[0]["name"] if rows else None


def _resolve_citations(answer, chunks, request):
    """Match answer citations to retrieved chunks and link them to their PDF page."""
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    citations = []
    seen = set()

    for group in CITATION_RE.findall(answer or ""):
        for chunk_id in (part.strip() for part in group.split(",")):
            chunk = by_id.get(chunk_id)
            if chunk is None or chunk_id in seen or not chunk.page_numbers:
                continue

            seen.add(chunk_id)
            doc_name = _doc_for_chunk(chunk_id)
            if not doc_name:
                continue

            page = int(min(chunk.page_numbers))
            pdf_path = reverse("pdf", kwargs={"doc_name": doc_name})
            citations.append(
                {
                    "chunk_id": chunk_id,
                    "doc_title": doc_name,
                    "page": page,
                    "quote": chunk.text[:300],
                    "pdf_url": f"{request.build_absolute_uri(pdf_path)}#page={page}",
                }
            )

    return citations


def pdf(request, doc_name):
    """Serve a PDF associated with an indexed Neo4j Document node."""
    rows = neo4j_client.execute_query(
        "MATCH (d:Document {name: $name}) "
        "RETURN d.pdf_data AS blob, d.file_path AS path LIMIT 1",
        {"name": doc_name},
    )

    data = None
    if rows and rows[0].get("blob"):
        data = bytes(rows[0]["blob"])
    elif rows and rows[0].get("path") and Path(rows[0]["path"]).is_file():
        data = Path(rows[0]["path"]).read_bytes()
    else:
        fallback = settings.DATA_DIR / f"{Path(doc_name).stem}.pdf"
        if fallback.is_file():
            data = fallback.read_bytes()

    if data is None:
        raise Http404(f"No PDF found for '{doc_name}'")

    response = HttpResponse(data, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{Path(doc_name).name}.pdf"'
    return response


@api_view(["GET"])
def system_stats(request):
    """Return live model, Neo4j connection, and graph metric details."""
    try:
        neo4j_status = neo4j_client.check_connection()
        rows = neo4j_client.execute_query(
            """
            CALL {
                MATCH (d:Document) RETURN count(d) AS docs
            }
            CALL {
                MATCH (c:Chunk) RETURN count(c) AS chunks
            }
            CALL {
                MATCH (t:Table) RETURN count(t) AS tables
            }
            CALL {
                MATCH ()-[r]->() RETURN count(r) AS rels
            }
            RETURN docs, chunks, tables, rels
            """
        )
    except Exception as exc:
        return Response(
            {"error": f"Could not load RAG system status: {exc}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    metrics = rows[0] if rows else {"docs": 0, "chunks": 0, "tables": 0, "rels": 0}
    return Response(
        {
            "neo4j": {
                "connected": neo4j_status["connected"],
                "server_agent": neo4j_status["server_agent"],
                "apoc_installed": neo4j_status["apoc_installed"],
            },
            "models": {
                "llm": settings.OLLAMA_LLM_MODEL,
                "embeddings": settings.OLLAMA_EMBED_MODEL,
                "embedding_dim": settings.EMBEDDING_DIM,
                "vlm": settings.OLLAMA_VLM_MODEL,
            },
            "metrics": {
                "documents": metrics["docs"],
                "chunks": metrics["chunks"],
                "tables": metrics["tables"],
                "edges": metrics["rels"],
            },
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------
# CHAT API
# ---------------------------------------------------------

@api_view(["POST"])
def chat(request):
    """
    Receive a question from the React frontend,
    pass it to the existing team RAG pipeline,
    and return the final answer and retrieved evidence.
    """

    question = request.data.get("question", "").strip()

    # Validate the incoming question
    if not question:
        return Response(
            {
                "error": "Please provide a question."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:

        # -------------------------------------------------
        # SAME STATE STRUCTURE USED BY TEAM app.py
        # -------------------------------------------------

        initial_state = {
            "messages": [],
            "user_query": question,
            "condensed_query": "",
            "route": "",
            "retrieved_candidates": [],
            "reranked_chunks": [],
            "context_string": "",
            "draft_answer": "",
            "citation_error": None,
            "hallucination_error": None,
            "iteration_count": 0,
            "final_answer": "",
        }

        # -------------------------------------------------
        # RUN EXISTING TEAM RAG
        # -------------------------------------------------

        final_state = financial_rag_app.invoke(initial_state)

        # Same outputs used by the team's Streamlit app
        final_answer = final_state.get("final_answer", "")
        route = final_state.get("route", "")
        reranked_chunks = final_state.get("reranked_chunks", [])

        citations = _resolve_citations(final_answer, reranked_chunks, request)

        # -------------------------------------------------
        # CONVERT RETRIEVED CHUNKS TO JSON
        # -------------------------------------------------

        sources = []

        for chunk in reranked_chunks:

            sources.append(
                {
                    "chunk_id": getattr(chunk, "chunk_id", ""),
                    "vector_score": getattr(chunk, "vector_score", None),
                    "page_numbers": getattr(chunk, "page_numbers", []),
                    "text": getattr(chunk, "text", ""),
                }
            )


        # -------------------------------------------------
        # SEND RESULT BACK TO REACT
        # -------------------------------------------------

        return Response(
            {
                "question": question,
                "answer": final_answer,
                "route": route,
                "sources": sources,
                "citations": citations,
            },
            status=status.HTTP_200_OK,
        )


    except Exception as exc:

        # During development we return the error so that
        # integration problems are visible in React.
        print(f"RAG ERROR: {exc}")

        return Response(
            {
                "question": question,
                "answer": "",
                "sources": [],
                "error": str(exc),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )