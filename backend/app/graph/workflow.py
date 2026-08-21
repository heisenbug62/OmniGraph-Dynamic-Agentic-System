"""
workflow.py — LangGraph State Machine
======================================
Optimized topology: two previously serial LLM classification nodes
(persona_node → router_node) have been merged into a single async
`classifier_node` that issues ONE structured LLM call, saving one full
network round-trip per request.

Further optimization: `suggestion_node` has been merged INTO `answer_formatter_node`.
Both LLM calls (answer generation + suggestion generation) now run concurrently
via asyncio.gather(), saving another ~4-6 s per request.

Graph execution order:
  classifier_node
      │
      ├── 'doc'     → doc_rag_node → answer_formatter_node → END
      ├── 'db'      → db_sql_node  → math_exec_node  → answer_formatter_node → END
      ├── 'math'    → math_exec_node → answer_formatter_node → END
      └── 'general' → answer_formatter_node → END
"""

from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes.classifier import classifier_node   # ← merged persona + router
from app.graph.nodes.doc_rag import doc_rag_node
from app.graph.nodes.db_sql import db_sql_node
from app.graph.nodes.math_exec import math_exec_node
from app.graph.nodes.formatter import answer_formatter_node  # ← now includes suggestions


def route_decision(state: AgentState) -> str:
    """
    Conditional routing function: reads `route_target` written by the
    classifier_node and returns the name of the next node to execute.
    """
    route = state.get("route_target", "general")
    if route == "doc":
        return "doc_rag_node"
    elif route == "db":
        return "db_sql_node"
    elif route == "math":
        return "math_exec_node"
    else:
        return "answer_formatter_node"


# ---------------------------------------------------------------------------
# Build StateGraph
# ---------------------------------------------------------------------------
workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("classifier_node", classifier_node)   # replaces persona_node + router_node
workflow.add_node("doc_rag_node", doc_rag_node)
workflow.add_node("db_sql_node", db_sql_node)
workflow.add_node("math_exec_node", math_exec_node)
# suggestion_node removed — suggestions now run concurrently inside answer_formatter_node
workflow.add_node("answer_formatter_node", answer_formatter_node)

# Entry point (single node — no serial edge to a second classifier)
workflow.set_entry_point("classifier_node")

# Conditional routing immediately after classification
workflow.add_conditional_edges(
    "classifier_node",
    route_decision,
    {
        "doc_rag_node": "doc_rag_node",
        "db_sql_node": "db_sql_node",
        "math_exec_node": "math_exec_node",
        "answer_formatter_node": "answer_formatter_node",
    }
)

# Downstream edges
workflow.add_edge("doc_rag_node", "answer_formatter_node")
workflow.add_edge("db_sql_node", "math_exec_node")
workflow.add_edge("math_exec_node", "answer_formatter_node")
workflow.add_edge("answer_formatter_node", END)

# Compile
agent_app = workflow.compile()