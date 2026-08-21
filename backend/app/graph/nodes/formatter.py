"""
formatter.py — Final Answer Formatter Node
==========================================
Combines the previously serial suggestion_node + answer_formatter_node into a
single node that fires both LLM calls concurrently via asyncio.gather().
This saves one full sequential round-trip (~4-6 s) per request.
"""
import os
import asyncio
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.graph.state import AgentState
from app.config import settings, get_chat_model

# ---------------------------------------------------------------------------
# Module-level LLM singleton with automatic resilience & fallback chain
# ---------------------------------------------------------------------------

_formatter_llm = get_chat_model(
    model=settings.MODEL_NAME,
    temperature=0.3,
    max_tokens=1000,
    streaming=True,   # ← enables on_chat_model_stream events for astream_events()
)

# ---------------------------------------------------------------------------
# Suggestion LLM singleton with structured output & fallbacks
# ---------------------------------------------------------------------------

class _SuggestionsSchema(BaseModel):
    suggested_queries: List[str] = Field(
        description="A list of 2 to 3 relevant follow-up questions for the user.",
        min_length=2,
        max_length=3,
    )

_suggestion_llm = get_chat_model(
    model="openai/gpt-4o-mini",
    temperature=0.5,
    max_tokens=256,
).with_structured_output(_SuggestionsSchema)

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

async def answer_formatter_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: Formats the final answer AND generates follow-up suggestions
    in parallel via asyncio.gather() — replacing the previous serial
    suggestion_node → answer_formatter_node chain and saving ~4-6 s per request.
    """
    user_query = state.get("user_query", "")
    persona = state.get("persona", "General Assistant")
    persona_prompt = state.get("persona_prompt", "You are a helpful and intelligent AI assistant.")

    retrieved_docs = state.get("retrieved_docs", []) or []
    db_results = state.get("db_results", None)
    math_results = state.get("math_results", None)
    # Keep any suggestions that may have been pre-populated (e.g. from state)
    existing_suggestions = state.get("suggested_queries", []) or []

    print(f"--- [ANSWER FORMATTER NODE] Formatting answer + suggestions in parallel | persona: '{persona}' ---")

    # ------------------------------------------------------------------
    # Build context for the formatter LLM
    # ------------------------------------------------------------------
    context_parts = []
    has_doc_evidence = False

    if retrieved_docs:
        has_doc_evidence = True
        doc_context = "### Document Information:\n"
        for idx, doc in enumerate(retrieved_docs, start=1):
            metadata = doc.get("metadata", {})
            page_no = metadata.get("page_number", "N/A")
            text = doc.get("chunk_text", "")
            doc_context += f"- [Page {page_no}]: {text}\n"
        context_parts.append(doc_context)

    if db_results and not db_results.get("error"):
        sql_context = "### SQL Database Results:\n"
        sql_context += f"Query: `{db_results.get('generated_sql')}`\n"
        sql_context += f"Data: {db_results.get('rows')}\n"
        context_parts.append(sql_context)

    if math_results and not math_results.get("error"):
        math_context = "### Calculation Results:\n"
        math_context += f"Result: {math_results.get('output')}\n"
        context_parts.append(math_context)

    full_context = "\n\n".join(context_parts) if context_parts else "No external documents or database records provided."

    system_instruction = (
        f"{persona_prompt}\n\n"
        "You are answering questions for the user. "
        "If specific document or database context is provided above, ground your response in it. "
        "If no document context is provided, answer the user's question directly and thoroughly using your general knowledge."
    )

    # ------------------------------------------------------------------
    # Build message list: SystemMessage + prior turns + current question
    # ------------------------------------------------------------------
    from langchain_core.messages import AIMessage

    # Keep at most the last 10 history entries (5 exchange pairs) to bound
    # token usage.  The frontend already trims to HISTORY_WINDOW but we apply
    # a hard cap here as a belt-and-suspenders measure.
    HISTORY_CAP = 10
    chat_history = state.get("chat_history") or []
    history_window = chat_history[-HISTORY_CAP:]

    history_messages = []
    for turn in history_window:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role == "user":
            history_messages.append(HumanMessage(content=content))
        else:
            history_messages.append(AIMessage(content=content))

    formatter_messages = (
        [SystemMessage(content=system_instruction)]
        + history_messages
        + [HumanMessage(content=f"Context:\n{full_context}\n\nUser Question: {user_query}")]
    )

    # ------------------------------------------------------------------
    # Build coroutines for both tasks
    # ------------------------------------------------------------------
    async def _generate_answer() -> str:
        """
        Streams tokens from the formatter LLM and accumulates them into a
        single string.  Using astream() instead of ainvoke() causes LangGraph's
        astream_events() to emit an `on_chat_model_stream` event for every
        token chunk — the SSE endpoint in main.py listens for those events
        and forwards each chunk to the client immediately, producing the
        word-by-word rendering effect.
        """
        chunks: list[str] = []
        try:
            async for chunk in _formatter_llm.astream(formatter_messages):
                text = ""
                if isinstance(chunk.content, str):
                    text = chunk.content
                elif isinstance(chunk.content, list):
                    # Some providers return a list of content blocks
                    text = "".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in chunk.content
                    )
                if text:
                    chunks.append(text)
            return "".join(chunks).strip()
        except Exception as exc:
            err_msg = str(exc)
            if "rate-limit" in err_msg.lower() or "429" in err_msg or "rate limit" in err_msg.lower():
                print(f"--- [ANSWER FORMATTER WARNING] Upstream rate limit encountered: {exc} ---")
                return (
                    "Notice: The primary and fallback upstream AI models are currently experiencing high demand or rate limits. "
                    "Please retry your query in a few moments."
                )
            print(f"--- [ANSWER FORMATTER ERROR] Generation failed: {exc} ---")
            raise

    async def _generate_suggestions():
        """Returns a list of suggestion strings; never raises."""
        try:
            suggestion_messages = _SUGGESTION_PROMPT.format_messages(
                query=user_query,
                # Use a placeholder — the real answer isn't ready yet;
                # suggestions will still be relevant since we pass the query + context.
                answer=full_context or user_query,
            )
            result = await _suggestion_llm.ainvoke(suggestion_messages)
            return result.suggested_queries if result and hasattr(result, "suggested_queries") else []
        except Exception as exc:
            print(f"--- [ANSWER FORMATTER NODE WARNING] Suggestion generation failed: {exc} ---")
            return existing_suggestions  # fall back to whatever was already in state

    # ------------------------------------------------------------------
    # Fire both LLM calls concurrently — no sequential waiting.
    # _generate_answer streams tokens (captured by astream_events in main.py)
    # while _generate_suggestions runs in parallel on a separate mini-model.
    # ------------------------------------------------------------------
    final_answer, suggested_queries = await asyncio.gather(
        _generate_answer(),
        _generate_suggestions(),
    )

    print(f"--- [ANSWER FORMATTER NODE] Both LLM calls completed | {len(suggested_queries)} suggestions ---")

    # ------------------------------------------------------------------
    # Build source_metadata
    # ------------------------------------------------------------------
    source_metadata: Dict[str, Any] = {
        "page_numbers": [],
        "screenshots": [],
        "generated_sql": db_results.get("generated_sql") if (db_results and not db_results.get("error")) else None,
        "math_code": math_results.get("generated_code") if (math_results and not math_results.get("error")) else None,
        "suggested_queries": suggested_queries,
    }

    if has_doc_evidence:
        for doc in retrieved_docs:
            meta = doc.get("metadata", {})
            if "page_number" in meta and meta["page_number"] not in source_metadata["page_numbers"]:
                source_metadata["page_numbers"].append(meta["page_number"])
            if "screenshot_path" in meta and meta["screenshot_path"]:
                raw_path = meta["screenshot_path"]
                filename = os.path.basename(raw_path)
                web_path = f"/screenshots/{filename}"
                if web_path not in source_metadata["screenshots"]:
                    source_metadata["screenshots"].append(web_path)

    return {
        **state,
        "final_answer": final_answer,
        "suggested_queries": suggested_queries,
        "source_metadata": source_metadata,
    }