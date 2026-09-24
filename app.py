"""
RAG Chat App — Streamlit GUI
Run: streamlit run rag_chat_app.py
"""

import os
import shutil
from operator import itemgetter
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="RAG Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── check imports up front so errors are visible ──────────────────────────────
try:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_ollama import OllamaEmbeddings, ChatOllama
    from langchain_chroma import Chroma
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False
    IMPORT_ERROR = str(e)

# ── session state ─────────────────────────────────────────────────────────────
if "messages"     not in st.session_state: st.session_state.messages     = []
if "chain"        not in st.session_state: st.session_state.chain        = None
if "index_ready"  not in st.session_state: st.session_state.index_ready  = False
if "doc_name"     not in st.session_state: st.session_state.doc_name     = None

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    st.subheader("📄 Upload PDF")
    uploaded_file = st.file_uploader("Drop a PDF here", type=["pdf"], label_visibility="collapsed")

    st.divider()
    st.subheader("🔧 Model settings")
    embed_model   = st.text_input("Embedding model", value="all-minilm")
    llm_model     = st.text_input("LLM model",        value="llama3.2:1b")
    temperature   = st.slider("Temperature", 0.0, 1.0, 0.0, 0.05)
    chunk_size    = st.number_input("Chunk size",    value=100, min_value=50,  max_value=2000, step=50)
    chunk_overlap = st.number_input("Chunk overlap", value=10,  min_value=0,   max_value=500,  step=10)
    k_results     = st.number_input("Top-k chunks",  value=2,   min_value=1,   max_value=20,   step=1)

    st.divider()
    build_btn = st.button("🔨 Build / Rebuild index", use_container_width=True)
    reset_btn = st.button("🗑️ Clear chat history",    use_container_width=True)
    st.divider()
    st.caption("Ollama + LangChain + Chroma")

if reset_btn:
    st.session_state.messages = []

# ── import error banner ───────────────────────────────────────────────────────
if not IMPORTS_OK:
    st.error(f"❌ Missing dependency: {IMPORT_ERROR}")
    st.code("pip install langchain langchain-community langchain-ollama langchain-chroma chromadb pypdf")
    st.stop()

# ── build index ───────────────────────────────────────────────────────────────
PERSIST_DIR = "./chroma_db"

def build_index(pdf_bytes, pdf_name, settings):
    tmp_path = Path(f"/tmp/{pdf_name}")
    tmp_path.write_bytes(pdf_bytes)

    with st.status("📖 Loading PDF…", expanded=True) as status:
        loader = PyPDFLoader(str(tmp_path))
        documents = loader.load()
        st.write(f"✅ Loaded **{len(documents)}** page(s)")

        status.update(label="✂️ Splitting into chunks…")
        splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", " ", ""],
            chunk_size=settings["chunk_size"],
            chunk_overlap=settings["chunk_overlap"],
        )
        chunks = splitter.split_documents(documents)
        st.write(f"✅ Created **{len(chunks)}** chunks")

        status.update(label="🧠 Embedding chunks…")
        embedding_model = OllamaEmbeddings(model=settings["embed_model"])

        if os.path.exists(PERSIST_DIR):
            shutil.rmtree(PERSIST_DIR)

        vector_store = Chroma(
            embedding_function=embedding_model,
            persist_directory=PERSIST_DIR,
        )

        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            vector_store.add_documents(batch)
            st.write(f"Embedded {i + len(batch)} / {len(chunks)} chunks…")

        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": settings["k_results"]},
        )

        status.update(label="⛓️ Building chain…")
        prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant. Use the context below to answer the question.
If the answer isn't in the context, say so.

Context:
{context}

Question:
{question}

Answer:""")

        llm = ChatOllama(model=settings["llm_model"], temperature=settings["temperature"])

        chain = (
            {
                "context": itemgetter("question") | retriever,
                "question": itemgetter("question"),
            }
            | prompt
            | llm
            | StrOutputParser()
        )

        st.session_state.chain      = chain
        st.session_state.index_ready = True
        st.session_state.doc_name   = pdf_name
        status.update(label="✅ Index ready!", state="complete", expanded=False)


if build_btn:
    if uploaded_file is None:
        st.sidebar.error("Please upload a PDF first.")
    else:
        try:
            build_index(
                uploaded_file.read(),
                uploaded_file.name,
                dict(
                    embed_model=embed_model,
                    llm_model=llm_model,
                    temperature=temperature,
                    chunk_size=int(chunk_size),
                    chunk_overlap=int(chunk_overlap),
                    k_results=int(k_results),
                )
            )
        except Exception as e:
            st.error(f"❌ Index build failed:\n\n{e}")

# ── main chat UI ──────────────────────────────────────────────────────────────
st.title("🤖 RAG Chat")

if st.session_state.doc_name:
    st.caption(f"Document: **{st.session_state.doc_name}**")
else:
    st.info("👈 Upload a PDF in the sidebar and click **Build / Rebuild index** to get started.")

# render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# chat input
if prompt_text := st.chat_input(
    "Ask something about your document…",
    disabled=not st.session_state.index_ready,
):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    with st.chat_message("user"):
        st.markdown(prompt_text)

    with st.chat_message("assistant"):
        try:
            response = st.write_stream(
                st.session_state.chain.stream({"question": prompt_text})
            )
        except Exception as e:
            response = f"❌ Error: {e}"
            st.error(response)

    st.session_state.messages.append({"role": "assistant", "content": response})