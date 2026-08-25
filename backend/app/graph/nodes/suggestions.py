"""
suggestions.py — Async Follow-up Query Suggestion Node
======================================================
Previously used a synchronous `llm.invoke()` call which blocked the entire
asyncio event loop for 5-10 seconds.  This version uses `await llm.ainvoke()`
and a module-level LLM singleton to eliminate both the blocking call and
per-request object instantiation overhead.

Grounding fix: suggestions are now generated using the actual retrieved
document chunks (state["retrieved_docs"]), not just the query/answer text.
Without this, the LLM would suggest plausible-sounding follow-up questions
based on the general topic of the document (e.g. "what are the key
financial figures") even when that information was never actually
retrieved/present in the source content — producing suggestions the system
then couldn't answer.
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
            "Given the user's initial query, the system's final answer, and the "
            "retrieved source context the answer was based on, generate 2 to 3 "
            "concise, highly relevant follow-up queries.\n\n"
            "CRITICAL: Only suggest questions that can plausibly be answered using "
            "the retrieved context provided below. Do NOT suggest questions about "
            "topics, figures, or details that are not present in the context, even "
            "if they seem like a natural follow-up to the general subject matter. "
            "If the context is sparse or doesn't support additional follow-ups, "
            "suggest broader questions about what IS covered in the context instead."
        ),
    ),
    (
        "human",
        "User Query: {query}\n\nFinal Answer:\n{answer}\n\nRetrieved Context:\n{context}",
    ),
])


# ---------------------------------------------------------------------------
# 4. Async LangGraph node
# ---------------------------------------------------------------------------
async def suggestion_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: Generates follow-up query suggestions based on the query,
    the current response, and the retrieved document context in state.

    ASYNC — uses `ainvoke` so it never blocks the event loop.
    Falls back to an empty list on any error so it never breaks the pipeline.
    """
    user_query = state.get("user_query", "")
    final_answer = state.get("final_answer", "")
    retrieved_docs = state.get("retrieved_docs", []) or []

    # Build a compact context string from the actual retrieved chunks so
    # suggestions are grounded in what's genuinely retrievable, not just
    # inferred from the topic of the query/answer.
    context_str = "\n\n".join(
        doc.get("chunk_text", "") for doc in retrieved_docs if doc.get("chunk_text")
    ) or "No document context was retrieved for this query."

    print("--- [SUGGESTION NODE] Generating follow-up queries (async) ---")
    logger.info("[SUGGESTION NODE] Generating suggestions for query='%.80s'", user_query)

    suggestions: List[str] = []
    try:
        formatted_messages = _SUGGESTION_PROMPT.format_messages(
            query=user_query,
            answer=final_answer,
            context=context_str,
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