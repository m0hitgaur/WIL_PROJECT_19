# RAG System Architecture Plan: Financial Document Analysis

This document outlines the complete architectural design for a closed-world, hybrid Vector-Graph RAG system tailored for querying a small dataset (approx. 6 PDFs) of highly structured financial reports. The system operates entirely on local open-source models with a hardware constraint of 26B parameters.

## 1. System Overview & Model Stack

* **Document Parsing:** Docling (Hybrid Mode)
* **Vision-Language Model (VLM):** Qwen2.5-VL-7B-Instruct or DeepSeek-VL2 (Used exclusively for complex financial tables).
* **Embedding Model:** Qwen3-embedding or BGE-M3 (for semantic vector search).
* **Graph Extraction & Core Reasoning:** Qwen3-14B or gpt-oss-20b.
* **Re-ranker (Cross-Encoder):** bge-reranker.
* **Database:** Neo4j (Acting as BOTH the Vector Store and Graph Database).
* **Orchestration:** LangGraph (Stateful Agentic Routing).

## 2. Ingestion Pipeline (Asynchronous)

The ingestion phase is a heavy, multi-step pipeline designed to construct a deeply connected Document Structure Graph and Knowledge Graph before the user ever asks a query.

### 2.1 Extraction & Parsing

1. **Structural Parsing:** Run the PDFs through Docling to extract standard text and markdown headers (`#`, `##`).
2. **Table Isolation:** Use Docling-parse to set precise bounding boxes around tables.
3. **VLM Table Transcription:** Pass the isolated table image crops to the lightweight VLM (Qwen2.5-VL-7B). The VLM is prompted to strictly output structured Markdown or JSON, preserving the dense semantic meaning of financial grids.

### 2.2 Chunking

* **Method:** Docling's native hybrid chunker.
* **Why:** It respects hierarchical document boundaries established by Markdown headers. Crucially, it repeats table headers at the top of a chunk if a large financial table spans multiple token windows.

### 2.3 Database Initialization & Graph Construction (Neo4j)

This system utilizes a three-tiered graph approach to solve the "cross-reference problem." As demonstrated in standard Neo4j GenAI architectures, embeddings are stored directly on the nodes, allowing a single query to handle both semantic search and topological traversal.

1. **Tier 1: Document Structure & Vector Indexing (Deterministic)**

   * **Embeddings:** As chunks are created, pass their text through `Qwen3-embedding` to generate a vector array (e.g., dimension size of 1024 or 384 depending on the model).
   * **Node Creation:** A Python script inserts the chunks into Neo4j without an LLM. The vector array is stored as a property on the node (e.g., `CREATE (c:Chunk {text: "...", chunk_id: "105", embedding: [0.01, -0.05, ...]})`).
   * **Edges:** Map structural relationships using `HAS_CHILD` (linking sections to chunks) and `NEXT` (linking sequential chunks).
   * **Vector Indexing (The Bridge):** Execute a Cypher command to create a Native Vector Index on the `Chunk` label and `embedding` property (`CREATE VECTOR INDEX chunk_embeddings FOR (n:Chunk) ON (n.embedding)`). **This is critical:** It allows the vector similarity search to return actual graph nodes as the starting point for entity traversal, exactly like the SEC 10-K demo.

2. **Tier 2: Knowledge Extraction (LLM Graph Transformer)**

   * Use LangChain's `LLMGraphTransformer` powered by Qwen3-14B.
   * Process the chunks to extract specific entities and merge them into the Neo4j graph.
   * *Constraint:* Restrict the LLM to a strict ontology (Allowed Nodes: `Company`, `Financial_Metric`, `Subsidiary`, `Table` | Allowed Relationships: `OWNS`, `REPORTED`, `CONTAINS_METRIC`) to prevent hallucinated, noisy graph structures.

3. **Tier 3: Graph Enrichment (Two-Pass Cross-Reference)**

   * *Pass 1:* An offline loop passes every chunk to the LLM to identify internal citations (e.g., "As detailed in Note 4").
   * *Pass 2:* A vector search finds the chunk representing "Note 4".
   * *Pass 3:* A Cypher query creates a deterministic `[:REFERENCES]` edge between the referencing chunk and the target chunk, allowing instant traversal during live queries.

## 3. Retrieval & Chat Pipeline (Real-Time LangGraph)

The real-time chat is governed by a stateful LangGraph agent that actively prevents context overflow, handles multi-part questions, and enforces strict compliance.

### 3.1 The Router / Planner Node

1. **Query Condenser:** A lightweight LLM call rewrites the user's raw prompt using the chat history to create a semantically complete standalone query.
2. **Task Decomposition:** The Router evaluates the condensed query.
   * If it's conversational, it routes to the final LLM.
   * If it's a single task, it routes to Hybrid Search.
   * If it's a multi-task query, the Router breaks it into sub-queries for parallel fan-out.

### 3.2 Hybrid Retrieval (Vector-to-Graph Traversal)

This is where the unified Neo4j database shines. Retrieval starts with a semantic vector match to find the most relevant chunks, then traverses outward along the explicit graph edges to pull connected facts (like Companies or linked Tables).

1. **The Vector Entry Point:** Embed the user's condensed query using the same `Qwen3-embedding` model.
2. **The Unified Cypher Search:** Execute a single Cypher query that performs both steps natively:
   * *Step A (Vector Search):* `CALL db.index.vector.queryNodes('chunk_embeddings', 5, $query_embedding) YIELD node AS start_chunk, score` -> *This finds the most semantically relevant chunks based on the vector.*
   * *Step B (Graph Traversal):* `MATCH (start_chunk)-[:REFERENCES|HAS_CHILD|NEXT|CONTAINS_METRIC|REPORTED]-(related_node)` 
   * *Step C (Return):* `RETURN start_chunk.text, related_node.name, score` -> *This pulls in the linked tables, parent sections, and referenced notes all in one database hit.*
3. **Graph Translation:** Raw JSON from the `related_node` traversals is translated into plain English sentences by a fast utility function (e.g., "Chunk 12 References Table 4 containing debt data") to save tokens.
4. **Re-Ranking (Crucial for Context Limits):** All retrieved chunks (the initial vector hits + their traversed graph context) are pooled and scored against the condensed query by the **bge-reranker** (Cross-Encoder). Only the top 3-4 highest-scoring chunks are passed into the final prompt context.

## 4. Answer Generation & Compliance Safeguards

To ensure a strict, closed-world system with no hallucinations or missing citations, the final output must pass through specific LangGraph evaluator nodes.

### 4.1 Generation & Guardrails

1. **Draft Generator:** The LLM receives the condensed query, the re-ranked chunks, and a strict system prompt: *"You must append the exact `[Chunk_ID]` at the end of every factual claim. Do not use outside knowledge."*
2. **Citation Checker (Deterministic):** A Python Regex node scans the drafted response. If it detects a factual claim missing a bracketed `[Chunk_ID]`, it flags the state as `Fail` and loops back to the Draft Generator.
3. **Hallucination Grader (Self-Reflection):** The LLM reviews the draft against the retrieved context. If any facts in the draft cannot be proven by the provided context chunks, it returns `Fail` and forces a rewrite.
4. **Disclaimer Injector:** Before delivering the payload to the UI, a deterministic function appends: *"Disclaimer: This information is extracted from provided documents and does not constitute financial advice."*

## 5. Continuous Graph Refinement (Topological Synthesis)

The RAG system improves its own graph dynamically over time based on user interactions.

* **The Trigger:** If a user asks a complex relational question and the initial Cypher query returns empty (missing edge), but the fallback Vector Search successfully finds the text chunk containing the answer.
* **The Async Update:** While the final answer is streaming to the user, a parallel, asynchronous LangGraph node takes the successful text chunk and the user's question, extracts the missing relationship, and writes an `UPDATE` Cypher statement back to Neo4j.