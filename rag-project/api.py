"""
FastAPI wrapper around the existing pipeline, so an HTML/JS page can replace Streamlit.

Run from the project root (next to config.py):
    pip install fastapi uvicorn
    uvicorn api:app --port 8000 --reload
"""
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from config import settings
from database.neo4j_client import neo4j_client
from agent.graph import financial_rag_app

app = FastAPI(title="Financial RAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5178", "http://127.0.0.1:5173",   # React (Vite)
        "http://localhost:5500", "http://127.0.0.1:5500",   # plain HTML version
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
CITATION_RE = re.compile(r"\[([^\[\]]+)\]")


class Turn(BaseModel):
    role: str
    content: str


class Query(BaseModel):
    question: str
    history: list[Turn] = []


def _doc_for_chunk(chunk_id: str):
    rows = neo4j_client.execute_query(
        "MATCH (c:Chunk {chunk_id: $cid})--(d:Document) RETURN d.name AS name LIMIT 1",
        {"cid": chunk_id},
    )
    return rows[0]["name"] if rows else None


@app.post("/query")
def query(q: Query):
    messages = [t.model_dump() for t in q.history] + [{"role": "user", "content": q.question}]
    state = financial_rag_app.invoke({
        "messages": messages, "user_query": q.question, "condensed_query": "", "route": "",
        "retrieved_candidates": [], "reranked_chunks": [], "context_string": "",
        "draft_answer": "", "citation_error": None, "hallucination_error": None,
        "iteration_count": 0, "final_answer": "",
    })
    answer = state.get("final_answer", "")
    chunks = state.get("reranked_chunks", [])
    by_id = {c.chunk_id: c for c in chunks}

    # Only chunks the answer actually cites (bracketed [chunk_id]) become citations
    citations, seen = [], set()
    for group in CITATION_RE.findall(answer):
        for cid in (p.strip() for p in group.split(",")):
            c = by_id.get(cid)
            if c and cid not in seen and c.page_numbers:
                seen.add(cid)
                doc = _doc_for_chunk(cid)
                if doc:
                    citations.append({
                        "doc_title": doc,
                        "page": int(min(c.page_numbers)),
                        "quote": c.text[:300],
                        "pdf_url": f"http://localhost:8000/pdf/{doc}",
                    })

    facts = []
    for c in chunks:
        for f in c.traversed_graph_facts:
            if f not in facts:
                facts.append(f)
    return {"answer": answer, "citations": citations, "facts": facts}


@app.get("/pdf/{doc_name}")
def pdf(doc_name: str):
    rows = neo4j_client.execute_query(
        "MATCH (d:Document {name: $n}) RETURN d.pdf_data AS blob, d.file_path AS path LIMIT 1",
        {"n": doc_name},
    )
    data = None
    if rows and rows[0].get("blob"):
        data = bytes(rows[0]["blob"])
    elif rows and rows[0].get("path") and Path(rows[0]["path"]).is_file():
        data = Path(rows[0]["path"]).read_bytes()
    else:
        fallback = settings.DATA_DIR / f"{Path(doc_name).stem}.pdf"  # Path().stem blocks ../ tricks
        if fallback.is_file():
            data = fallback.read_bytes()
    if data is None:
        raise HTTPException(404, f"No PDF found for '{doc_name}'")
    return Response(data, media_type="application/pdf")


@app.get("/stats")
def stats():
    rows = neo4j_client.execute_query(
        "CALL { MATCH (d:Document) RETURN count(d) AS docs } "
        "CALL { MATCH (c:Chunk) RETURN count(c) AS chunks } "
        "CALL { MATCH ()-[r]->() RETURN count(r) AS rels } RETURN docs, chunks, rels"
    )
    return rows[0] if rows else {"docs": 0, "chunks": 0, "rels": 0}
