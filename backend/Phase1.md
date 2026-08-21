# Phase 1: Core Orchestration, Automatic Persona Adaptation & Intent Router

## 1. Overview
Phase 1 establishes the core orchestration engine for the Dynamic Agentic System using LangGraph. It introduces dynamic/automatic persona selection and an intent-classification router that directs user queries to specialized execution nodes (`doc`, `db`, `math`, or combined pathways).

---

## 2. Architecture Flow

---

           [ User Query ]
                │
                ▼
[ Persona Selector Node ] ──► Auto-detects domain (Financial Analyst / Legal Advisor / General Assistant)
                │                      or accepts manual UI override
                ▼
        [ Router Node ]  ──► Classifies intent via Structured Output
                │
                ├──► 'doc'  (Document RAG Pipeline)
                ├──► 'db'   (SQL Database Pipeline)
                └──► 'math' (Deterministic Python Math Sandbox)

---

## 3. Core Components & Logic

### A. State Definition (`app/graph/state.py`)
* Defines `AgentState` schema tracking `user_query`, `persona`, `persona_prompt`, `selected_llm`, `retrieved_docs`, `db_results`, `math_results`, `final_answer`, `source_metadata`, and `suggested_queries`.

### B. Persona Selector Node (`app/graph/nodes/persona.py`)
* Inspects `state["persona"]`.
* If `persona` is set to `"Auto"` (or empty), an LLM classifier analyzes the domain of `user_query` and automatically adapts to the most suitable persona:
  * **Financial Analyst**: For stocks, revenue, moving averages, and accounting.
  * **Legal Advisor**: For contracts, compliance, data breach clauses, and liability terms.
  * **General Assistant**: For general inquiries and open conversational queries.
* Injects persona-specific domain instructions into `state["persona_prompt"]`.

### C. Router Node (`app/graph/nodes/router.py`)
* Uses `gpt-4o-mini` with Pydantic structured output (`with_structured_output`) to classify queries into execution routes (`doc`, `db`, `math`).

---

## 4. Verification Results
Running `python test_phase1.py` confirmed:
1. **Financial Query:** *"Calculate the 50-day moving average and total Q1 revenue for MSFT"* $\rightarrow$ Automatically adapted to **`Financial Analyst`**.
2. **Legal Query:** *"What clause handles data breach retention and liability penalties?"* $\rightarrow$ Automatically adapted to **`Legal Advisor`**.
3. **Intent Routing:** Successfully classified financial/metric queries to `db`/`math` and document/contract queries to `doc`.