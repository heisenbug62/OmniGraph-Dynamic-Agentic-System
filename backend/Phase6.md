# Phase 6: Production Deployment, Monitoring, and System Documentation

This document provides a comprehensive blueprint for deploying, monitoring, and documenting the production environment of the Agentic Assistant platform.

---

## 1. Production Architecture & Deployment Strategy

* **Frontend Hosting (React / Vite)**: The frontend is built into optimized static assets (`dist/`) using Vite and can be hosted on edge services like Vercel, Netlify, or served directly via the FastAPI static files mounting layer.
* **Backend Application Server (FastAPI)**: Hosted on containerized infrastructure (such as Docker on AWS ECS, Google Cloud Run, or a dedicated Linux VPS). The application runs on an ASGI server like Uvicorn with multiple worker processes managed via Gunicorn.
* **Vector Database (Pinecone)**: Managed cloud vector storage handling dense embedding indices, namespace partitioning, and cosine similarity queries for high-throughput RAG.

---

## 2. Environment Variables & Configuration

Create a secure `.env` file on your production server. Ensure the following keys are properly populated:

```env
# LLM Provider Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
MODEL_NAME=anthropic/claude-3.5-sonnet

# Vector Database Configuration
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=us-east-1

# Server Settings
PORT=8000
HOST=0.0.0.0

---

## 3. Monitoring, Observability, and Traceability
Live Graph Tracer (TracePanel.jsx): Connects to the backend via secure WebSockets (wss://your-domain/ws/{client_id}) to stream LangGraph state transitions, active node execution, and workflow completion in real time.

Structured Logging: Backend nodes output detailed JSON logs capturing token usage, latency per node (doc_rag_node, db_sql_node, math_exec_node), and execution errors for debugging.

Health Check Endpoint: A dedicated /health route is available for load balancers and container orchestrators to monitor uptime and readiness.