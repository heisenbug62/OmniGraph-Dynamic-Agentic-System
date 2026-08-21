import json
import asyncio
import itertools
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.graph.workflow import agent_app
from app.config import settings
from eval_judge import JudgeEvaluation, GOLDEN_DATASET

# -------------------------------------------------------------------
# 1. Hyperparameter Search Space & Target Criteria
# -------------------------------------------------------------------
# Reduced to 4 combinations (2 x 2) to fit within OpenRouter's free-tier
# daily request cap. Each experiment burns ~15-18 LLM calls across the
# graph's nodes (persona, router, retrieval/db/math, suggestions,
# formatter, judge) x 3 golden test cases, so keep this grid small.
GRID_SEARCH_SPACE = {
    "top_k": [2, 5],
    "temperature": [0.0, 0.2]
}

TARGET_FAITHFULNESS_THRESHOLD = 9.5
TARGET_RELEVANCE_THRESHOLD = 9.5

# -------------------------------------------------------------------
# 2. Optimization Loop Function
# -------------------------------------------------------------------
async def run_hyperparameter_tuning():
    print("\n==================================================")
    print("    STARTING AUTOMATED HYPERPARAMETER TUNING     ")
    print("==================================================\n")

    # Initialize Judge LLM
    judge_llm = ChatOpenAI(
        model="openai/gpt-4o-mini",
        api_key=settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY,
        base_url="https://openrouter.ai/api/v1" if settings.OPENROUTER_API_KEY else None,
        temperature=0.0,
        max_tokens=500
    )
    structured_judge = judge_llm.with_structured_output(JudgeEvaluation)

    judge_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert AI Benchmark Evaluator.
Score the AI Agent's response strictly on:
1. Faithfulness (1-10): Is the answer fully supported by context without hallucination?
2. Relevance (1-10): Does the answer directly solve the user request?"""),
        ("human", """User Query: {query}
Retrieved Context / Data: {context}
Agent Final Answer: {final_answer}""")
    ])

    # Generate Cartesian Product of Hyperparameters
    keys, values = zip(*GRID_SEARCH_SPACE.items())
    combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]

    best_config = None
    highest_score = -1.0

    for idx, config in enumerate(combinations, 1):
        print(f"\n--- [EXPERIMENT {idx}/{len(combinations)}] Config: {config} ---")

        results = []
        for test_case in GOLDEN_DATASET:
            query = test_case["user_query"]
            expected_route = test_case["expected_route"]

            # Run LangGraph pipeline with test case
            state_input = {"user_query": query, "persona": "Auto", **config}
            agent_output = await agent_app.ainvoke(state_input)

            actual_route = agent_output.get("route_target")
            final_answer = agent_output.get("final_answer", "")
            retrieved_docs = agent_output.get("retrieved_docs", [])
            db_results = agent_output.get("db_results", {})
            math_results = agent_output.get("math_results", {})

            context_str = f"Docs: {retrieved_docs}\nDB Results: {db_results}\nMath Results: {math_results}"

            eval_messages = judge_prompt.format_messages(
                query=query,
                context=context_str,
                final_answer=final_answer
            )
            eval_res: JudgeEvaluation = await structured_judge.ainvoke(eval_messages)

            route_passed = (actual_route == expected_route)
            results.append({
                "route_match": route_passed,
                "faithfulness": eval_res.faithfulness_score,
                "relevance": eval_res.relevance_score
            })

        avg_faithfulness = sum(r["faithfulness"] for r in results) / len(results)
        avg_relevance = sum(r["relevance"] for r in results) / len(results)
        route_acc = (sum(1 for r in results if r["route_match"]) / len(results)) * 100
        combined_score = (avg_faithfulness + avg_relevance) / 2.0

        print(f"Results for Config {config}:")
        print(f"  Routing Accuracy:     {route_acc:.1f}%")
        print(f"  Average Faithfulness: {avg_faithfulness:.2f} / 10")
        print(f"  Average Relevance:    {avg_relevance:.2f} / 10")

        if combined_score > highest_score:
            highest_score = combined_score
            best_config = config

        # Target threshold check
        if avg_faithfulness >= TARGET_FAITHFULNESS_THRESHOLD and avg_relevance >= TARGET_RELEVANCE_THRESHOLD and route_acc == 100.0:
            print("\n🎯 TARGET SCORE THRESHOLD REACHED! Stopping tuning early.")
            break

    print("\n==================================================")
    print("               TUNING COMPLETE                    ")
    print("==================================================")
    print(f" Best Config: {best_config}")
    print(f" Highest Combined Score: {highest_score:.2f} / 10")

    # Save winning config
    with open("app/best_config.json", "w") as f:
        json.dump(best_config, f, indent=2)
    print(" Saved winning parameters to 'app/best_config.json'.\n")


if __name__ == "__main__":
    asyncio.run(run_hyperparameter_tuning())