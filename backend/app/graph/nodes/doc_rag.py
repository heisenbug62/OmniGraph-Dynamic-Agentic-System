"""
doc_rag.py — Document RAG Node
================================
Optimized: this node now ONLY performs vector retrieval (embedding + Pinecone
similarity search) and normalises the returned chunks for downstream use.

All LLM synthesis is handled exclusively by answer_formatter_node, which runs
concurrently with suggestion generation. Removing the intermediate llm.ainvoke()
call here eliminates one full LLM round-trip (~3-5 s) from the doc-RAG path.
"""
from app.config import settings
from app.services.vector_store import vector_store_service


async def doc_rag_node(state: dict) -> dict:
    """
    LangGraph Node: Vector retrieval only — no LLM call.

    1. Embeds the user query and runs an async Pinecone similarity search.
    2. Normalises the returned chunks into the shape expected by answer_formatter_node:
       [{"metadata": {...}, "chunk_text": "..."}]
    3. Returns immediately so answer_formatter_node can synthesise the final
       answer (concurrently with follow-up suggestions).

    Latency: ~200–400 ms (embedding API + Pinecone query), down from ~4–8 s
    when an additional LLM generation was performed in this node.
    """
    # Support both 'question' and 'user_query' state keys safely
    query = state.get("question", "") or state.get("user_query", "")

    # Read tunable top_k from state (set by grid search); fall back to config default
    top_k = state.get("top_k") or settings.DEFAULT_TOP_K

    # Async Pinecone similarity search — event loop stays free during network I/O
    docs = await vector_store_service.asimilarity_search(query, k=top_k)

    print(f"--- [DOC RAG NODE] Query: '{query}' | top_k={top_k} | Retrieved {len(docs)} chunks ---")
    if docs:
        print(f"--- [DOC RAG NODE] Top match metadata: {docs[0].get('metadata', {})} ---")
    else:
        print("--- [DOC RAG NODE WARNING] No chunks found. Check Pinecone index / namespace. ---")

    # Normalise to the shape answer_formatter_node expects
    normalized_docs = [
        {
            "metadata": doc.get("metadata", {}),
            "chunk_text": doc.get("text", ""),
        }
        for doc in docs
    ]

    # Return retrieved_docs to formatter — no LLM call here
    return {
        **state,
        "retrieved_docs": normalized_docs,
        "sources": [doc.get("metadata", {}) for doc in docs],
    }