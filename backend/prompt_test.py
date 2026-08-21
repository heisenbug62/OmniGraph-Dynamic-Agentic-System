import asyncio
import inspect
import os
import sys

# Ensure backend root is on sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.prompt_loader import load_prompt_file, get_persona_prompt
from app.graph.nodes.persona import persona_node
from app.graph.nodes.formatter import answer_formatter_node


async def run_node(node_func, state):
    """Helper to run both synchronous and asynchronous LangGraph nodes."""
    if inspect.iscoroutinefunction(node_func):
        return await node_func(state)
    return node_func(state)


def test_file_loading():
    print("=" * 60)
    print("STEP 1: Testing Direct File Loading from app/prompts/")
    print("=" * 60)

    files = ["general_assistant.txt", "financial_analyst.txt", "legal_advisor.txt"]
    for filename in files:
        content = load_prompt_file(filename)
        status = "✅ LOADED" if content else "❌ FAILED (Empty or missing)"
        preview = (content[:80].replace("\n", " ") + "...") if content else "No content"
        print(f"[{filename}] -> {status}")
        print(f"  Preview: {preview}\n")


async def test_persona_node_mapping():
    print("=" * 60)
    print("STEP 2: Testing Persona Mapping")
    print("=" * 60)

    test_personas = [
        "Financial Analyst",
        "Legal Advisor",
        "General Assistant",
        "Auto",
        "Unknown / Custom Persona"
    ]

    for p in test_personas:
        state = {"persona": p}
        updated_state = await run_node(persona_node, state)
        
        # Support both persona_prompt and system_prompt keys
        loaded_prompt = updated_state.get("persona_prompt") or updated_state.get("system_prompt", "")
        
        print(f"Persona input: '{p}'")
        print(f"  -> Assigned prompt length: {len(loaded_prompt)} chars")
        first_line = loaded_prompt.splitlines()[0] if loaded_prompt else "None"
        print(f"  -> Header preview: {first_line}\n")


async def test_formatter_simulation():
    print("=" * 60)
    print("STEP 3: Testing Formatter Node with Edge Cases & LLM")
    print("=" * 60)

    # Test Case A: Missing Evidence Edge Case
    print("--- Test Case A: Missing Document Evidence ---")
    state_no_evidence = {
        "user_query": "What is the company's policy on remote work in Japan?",
        "persona": "General Assistant",
        "persona_prompt": get_persona_prompt("General Assistant"),
        "route_target": "doc_rag",
        "retrieved_docs": [],
        "db_results": None,
        "math_results": None,
    }
    result_a = await run_node(answer_formatter_node, state_no_evidence)
    final_a = result_a.get("final_answer") or result_a.get("final_response", "")
    print(f"Final Answer Output:\n{final_a}\n")

    # Test Case B: Financial Analyst Persona with Mock SQL Data
    print("--- Test Case B: Financial Analyst with SQL Data ---")
    state_financial = {
        "user_query": "What was the total SaaS Enterprise revenue in 2024?",
        "persona": "Financial Analyst",
        "persona_prompt": get_persona_prompt("Financial Analyst"),
        "route_target": "db_sql",
        "retrieved_docs": [],
        "db_results": {
            "generated_sql": "SELECT SUM(revenue) as total_revenue FROM sales_data WHERE product = 'SaaS Enterprise' AND year = 2024",
            "rows": [{"total_revenue": 680000.0}],
            "error": None
        },
        "math_results": None,
    }
    result_b = await run_node(answer_formatter_node, state_financial)
    final_b = result_b.get("final_answer") or result_b.get("final_response", "")
    print(f"Final Answer Output:\n{final_b}\n")


async def main():
    print("\n🚀 STARTING PROMPT & FORMATTER TEST SUITE\n")
    test_file_loading()
    await test_persona_node_mapping()
    await test_formatter_simulation()
    print("🏁 ALL TESTS COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())