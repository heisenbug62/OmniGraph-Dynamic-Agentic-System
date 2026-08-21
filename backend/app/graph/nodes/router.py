from app.graph.state import AgentState
from app.config import llm


def _format_history_snippet(chat_history: list, n: int = 6) -> str:
    """
    Return the last `n` turns formatted as a compact dialogue block.
    Used to give the router/persona classifiers conversational context.
    """
    if not chat_history:
        return ""
    recent = chat_history[-n:]
    lines = []
    for turn in recent:
        role = "User" if turn.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {turn.get('content', '')}")
    return "\n".join(lines)


def router_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: Classifies the user request (with conversational context)
    into one of:
    - 'doc'     (document RAG)
    - 'db'      (database queries)
    - 'math'    (mathematical calculations / python execution)
    - 'general' (general conversation)
    """
    user_query = state.get("user_query", "") or state.get("question", "")
    chat_history = state.get("chat_history") or []

    history_block = _format_history_snippet(chat_history, n=6)
    history_section = (
        f"\n\nConversation so far (use for context only):\n{history_block}\n"
        if history_block else ""
    )

    prompt = f"""You are an intelligent query routing agent. Classify the LATEST user message into EXACTLY ONE category.

Categories:
- 'doc': Asking about documents, PDFs, policies, legal clauses, or contracts.
- 'db': Asking for structured sales records, database rows, quarterly revenue figures.
- 'math': Asking for arithmetic, equations, statistical calculations, or python data analysis.
- 'general': Greetings, casual questions, or general knowledge.

Respond ONLY with one word: 'doc', 'db', 'math', or 'general'.
{history_section}
Latest User Message: {user_query}
"""
    response = llm.invoke(prompt)
    raw_target = response.content.strip().lower()

    if "sql" in raw_target or "db" in raw_target:
        route_target = "db"
    elif "math" in raw_target or "calc" in raw_target:
        route_target = "math"
    elif "doc" in raw_target or "pdf" in raw_target:
        route_target = "doc"
    else:
        route_target = "general"

    print(f"--- [ROUTER NODE] Classified query as: '{route_target}' ---")

    return {
        **state,
        "route_target": route_target
    }