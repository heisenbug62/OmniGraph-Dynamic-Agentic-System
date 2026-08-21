from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    """
    Central clipboard (state schema) passed between LangGraph nodes.
    """
    user_query: str                  # Question from the user
    persona: str                     # Selected role (e.g., Financial Analyst)
    persona_prompt: str              # System prompt for the active role
    selected_llm: str                # Chosen model (e.g., gpt-4o-mini)

    # Multi-turn conversation history injected from the frontend each request.
    # Each entry: {"role": "user" | "assistant", "content": "..."}
    # Capped at HISTORY_WINDOW turns before being stored in state (see main.py).
    chat_history: List[Dict[str, str]]

    # Tunable generation parameters (set by tune_pipeline.py grid search;
    # fall back to app.config.settings defaults if absent)
    top_k: Optional[int]             # Number of chunks to retrieve from Pinecone
    temperature: Optional[float]     # LLM sampling temperature for final answer

    # Router Node Output
    route_target: Optional[str]      # "doc", "db", "math", or "general"

    # Node Outputs (filled as the query travels)
    retrieved_docs: List[Dict[Any, Any]]  # Matches from Pinecone + metadata
    db_results: Optional[Any]             # Raw SQL query results
    math_results: Optional[Any]           # Output from Python calculations

    # Final Output
    final_answer: str                # Answer sent to the user
    source_metadata: Dict[str, Any]  # Page numbers, citations, screenshot paths
    suggested_queries: List[str]     # Recommended follow-up queries