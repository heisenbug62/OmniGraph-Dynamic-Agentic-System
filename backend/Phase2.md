# Phase 2: Knowledge Base Ingestion & Document RAG Node

## 1. Overview
Phase 2 builds the document ingestion and RAG retrieval pipeline. It processes uploaded PDFs, renders page snapshot images for visual proof, creates semantic text chunks, upserts vector embeddings to Pinecone, and retrieves matching chunks with page citations.

---

## 2. Architecture Flow

[Uploaded PDF Document]
        │
        ▼
[PDF Processor Service] ──► Renders page snapshots (data/screenshots/)
        │    & extracts ~500-char semantic chunks
        ▼
[Vector Store Service] ──► Embeds text (text-embedding-3-small)
        │    & upserts 1536-dim vectors to Pinecone
        ▼
[Doc RAG Node] ──► Performs similarity search (top_k=3)
& attaches page citations + snapshot paths

---

## 3. Core Components & Logic

### A. PDF Processor (`app/services/pdf_processor.py`)
* Renders each PDF page into a high-DPI image saved to `data/screenshots/` for visual verification.
* Uses `RecursiveCharacterTextSplitter` (`chunk_size=500`, `chunk_overlap=100`) to split pages into granular semantic chunks.
* Binds each chunk to metadata: `document_title`, `page_number`, `chunk_index`, and `screenshot_path`.

### B. Vector Store Service (`app/services/vector_store.py`)
* Manages the serverless Pinecone index `agentic-docs` (dimension: 1536, metric: cosine).
* Generates embeddings via `OpenAIEmbeddings` using `text-embedding-3-small`.
* Performs cosine similarity search to retrieve top $k$ relevant context chunks.

### C. Doc RAG Node (`app/graph/nodes/doc_rag.py`)
* LangGraph node that reads `user_query` from `AgentState`.
* Calls `vector_store_service.similarity_search()`.
* Populates `state["retrieved_docs"]` with retrieved context chunks, similarity scores, and page snapshot paths.

---

## 4. Verification

Running `python test_phase2.py` verified:
1. Processing a multi-page PDF generated granular chunks (68 chunks across 9 pages) and rendered page PNG snapshots in `data/screenshots/`.
2. Successfully upserted all chunks into Pinecone index `agentic-docs`.
3. The `DocNode` returned relevant matches with exact page citations (`Page 5.0`, `Page 6.0`) and screenshot paths (`data/screenshots/sample_doc_page_6.png`).