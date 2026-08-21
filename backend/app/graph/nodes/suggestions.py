"""
suggestions.py — Async Follow-up Query Suggestion Node
======================================================
Previously used a synchronous `llm.invoke()` call which blocked the entire
asyncio event loop for 5-10 seconds.  This version uses `await llm.ainvoke()`
and a module-level LLM singleton to eliminate both the blocking call and
per-request object instantiation overhead.
"""

from __future__ import annotations

import logging
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import settings, get_chat_model
from app.graph.state import AgentState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Pydantic schema for structured output
# ---------------------------------------------------------------------------

class SuggestionsSchema(BaseModel):
    suggested_queries: List[str] = Field(
        description="A list of 2 to 3 relevant follow-up questions for the user.",
        min_length=2,
        max_length=3,
    )


# ---------------------------------------------------------------------------
# 2. Module-level LLM singleton with fallback resilience
# ---------------------------------------------------------------------------

_suggestion_llm = get_chat_model(
    model="openai/gpt-4o-mini",
    temperature=0.5,
    max_tokens=512,  # Cap tokens to avoid large upstream reservation on OpenRouter
)

_structured_suggestion_llm = _suggestion_llm.with_structured_output(SuggestionsSchema)

# ---------------------------------------------------------------------------
# 3. Prompt template
# ---------------------------------------------------------------------------

_SUGGESTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are an intelligent conversational suggestion assistant. "
            "Given the user's initial query and the system's final answer, "
            "generate 2 to 3 concise, highly relevant follow-up queries "
            "that the user might want to ask next."
        ),
    ),
    ("human", "User Query: {query}\n\nFinal Answer:\n{answer}"),
])


# ---------------------------------------------------------------------------
# 4. Async LangGraph node
# ---------------------------------------------------------------------------

async def suggestion_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: Generates follow-up query suggestions based on the query
    and the current response in state.

    ASYNC — uses `ainvoke` so it never blocks the event loop.
    Falls back to an empty list on any error so it never breaks the pipeline.
    """
    user_query = state.get("user_query", "")
    final_answer = state.get("final_answer", "")

    print("--- [SUGGESTION NODE] Generating follow-up queries (async) ---")
    logger.info("[SUGGESTION NODE] Generating suggestions for query='%.80s'", user_query)

    suggestions: List[str] = []

    try:
        formatted_messages = _SUGGESTION_PROMPT.format_messages(
            query=user_query,
            answer=final_answer,
        )
        # ✅ Non-blocking: uses ainvoke instead of invoke
        response: SuggestionsSchema = await _structured_suggestion_llm.ainvoke(
            formatted_messages
        )

        if response and hasattr(response, "suggested_queries"):
            suggestions = response.suggested_queries

        print(
            f"--- [SUGGESTION NODE] Generated {len(suggestions)} suggested queries ---"
        )

    except Exception as exc:
        logger.warning("[SUGGESTION NODE] Failed to generate suggestions: %s", exc)
        print(f"--- [SUGGESTION NODE WARNING] Failed: {exc} — returning empty list ---")
        suggestions = []

    return {**state, "suggested_queries": suggestions}