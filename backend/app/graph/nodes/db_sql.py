import asyncio
from app.graph.state import AgentState
from app.services.sql_service import sql_service

async def db_sql_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: Translates natural language queries to SQL and executes against the database asynchronously.
    """
    user_query = state.get("user_query", "")
    print(f"--- [DB SQL NODE] Processing query: '{user_query}' ---")
    
    # Offload the blocking SQL generation and DB execution to a worker thread
    sql_result = await asyncio.to_thread(sql_service.execute_query, user_query=user_query)
    
    print(f"--- [DB SQL NODE] Returned {sql_result.get('row_count', 0)} rows ---")
    
    # Update AgentState
    return {
        **state,
        "db_results": sql_result
    }