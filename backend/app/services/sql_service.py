import sqlite3
import os
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings, get_chat_model


class SQLService:
    def __init__(self, db_path: str = "data/database/app_data.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_demo_database()

        self.llm = get_chat_model(
            model=settings.MODEL_NAME,
            temperature=0,
            max_tokens=settings.MAX_OUTPUT_TOKENS,
        )

    def _init_demo_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region TEXT,
                product TEXT,
                revenue REAL,
                quarter TEXT,
                year INTEGER
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM sales_data")
        if cursor.fetchone()[0] == 0:
            sample_rows = [
                ("North America", "SaaS Enterprise", 150000.0, "Q1", 2024),
                ("North America", "SaaS Pro", 85000.0, "Q1", 2024),
                ("Europe", "SaaS Enterprise", 120000.0, "Q1", 2024),
                ("Asia Pacific", "SaaS Enterprise", 95000.0, "Q1", 2024),
                ("North America", "SaaS Enterprise", 180000.0, "Q2", 2024),
                ("Europe", "SaaS Enterprise", 135000.0, "Q2", 2024),
            ]
            cursor.executemany(
                "INSERT INTO sales_data (region, product, revenue, quarter, year) VALUES (?, ?, ?, ?, ?)",
                sample_rows
            )
            conn.commit()

        conn.close()

    def get_schema(self) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
        schemas = [row[0] for row in cursor.fetchall() if row[0]]
        conn.close()
        return "\n\n".join(schemas)

    def execute_query(self, user_query: str) -> Dict[str, Any]:
        schema_info = self.get_schema()

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert SQL assistant. Given the database schema below, convert the user query into a valid, executable SQLite query. Return ONLY raw SQL, with no markdown fences, code blocks, or explanations.\n\nDatabase Schema:\n{schema}"),
            ("human", "{user_query}")
        ])

        formatted_prompt = prompt.format_messages(schema=schema_info, user_query=user_query)
        try:
            response = self.llm.invoke(formatted_prompt)
            generated_sql = response.content.strip().replace("```sql", "").replace("```", "").strip()
            print(f"--- [SQL ENGINE] Generated SQL: {generated_sql} ---")
        except Exception as exc:
            err_msg = str(exc)
            if "rate-limit" in err_msg.lower() or "429" in err_msg or "rate limit" in err_msg.lower():
                print(f"--- [SQL ENGINE WARNING] Upstream rate limit during SQL generation: {exc} ---")
            else:
                print(f"--- [SQL ENGINE ERROR] SQL LLM generation failed: {exc} ---")
            return {
                "generated_sql": "",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": f"SQL generation failed: {err_msg}"
            }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(generated_sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            conn.close()

            results = [dict(zip(columns, row)) for row in rows]
            return {
                "generated_sql": generated_sql,
                "columns": columns,
                "rows": results,
                "row_count": len(results),
                "error": None
            }
        except Exception as e:
            conn.close()
            return {
                "generated_sql": generated_sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e)
            }


sql_service = SQLService()