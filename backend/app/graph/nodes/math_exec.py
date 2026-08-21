import asyncio
from app.graph.state import AgentState
from app.services.math_service import math_service

async def math_exec_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: Translates math queries into Python code and computes exact deterministic results asynchronously.
    Bypasses secondary execution if a DB query already provided a direct scalar aggregate.
    """
    user_query = state.get("user_query", "")
    db_results = state.get("db_results")

    print(f"--- [MATH EXEC NODE] Processing query: '{user_query}' ---")

    # Check if DB query already produced a direct scalar aggregate result
    if db_results and not db_results.get("error") and db_results.get("rows"):
        rows = db_results.get("rows", [])
        # If the result is a single row with a single column (e.g. SUM, COUNT, AVG)
        if len(rows) == 1 and len(rows[0]) == 1:
            print("--- [MATH EXEC NODE] Simple SQL aggregate detected. Skipping secondary Python math execution. ---")
            return {
                **state,
                "math_results": None
            }

    # Offload blocking Python math execution to a worker thread
    math_result = await asyncio.to_thread(math_service.execute_math_query, user_query=user_query)

    print(f"--- [MATH EXEC NODE] Calculation Result: {math_result.get('output')} ---")

    # Update AgentState
    return {
        **state,
        "math_results": math_result
    }