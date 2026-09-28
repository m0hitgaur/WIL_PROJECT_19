"""
Streamlit Web Application: Financial Hybrid Vector-Graph RAG.
Interactive UI for querying financial reports with LangGraph agentic routing,
native Neo4j vector-to-graph traversal, citation verification, and graph inspection.

Run via:
    streamlit run app.py
"""

import sys
from pathlib import Path
import streamlit as st

# Setup sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from database.neo4j_client import neo4j_client
from database.schema import schema_manager
from agent.graph import financial_rag_app
from ingestion.parser import document_parser
from ingestion.table_extractor import table_extractor
from ingestion.chunker import financial_chunker
from ingestion.tier1_loader import tier1_loader
from kg.cross_reference import cross_reference_linker

st.set_page_config(
    page_title="Financial RAG | Hybrid Vector-Graph",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State Initialization ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_history" not in st.session_state:
    st.session_state.agent_history = []


def get_graph_stats():
    """Fetch current node and edge counts from Neo4j."""
    try:
        query = """
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
        records = neo4j_client.execute_query(query)
        if records:
            return records[0]
    except Exception:
        pass
    return {"docs": 0, "chunks": 0, "tables": 0, "rels": 0}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 Financial Graph RAG")
    st.caption("Closed-world Hybrid Vector-Graph Analysis")

    st.divider()
    st.subheader("🖥️ System Status")

    # Neo4j Health Check
    try:
        neo_info = neo4j_client.check_connection()
        st.success(f"**Neo4j:** Connected ({neo_info['server_agent']})")
        if neo_info.get("apoc_installed"):
            st.caption("APOC Core: Enabled ✅")
    except Exception as e:
        st.error(f"**Neo4j:** Disconnected ({e})")

    # Model Settings
    st.markdown(f"**LLM:** `{settings.OLLAMA_LLM_MODEL}`")
    st.markdown(f"**Embeddings:** `{settings.OLLAMA_EMBED_MODEL}` ({settings.EMBEDDING_DIM}d)")
    st.markdown(f"**VLM:** `{settings.OLLAMA_VLM_MODEL}`")

    st.divider()
    st.subheader("📊 Graph Database Metrics")
    stats = get_graph_stats()
    col1, col2 = st.columns(2)
    col1.metric("Documents", stats.get("docs", 0))
    col1.metric("Chunks", stats.get("chunks", 0))
    col2.metric("Tables", stats.get("tables", 0))
    col2.metric("Edges", stats.get("rels", 0))

    st.divider()
    st.subheader("📑 Document Ingestion")
    pdf_files = list(settings.DATA_DIR.glob("*.pdf"))
    pdf_names = [f.name for f in pdf_files]

    if pdf_names:
        selected_pdf = st.selectbox("Select PDF to Ingest", pdf_names)
        if st.button("🚀 Ingest / Re-index", use_container_width=True):
            target_path = settings.DATA_DIR / selected_pdf
            with st.status(f"Ingesting {selected_pdf}...", expanded=True) as status:
                st.write("1. Parsing document structure & layout...")
                doc = document_parser.parse_pdf(target_path)
                
                st.write("2. Isolating tables & extracting image crops...")
                tables = table_extractor.process_tables(doc, doc_name=target_path.stem)
                
                st.write("3. Hierarchical hybrid chunking...")
                chunks = financial_chunker.chunk_document(doc, doc_name=target_path.stem, parsed_tables=tables)
                
                st.write("4. Generating embeddings & loading Tier 1 graph into Neo4j...")
                schema_manager.initialize_schema()
                tier1_loader.load_chunks(chunks=chunks, doc_name=target_path.stem, parsed_tables=tables)
                
                st.write("5. Linking internal statutory citations ([:REFERENCES])...")
                cross_reference_linker.link_document_citations(doc_name=target_path.stem)

                status.update(label=f"✅ Successfully indexed {selected_pdf}!", state="complete", expanded=False)
                st.rerun()

    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent_history = []
        st.rerun()


# ── Main Chat Area ────────────────────────────────────────────────────────────
st.title("💬 Financial Report Assistant")
st.markdown(
    "Query Vanguard annual reports, ETFs performance summaries, and Product Disclosure Statements (PDS) "
    "with strict **closed-world grounded answers**, **bracketed citations**, and **real-time graph traversal**."
)

# Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Display metadata expanders if stored
        if msg.get("chunks"):
            with st.expander("🔍 Retrieved Evidence & Vector Scores"):
                for c in msg["chunks"]:
                    st.markdown(f"**[{c.get('chunk_id')}]** — Score: `{c.get('vector_score', 0):.4f}` | Page: `{c.get('page_numbers')}`")
                    st.text(c.get("text", "")[:300] + "...")
        
        if msg.get("facts"):
            with st.expander("🕸️ Traversed Graph Relationships"):
                for f in msg["facts"]:
                    st.markdown(f"- {f}")

# User Input
if prompt := st.chat_input("Ask a question (e.g. 'What is the 1-year return for VAS?', 'What does Note 4 report?')..."):
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.agent_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Execute LangGraph Pipeline
    with st.chat_message("assistant"):
        with st.spinner("Traversing knowledge graph and retrieving evidence..."):
            initial_state = {
                "messages": st.session_state.agent_history,
                "user_query": prompt,
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

            final_state = financial_rag_app.invoke(initial_state)
            final_text = final_state.get("final_answer", "")
            reranked = final_state.get("reranked_chunks", [])
            route = final_state.get("route", "")

            # Display final answer
            st.markdown(final_text)

            # Extract chunk details and facts for history
            chunk_details = []
            traversed_facts = []
            if reranked:
                with st.expander("🔍 Retrieved Evidence & Vector Scores"):
                    for c in reranked:
                        c_dict = {
                            "chunk_id": c.chunk_id,
                            "vector_score": c.vector_score,
                            "page_numbers": c.page_numbers,
                            "text": c.text,
                        }
                        chunk_details.append(c_dict)
                        st.markdown(f"**[{c.chunk_id}]** — Vector Similarity: `{c.vector_score:.4f}` | Pages: `{c.page_numbers}`")
                        st.caption(f"Section: {c.section_header}")
                        st.text(c.text[:400] + ("..." if len(c.text) > 400 else ""))

                        for fact in c.traversed_graph_facts:
                            if fact not in traversed_facts:
                                traversed_facts.append(fact)

                if traversed_facts:
                    with st.expander("🕸️ Traversed Graph Relationships"):
                        for fact in traversed_facts:
                            st.markdown(f"- {fact}")

            # Store assistant response in history
            assistant_msg = {
                "role": "assistant",
                "content": final_text,
                "chunks": chunk_details,
                "facts": traversed_facts,
            }
            st.session_state.messages.append(assistant_msg)
            st.session_state.agent_history.append({"role": "assistant", "content": final_text})
