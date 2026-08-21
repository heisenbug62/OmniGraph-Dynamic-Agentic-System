import asyncio
import time
from collections import defaultdict
from typing import Dict, List
 
from app.graph.workflow import agent_app  # adjust import if your graph export differs
 
 
# Names of your actual LangGraph nodes, so we only aggregate real pipeline
# steps into the "NODE BREAKDOWN" table (adjust to match your real node names
# if any of these differ, e.g. db_sql_node).
KNOWN_NODES = {
    "persona_node",
    "router_node",
    "doc_rag_node",
    "db_sql_node",
    "math_exec_node",
    "suggestion_node",
    "answer_formatter_node",
}
 
 
async def profile_graph_execution(query: str, persona: str = "Auto") -> dict:
    print(f"\nProfiling: '{query}'")
    print("-" * 78)
 
    initial_state = {
        "user_query": query,
        "persona": persona,
    }
 
    # Keyed by run_id (unique per execution span), NOT by name — this avoids
    # silently overwriting timings when a node or LLM call fires more than
    # once in a single graph run.
    run_starts: Dict[str, float] = {}
 
    node_durations: Dict[str, List[float]] = defaultdict(list)
    llm_durations: Dict[str, List[float]] = defaultdict(list)
 
    start_time = time.perf_counter()
 
    try:
        async for event in agent_app.astream_events(initial_state, version="v2"):
            kind = event.get("event")
            name = event.get("name", "")
            run_id = event.get("run_id")
 
            if kind in ("on_chain_start", "on_chat_model_start", "on_llm_start"):
                run_starts[run_id] = time.perf_counter()
 
            elif kind in ("on_chain_end", "on_chat_model_end", "on_llm_end"):
                if run_id in run_starts:
                    duration = time.perf_counter() - run_starts.pop(run_id)
 
                    if kind == "on_chain_end" and name in KNOWN_NODES:
                        node_durations[name].append(duration)
                    elif kind in ("on_chat_model_end", "on_llm_end"):
                        # LLM calls are nested inside nodes — tracked separately
                        # so you can see how much of a node's time is "waiting
                        # on the model API" vs. its own logic.
                        llm_durations[name or "llm_call"].append(duration)
 
    except Exception as e:
        print(f"Error during execution: {e}")
 
    total_time = time.perf_counter() - start_time
 
    def _print_table(title: str, data: Dict[str, List[float]]):
        print(f"\n{title}")
        print(f"{'Name':<28} | {'Calls':<6} | {'Total (s)':<10} | {'Avg (s)':<9} | {'% of Total':<10}")
        print("-" * 78)
        if not data:
            print("(none captured)")
            return
        for name, durations in sorted(data.items(), key=lambda kv: sum(kv[1]), reverse=True):
            total = sum(durations)
            avg = total / len(durations)
            pct = (total / total_time) * 100 if total_time else 0
            print(f"{name:<28} | {len(durations):<6} | {total:>8.3f}s  | {avg:>7.3f}s | {pct:>6.1f}%")
 
    _print_table("NODE BREAKDOWN", node_durations)
    _print_table("LLM CALL BREAKDOWN (time spent nested inside nodes above)", llm_durations)
 
    print("\n" + "-" * 78)
    print(f"{'TOTAL WALL TIME':<28} | {'':<6} | {total_time:>8.3f}s")
    print("=" * 78)
 
    return {
        "query": query,
        "total_time": total_time,
        "nodes": {k: sum(v) for k, v in node_durations.items()},
        "llm_calls": {k: sum(v) for k, v in llm_durations.items()},
    }
 
 
async def run_all(test_queries: List[str]):
    results = []
    for q in test_queries:
        result = await profile_graph_execution(q)
        results.append(result)
    return results
 
 
if __name__ == "__main__":
    test_queries = [
        "Hi, how are you?",                                          # General persona, no retrieval
        "What is the product of 133 and 21?",                        # Math node
        "What was the total net profit for the year 2019?",          # Doc RAG node
        # Add a query that should trigger the SQL/DB node here, e.g.:
        # "What was MSFT's closing price on March 1, 2024?",
    ]
 
    asyncio.run(run_all(test_queries))