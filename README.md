# Agentic Assistant

An advanced, multi-agent AI system built with FastAPI, LangGraph, Pinecone, and React. It dynamically orchestrates user queries across specialized modules including Vector RAG for document analysis, Text-to-SQL database querying, and a secure Python execution engine for math and data analysis.

---

## 🌟 What It Does

* **Smart Router**: Intelligently analyzes user query intent and automatically delegates execution to the optimal specialist agent.
* **Vector RAG**: Upload, chunk, and embed PDF documents into Pinecone to perform context-aware document analysis with source metadata retrieval.
* **Text-to-SQL Engine**: Safely translates natural language instructions into structured SQL queries against your database.
* **Python Math Engine**: Dynamically converts mathematical or analytical requests into executable Python code running in a secured runtime environment.
* **Live Graph Tracer (`TracePanel.jsx`)**: A real-time WebSocket-powered observability panel that streams LangGraph state transitions, node execution steps, and workflow success status directly into the UI.

---

## ⚙️ Prerequisites & System Requirements

Before you begin, ensure you have the following installed and configured:

* **Python** (version 3.10 or higher)
* **Node.js & npm** (for building and running the React frontend)
* **API Keys**: Active API credentials for OpenAI or OpenRouter, and Pinecone.

---

## 🚀 Installation & Setup Guide

### 1. Backend Setup (FastAPI & LangGraph)

Clone the repository and set up your Python virtual environment:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in your root or backend directory with your required environment variables:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
MODEL_NAME=anthropic/claude-3.5-sonnet
```

Start the FastAPI development server with Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup (React, Vite & Tailwind CSS)

Open a new terminal window, navigate to the frontend directory, install dependencies, and run the development server:

```bash
cd frontend
npm install
npm run dev
```

---

## 🖥️ How to Use

Open your web browser and navigate to:

`http://localhost:5173`

Choose an active agent persona from the header dropdown menu (or leave it on **Auto (Smart Router)** for automatic backend intent detection).

Put the document in backend/data/pdf and run the ingestion pineline. The document will be stored in the pinecone in for of vectors.

Type your questions, data analysis prompts, or math problems into the chat bar, and watch real-time state execution and graph traces update live on your interface.
