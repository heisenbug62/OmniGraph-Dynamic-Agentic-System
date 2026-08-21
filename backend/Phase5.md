# Phase 5: Production API, Multi-Modal Streaming, & LLM Evaluation

## 1. Overview
Phase 5 transitions the dynamic multi-agent system from a local command-line state machine into a production-ready, high-concurrency backend built with **FastAPI**, **Async WebSockets**, **Server-Sent Events (SSE)**, and an **LLM-as-a-Judge Evaluation Pipeline**. It introduces:
1. **Multi-Transport API Gateway**: Delivers synchronous REST execution, real-time token streaming via SSE, and asynchronous state execution tracing over WebSockets.
2. **Table-Aware Vector Ingestion**: Enhances Pinecone PDF ingestion by injecting structural page and document headers into text chunks prior to embedding.
3. **Automated LLM-as-a-Judge Evaluation**: Implements an automated quality control framework (`eval_judge.py`) using `gpt-4o-mini` to grade outputs on faithfulness, relevance, and citation precision.

---

## 2. Production API Architecture Flow

                          [ Client Application / UI ]
                           /          |                \
             POST /api/chat     POST /api/chat/stream    WS /ws/trace/{client_id}
             (Sync REST)        (SSE Token Stream)       (Live Tracing Channel)
                  │                   │                          │
                  ▼                   ▼                          ▼
          [ REST Controller ]  [ Event Generator ]      [ WebSocket Manager ]
                  │                   │                          │
                  └─────────┬─────────┴──────────────────────────┘
                            │
                            ▼
              [ LangGraph State Engine ]
            (Router -> Node -> Formatter)
                            │
             ┌──────────────┴──────────────┐
             │                             │
             ▼                             ▼
   [ Pinecone Vector Store ]    [ Static Asset Server ]
   (Table Chunks & Metadata)    (/screenshots Static Mount)

---

## 3. Core Components Implemented

### A. Production API Endpoints & Transport Layer (`app/main.py`)
* **REST Endpoint (`POST /api/chat`)**: Executes `agent_app.invoke` asynchronously in a background thread and returns validated `ChatResponse` objects.
* **SSE Streaming Endpoint (`POST /api/chat/stream`)**: Streams final generated text in token chunks via `text/event-stream` followed by a structured JSON metadata block containing citations, persona, and suggested queries.
* **WebSocket Live Tracing (`WS /ws/trace/{client_id}`)**: Emits live node execution events (`workflow_start`, `router`, `doc_rag`, `workflow_complete`) managed by `ConnectionManager`.
* **Static Assets Server (`/screenshots`)**: Mounts screenshot asset directories to serve PDF page preview images for citations.

### B. Table-Aware Ingestion Pipeline (`ingest_pdf.py`)
* Prepends explicit structural page context (`[Document: filename | Page Number: X]`) to extracted PDF text to preserve document structure.
* Indexes text into Pinecone using deterministic record keys (`{filename}_p{page_num}_c{chunk_idx}`) for idempotent upserts.
* Supports dual-provider embedding routes via `OpenAIEmbeddings`, handling both official OpenAI endpoints and OpenRouter base URLs (`https://openrouter.ai/api/v1`).

### C. Automated LLM-as-a-Judge Evaluator (`eval_judge.py`)
* Evaluates system responses against ground-truth context across key quality metrics:
  * **Faithfulness / Groundedness**: Verifies if claims are strictly backed by retrieved documents.
  * **Answer Relevance**: Measures direct responsiveness to the user prompt.
  * **Citation Precision**: Validates page numbers and screenshot references.
* Employs structured JSON outputs to output numerical scores and diagnostic reasoning.

---

## 4. End-to-End Verification Results (`test_phase5.py`)

### Test Run 1: Standard REST Endpoint (`POST /api/chat`)
* **Query:** *"In the uploaded document, what was the Total Foreign Currency Financial Assets for 2019 compared to 2018?"*
* **Status:** `200 OK`
* **Persona Adapted:** `Financial Analyst`
* **Route Target:** `'doc'`
* **Retrieved Table Values:** **2019:** `81,888,828` thousand vs. **2018:** `76,871,204` thousand.
* **Citations & Metadata:**
  * **Page Numbers Cited:** `[2.0]`
  * **Screenshot Reference:** `['/screenshots/sample_doc_page_2.png']`

### Test Run 2: SSE Streaming Endpoint (`POST /api/chat/stream`)
* **Query:** *"According to the User Guidance in the PDF, how does IAS 1 allow central banks to present assets?"*
* **Status:** `200 OK`
* **Transport:** `text/event-stream`
* **Token Streaming:** Successfully streamed answer content sequentially, followed by the final `type: metadata` payload containing route target and citation metadata.

### Test Run 3: WebSocket Live Tracing (`WS /ws/trace/test_trace_client`)
* **Query:** *"What is Cillian Murphy known for?"*
* **Status:** `101 Switching Protocols` (Connection Established)
* **Live Trace Events Received:**
  * `workflow_start` (status: `running`)
  * `workflow_complete` (status: `success`, route: `'general'`, persona: `'General Assistant'`)
* **Execution Status:** All client message exchanges and graph trace events completed successfully.