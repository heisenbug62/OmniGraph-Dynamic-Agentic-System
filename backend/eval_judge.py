import json
import asyncio
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.graph.workflow import agent_app
from app.config import settings

# -------------------------------------------------------------------
# 1. Pydantic Schema for LLM Judge Structured Output
# -------------------------------------------------------------------
class JudgeEvaluation(BaseModel):
    faithfulness_score: int = Field(
        description="Score from 1 to 10. How accurately does the final answer reflect the retrieved context without making things up?"
    )
    relevance_score: int = Field(
        description="Score from 1 to 10. How well does the final answer address the user's specific query?"
    )
    reasoning: str = Field(
        description="Brief explanation justifying the scores."
    )

# -------------------------------------------------------------------
# 2. Golden Test Dataset (Ground Truth Benchmarks)
# -------------------------------------------------------------------
GOLDEN_DATASET = [
    {
        "id": "test_1_sql_db",
        "user_query": "What is the total revenue for North America in 2024?",
        "expected_route": "db"
    },
    {
        "id": "test_2_doc_rag",
        "user_query": "What is the purpose of the Statement of Financial Position described in the document?",
        "expected_route": "doc"
    },
    {
        "id": "test_3_doc_policy",
        "user_query": "What does IAS 1 state regarding how assets and liabilities should be presented on the balance sheet?",
        "expected_route": "doc"
    }
]

# -------------------------------------------------------------------
# 3. Judge Evaluation Engine Function
# -------------------------------------------------------------------
async def evaluate_pipeline():
    print("\n==================================================")
    print("      STARTING LLM-AS-A-JUDGE BENCHMARK          ")
    print("==================================================\n")

    # Use gpt-4o-mini with max_tokens cap to fit low-credit limits
    judge_llm = ChatOpenAI(
        model="openai/gpt-4o-mini",
        api_key=settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY,
        base_url="https://openrouter.ai/api/v1" if settings.OPENROUTER_API_KEY else None,
        temperature=0.0,
        max_tokens=500  # <--- CRITICAL FIX: Limits token reservation to prevent 402 error
    )

    structured_judge = judge_llm.with_structured_output(JudgeEvaluation)

    judge_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert AI Benchmark Evaluator. 
Your job is to objectively score an AI Agent's final response based on the retrieved raw context.
Grade the response on:
1. Faithfulness (1-10): Is the answer fully supported by the retrieved context/SQL data without hallucination?
2. Relevance (1-10): Does the answer directly solve the user's request?
Provide a concise justification for your scores."""),
        ("human", """User Query: {query}
Retrieved Context / Data:
{context}
Agent's Final Answer:
{final_answer}""")
    ])

    results = []
    for test_case in GOLDEN_DATASET:
        test_id = test_case["id"]
        query = test_case["user_query"]
        expected_route = test_case["expected_route"]

        print(f"--- Running Eval Case: {test_id} ---")

        # 1. Execute the LangGraph Agent
        state_input = {"user_query": query, "persona": "Auto"}
        agent_output = await agent_app.ainvoke(state_input)

        actual_route = agent_output.get("route_target")
        final_answer = agent_output.get("final_answer", "")

        # Consolidate evidence context for the judge
        retrieved_docs = agent_output.get("retrieved_docs", [])
        db_results = agent_output.get("db_results", {})
        math_results = agent_output.get("math_results", {})
        context_str = f"Docs: {retrieved_docs}\nDB Results: {db_results}\nMath Results: {math_results}"

        # 2. Invoke Judge Evaluation
        eval_messages = judge_prompt.format_messages(
            query=query,
            context=context_str,
            final_answer=final_answer
        )
        eval_res: JudgeEvaluation = await structured_judge.ainvoke(eval_messages)

        # Check Routing Accuracy
        route_passed = (actual_route == expected_route)
        results.append({
            "id": test_id,
            "route_match": route_passed,
            "expected_route": expected_route,
            "actual_route": actual_route,
            "faithfulness": eval_res.faithfulness_score,
            "relevance": eval_res.relevance_score,
            "reasoning": eval_res.reasoning
        })

        print(f"✓ Route: {actual_route} (Expected: {expected_route}) | Passed: {route_passed}")
        print(f"✓ Faithfulness Score: {eval_res.faithfulness_score}/10")
        print(f"✓ Relevance Score:    {eval_res.relevance_score}/10")
        print(f"✓ Judge Reasoning:   {eval_res.reasoning}\n")

    # -------------------------------------------------------------------
    # 4. Summary & Benchmark Aggregate
    # -------------------------------------------------------------------
    avg_faithfulness = sum(r["faithfulness"] for r in results) / len(results)
    avg_relevance = sum(r["relevance"] for r in results) / len(results)
    route_accuracy = (sum(1 for r in results if r["route_match"]) / len(results)) * 100

    print("==================================================")
    print("               BENCHMARK SUMMARY                  ")
    print("==================================================")
    print(f" Routing Accuracy:     {route_accuracy:.1f}%")
    print(f" Average Faithfulness: {avg_faithfulness:.2f} / 10")
    print(f" Average Relevance:    {avg_relevance:.2f} / 10")
    print("==================================================\n")


if __name__ == "__main__":
    asyncio.run(evaluate_pipeline())