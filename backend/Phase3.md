# Phase 3: Structured Data Querying (SQL) & Deterministic Math Execution Nodes

## 1. Overview
Phase 3 implements structured data querying and deterministic calculation execution engines. It allows the agent system to translate natural language into safe executable SQL queries against a database and run Python code for numerical math problems.

---

## 2. Architecture Flow

                    [ Router Node ]
                      /           \
             Route = 'db'        Route = 'math'
                    /               \
                   ▼                 ▼
         [ DB SQL Node ]         [ Math Exec Node ]
               │                         │
               ▼                         ▼
     [ SQL Engine Service ]    [ Python Math Service ]
     (Generates & executes      (Executes exact formulas
      SQLite/PostgreSQL)         deterministically)

---

## 3. Core Components & Logic

### A. SQL Service & Node (`app/services/sql_service.py` & `app/graph/nodes/db_sql.py`)
* Connects to SQLite database (`data/database/app_data.db`) containing structured data (`sales_data`).
* Extracts table schema dynamically to prompt the LLM.
* Generates clean raw SQL, executes it safely, and populates `state["db_results"]` with structured record rows and columns.

### B. Math Service & Node (`app/services/math_service.py` & `app/graph/nodes/math_exec.py`)
* Accepts mathematical natural language questions.
* Uses an LLM to generate executable Python code with variables and formulas.
* Executes Python code in an isolated scope, capturing stdout/return value `1614.72` to ensure 100% numerical accuracy without LLM hallucination.
* Populates `state["math_results"]` with code snippets and calculated values.

---

## 4. Verification

Running `python test_phase3.py` verified:
1. **SQL Node:** Correctly translated *"What is the total revenue for North America in 2024?"* into `SELECT SUM(revenue)...` and retrieved `$415,000.0`.
2. **Math Node:** Correctly generated compound interest Python code for `$10,000 at 5% over 3 years` and returned exact result `1614.7223`.