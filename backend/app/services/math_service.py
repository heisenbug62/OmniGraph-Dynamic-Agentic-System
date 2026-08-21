import sys
import io
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings, get_chat_model


class MathExecutionService:
    def __init__(self):
        self.llm = get_chat_model(
            model=settings.MODEL_NAME,
            temperature=0,
            max_tokens=settings.MAX_OUTPUT_TOKENS,
        )

    def execute_math_query(self, user_query: str) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert Python data scientist. Convert the user's math or analytical query "
                "into executable Python code. Print the final result clearly using print(). "
                "Return ONLY executable Python code with no markdown formatting or triple backticks."
            ),
            ("human", "{user_query}")
        ])

        formatted_prompt = prompt.format_messages(user_query=user_query)
        try:
            response = self.llm.invoke(formatted_prompt)
            generated_code = response.content.strip().replace("```python", "").replace("```", "").strip()
        except Exception as exc:
            err_msg = str(exc)
            if "rate-limit" in err_msg.lower() or "429" in err_msg or "rate limit" in err_msg.lower():
                print(f"--- [MATH ENGINE WARNING] Upstream rate limit during Python code generation: {exc} ---")
            else:
                print(f"--- [MATH ENGINE ERROR] Math LLM generation failed: {exc} ---")
            return {
                "generated_code": "",
                "output": None,
                "error": f"Math code generation failed: {err_msg}"
            }

        stdout_capture = io.StringIO()
        sys.stdout = stdout_capture

        try:
            exec_globals = {}
            exec(generated_code, exec_globals)
            sys.stdout = sys.__stdout__
            output = stdout_capture.getvalue().strip()

            return {
                "generated_code": generated_code,
                "output": output or "Executed successfully with no output.",
                "error": None
            }
        except Exception as e:
            sys.stdout = sys.__stdout__
            return {
                "generated_code": generated_code,
                "output": None,
                "error": str(e)
            }


math_service = MathExecutionService()