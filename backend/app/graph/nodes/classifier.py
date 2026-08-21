"""
classifier.py — Merged Persona-Router Node
==========================================
Replaces the two serial LLM calls from persona_node + router_node with a SINGLE
async structured-output call.  The LLM returns a JSON object containing both the
adapted persona and the route target, cutting one full network round-trip (~5-10 s)
off every Auto-mode request.

Output contract (preserved for downstream nodes and the TracePanel):
  state["persona"]       → "Financial Analyst" | "Legal Advisor" | "General Assistant"
  state["persona_prompt"]→ full system-prompt text loaded from app/prompts/
  state["route_target"]  → "doc" | "db" | "math" | "general"

==============================================================================
Optimisation — Three-tier classification strategy (fastest path wins):
==============================================================================

Tier 1 — Instant bypass (0 ms):
  • Trivial conversational queries (greetings, thanks, farewells) are caught by a
    small set of prefix/keyword patterns and routed to 'general' without ANY LLM
    call.  Saves ~1.5–3 s on every small-talk message.

Tier 2 — Rule-based route only (~0 ms):
  • When the user has already pinned a persona (not 'Auto'), the persona step is
    fully skipped.  Only the route_target is determined.
  • For short queries whose tokens match the keyword dictionaries well enough
    (confidence ≥ threshold), the existing _fallback_classify() logic is promoted
    to the primary path — still no LLM call.

Tier 3 — LLM structured-output call (~1.5–3 s):
  • All remaining ambiguous queries go through the LLM as before.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

from app.config import settings, get_chat_model
from app.graph.state import AgentState
from app.utils.prompt_loader import get_persona_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Structured output schema — single LLM call returns both fields
# ---------------------------------------------------------------------------

class ClassificationResult(BaseModel):
    persona: str = Field(
        description=(
            "The expert domain persona best suited for this query. "
            "Must be exactly one of: 'Financial Analyst', 'Legal Advisor', 'General Assistant'."
        )
    )
    route_target: str = Field(
        description=(
            "The execution pipeline to route this query to. "
            "Must be exactly one of: 'doc', 'db', 'math', 'general'."
        )
    )


# ---------------------------------------------------------------------------
# 2. Module-level LLM client with automatic fallback chain
# ---------------------------------------------------------------------------

_classifier_llm = get_chat_model(
    model=settings.MODEL_NAME,
    temperature=0.0,          # deterministic classification
    max_tokens=150,           # only need a small JSON blob
).with_structured_output(ClassificationResult)


# ---------------------------------------------------------------------------
# 3. Tier-1 — Instant conversational bypass (no LLM call)
# ---------------------------------------------------------------------------

# Normalised set of exact short-query matches that are always 'general'
_TRIVIAL_EXACT: frozenset[str] = frozenset({
    "hi", "hello", "hey", "hiya", "howdy",
    "bye", "goodbye", "see you", "cya",
    "thanks", "thank you", "thx", "ty",
    "ok", "okay", "cool", "great", "nice",
    "yes", "no", "sure", "alright",
    "help", "what can you do", "what do you do",
})

# Regex patterns matched against the lowercased query — still no LLM
_TRIVIAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"^(hi|hello|hey|howdy|hiya)[!.,\s]*$"),
    re.compile(r"^(bye|goodbye|see\s+you|cya)[!.,\s]*$"),
    re.compile(r"^(thanks?|thank\s+you|thx|ty)[!.,\s]*$"),
    re.compile(r"^who\s+are\s+you[\s?!.]*$"),
    re.compile(r"^what\s+(are|can)\s+you[\s\w]*[\s?!.]*$"),
    re.compile(r"^how\s+are\s+you[\s?!.]*$"),
    re.compile(r"^(good\s+)?(morning|afternoon|evening|night)[\s!.]*$"),
    re.compile(r"^(ok|okay|sure|alright|cool|great|nice|got\s+it)[\s!.]*$"),
]


def _is_trivial_conversational(query: str) -> bool:
    """
    Returns True if the query is a greeting / farewell / filler that can be
    answered by the general path without any classification LLM call.
    """
    q = query.strip().lower()
    if q in _TRIVIAL_EXACT:
        return True
    for pattern in _TRIVIAL_PATTERNS:
        if pattern.match(q):
            return True
    return False


# ---------------------------------------------------------------------------
# 4. Rule-based fallback / Tier-2 classifier
# ---------------------------------------------------------------------------

_PERSONA_KEYWORDS: dict[str, set[str]] = {
    "Financial Analyst": {
        "financial", "revenue", "stock", "calculation", "ratio", "math",
        "profit", "loss", "balance", "equity", "earnings", "dividend",
        "analysis", "budget", "forecast", "metrics",
    },
    "Legal Advisor": {
        "compliance", "regulation", "legal", "contract", "clause", "liability",
        "law", "statute", "ias", "ifrs", "disclosure", "policy", "audit",
        "risk", "agreement", "obligation",
    },
}

_ROUTE_KEYWORDS: dict[str, set[str]] = {
    "doc":  {"document", "pdf", "policy", "contract", "clause", "report", "agreement"},
    "db":   {"sales", "revenue", "quarter", "record", "database", "row", "total"},
    "math": {"calculate", "compute", "arithmetic", "equation", "formula", "percent",
             "average", "sum", "product", "statistic", "analysis"},
}

# Minimum keyword-hit count required to trust rule-based classification
# instead of escalating to the LLM (Tier-2 → Tier-3 threshold).
_ROUTE_CONFIDENCE_THRESHOLD = 1   # ≥1 matching keyword is sufficient for route
_PERSONA_CONFIDENCE_THRESHOLD = 1  # ≥1 matching keyword is sufficient for persona


def _rule_based_classify(
    user_query: str,
    require_persona: bool = True,
) -> tuple[str, str, bool]:
    """
    Keyword-based classification.

    Returns:
        (persona, route_target, confident)

    `confident` is True when the rule engine matched at least one keyword for
    route_target (and persona, when require_persona is True), meaning we can
    skip the LLM call entirely.
    """
    q_lower = user_query.lower()
    words = set(q_lower.split())

    # Route classification
    route_target = "general"
    best_route_score = 0
    for candidate, keywords in _ROUTE_KEYWORDS.items():
        score = len(words & keywords)
        if score > best_route_score:
            best_route_score = score
            route_target = candidate

    route_confident = best_route_score >= _ROUTE_CONFIDENCE_THRESHOLD

    # Persona classification (only when operating in 'Auto' mode)
    persona = "General Assistant"
    best_persona_score = 0
    if require_persona:
        for candidate, keywords in _PERSONA_KEYWORDS.items():
            score = len(words & keywords)
            if score > best_persona_score:
                best_persona_score = score
                persona = candidate

    persona_confident = (not require_persona) or (best_persona_score >= _PERSONA_CONFIDENCE_THRESHOLD)

    confident = route_confident and persona_confident
    return persona, route_target, confident


# ---------------------------------------------------------------------------
# 5. Classification prompt — used only when Tier-1 and Tier-2 both fail
# ---------------------------------------------------------------------------

_CLASSIFICATION_PROMPT = """\
You are an expert query classifier for a multi-agent AI system.

Analyse the user query below and respond with a JSON object containing exactly:
  - "persona": the expert domain best suited to answer this query
  - "route_target": the execution pipeline that should handle this query

Persona options:
  - "Financial Analyst"  → math, calculations, financial data, ratios, stocks, revenue
  - "Legal Advisor"      → contracts, compliance, regulations, legal clauses, IAS/IFRS
  - "General Assistant"  → greetings, general knowledge, anything else

Route target options:
  - "doc"     → questions about uploaded documents, PDFs, policies, contracts
  - "db"      → questions about structured sales records, database rows, revenue figures
  - "math"    → arithmetic, equations, statistical calculations, Python data analysis
  - "general" → greetings, general knowledge, casual conversation

User Query: {user_query}
"""


# ---------------------------------------------------------------------------
# 6. The combined LangGraph node
# ---------------------------------------------------------------------------

async def classifier_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: Three-tier combined persona-router classifier.

    Tier 1 — Instant bypass (0 LLM calls):
        Trivial conversational queries (greetings, farewells, thanks) are
        immediately classified as persona='General Assistant', route='general'.

    Tier 2 — Rule-based (0 LLM calls):
        When the user has pinned a persona (non-Auto), skip persona classification.
        When keyword confidence is high enough, route without an LLM call.

    Tier 3 — LLM structured-output call:
        Only ambiguous queries that passed through Tiers 1 and 2 without high
        confidence reach the LLM.

    Falls back to rule-based classification if the LLM call fails.
    """
    user_query: str = state.get("user_query", "")
    selected_persona: Optional[str] = state.get("persona", "Auto")

    # Whether the user has fixed a persona (anything other than Auto / empty)
    persona_is_pinned = selected_persona not in ("Auto", None, "")

    persona = selected_persona if persona_is_pinned else "General Assistant"
    route_target = "general"
    tier_used = "llm"  # for logging

    # ------------------------------------------------------------------
    # Tier 1: Instant conversational bypass — no LLM, no keywords
    # ------------------------------------------------------------------
    if _is_trivial_conversational(user_query):
        route_target = "general"
        if not persona_is_pinned:
            persona = "General Assistant"
        tier_used = "tier1-bypass"
        logger.info(
            "[CLASSIFIER NODE] Tier-1 bypass | persona='%s' route_target='%s'",
            persona, route_target,
        )
        print(
            f"--- [CLASSIFIER NODE] Tier-1 (instant bypass) | "
            f"persona='{persona}' | route_target='{route_target}' ---"
        )

    else:
        # ------------------------------------------------------------------
        # Tier 2: Rule-based keyword classification
        # ------------------------------------------------------------------
        rb_persona, rb_route, rb_confident = _rule_based_classify(
            user_query,
            require_persona=not persona_is_pinned,
        )

        if rb_confident:
            # Rule engine has sufficient confidence — skip LLM entirely
            route_target = rb_route
            if not persona_is_pinned:
                persona = rb_persona
            tier_used = "tier2-rules"
            logger.info(
                "[CLASSIFIER NODE] Tier-2 rule-based | persona='%s' route_target='%s'",
                persona, route_target,
            )
            print(
                f"--- [CLASSIFIER NODE] Tier-2 (rule-based) | "
                f"persona='{persona}' | route_target='{route_target}' ---"
            )

        else:
            # ------------------------------------------------------------------
            # Tier 3: LLM structured-output call (only for ambiguous queries)
            # ------------------------------------------------------------------
            try:
                prompt = _CLASSIFICATION_PROMPT.format(user_query=user_query)
                result: ClassificationResult = await _classifier_llm.ainvoke(prompt)

                route_target = result.route_target

                # Only adopt the LLM persona when the user is in Auto mode
                if not persona_is_pinned:
                    persona = result.persona

                tier_used = "tier3-llm"
                logger.info(
                    "[CLASSIFIER NODE] Tier-3 LLM | persona='%s' route_target='%s'",
                    persona, route_target,
                )
                print(
                    f"--- [CLASSIFIER NODE] Tier-3 (LLM) | "
                    f"persona='{persona}' | route_target='{route_target}' ---"
                )

            except Exception as exc:
                logger.warning(
                    "[CLASSIFIER NODE] Tier-3 LLM failed: %s — using Tier-2 rule-based fallback",
                    exc,
                )
                print(
                    f"--- [CLASSIFIER NODE WARNING] LLM failed ({exc}); "
                    f"falling back to rule-based ---"
                )
                route_target = rb_route
                if not persona_is_pinned:
                    persona = rb_persona
                tier_used = "tier2-fallback"

    # ------------------------------------------------------------------
    # Normalise to valid values
    # ------------------------------------------------------------------
    _valid_personas = {"Financial Analyst", "Legal Advisor", "General Assistant"}
    if persona not in _valid_personas:
        persona = "General Assistant"

    _valid_routes = {"doc", "db", "math", "general"}
    if route_target not in _valid_routes:
        route_target = "general"

    # Load the system prompt for the resolved persona
    persona_prompt = get_persona_prompt(persona)

    return {
        **state,
        "persona": persona,
        "persona_prompt": persona_prompt,
        "route_target": route_target,
    }
