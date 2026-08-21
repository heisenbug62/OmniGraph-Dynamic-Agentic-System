from app.graph.state import AgentState
from app.utils.prompt_loader import get_persona_prompt
from app.config import llm  # reuse your existing LLM client

VALID_PERSONAS = ["Financial Analyst", "Legal Advisor", "General Assistant"]


def _format_history_snippet(chat_history: list, n: int = 6) -> str:
    """Return the last `n` turns as a compact dialogue string."""
    if not chat_history:
        return ""
    recent = chat_history[-n:]
    lines = []
    for turn in recent:
        role = "User" if turn.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {turn.get('content', '')}")
    return "\n".join(lines)


def classify_persona(user_query: str, chat_history: list | None = None) -> str:
    """
    Uses the LLM to classify user intent into one of the defined personas.
    Only called when the user has selected 'Auto'.
    Includes the last 6 turns so follow-up questions are classified correctly.
    """
    history_block = _format_history_snippet(chat_history or [], n=6)
    history_section = (
        f"\nConversation so far (for context only):\n{history_block}\n"
        if history_block else ""
    )

    classification_prompt = (
        "Classify the following user query into exactly one category. "
        "Respond with ONLY the category name, nothing else.\n\n"
        "Categories:\n"
        "- Financial Analyst: math, stock data, calculations, ratios, financial trends\n"
        "- Legal Advisor: compliance, regulations, legal frameworks, contracts, disclosure requirements, laws, standards like IAS/IFRS\n"
        "- General Assistant: mixed intent, general questions, anything unclear\n"
        f"{history_section}"
        f"\nLatest Query: {user_query}\n\n"
        "Category:"
    )
    response = llm.invoke(classification_prompt)
    result = str(response.content).strip()

    # Guard against the LLM returning something outside the valid set
    for persona in VALID_PERSONAS:
        if persona.lower() in result.lower():
            return persona
    return "General Assistant"  # safe fallback


def persona_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: Resolves the active persona (classifying intent if 'Auto'
    was selected), then loads the corresponding system prompt from app/prompts/.
    """
    selected_persona = state.get("persona", "General Assistant")
    user_query = state.get("user_query", "")
    chat_history = state.get("chat_history") or []

    if selected_persona == "Auto":
        selected_persona = classify_persona(user_query, chat_history)
        print(f"--- [PERSONA NODE] Auto-classified query as: '{selected_persona}' ---")

    prompt_text = get_persona_prompt(selected_persona)

    return {
        **state,
        "persona": selected_persona,   # now holds the RESOLVED persona, not "Auto"
        "persona_prompt": prompt_text,
    }