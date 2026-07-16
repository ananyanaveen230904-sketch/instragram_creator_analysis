"""
Natural Language Query Engine (Text-to-SQL over analytics.db)

Chains together:
  1. get_schema_description()      - describes the DB schema for the LLM prompt
  2. natural_language_to_sql()     - LLM (Gemini) turns a question into SQL
  3. is_safe_sql() / run_query()   - validates and safely executes the SQL
  4. generate_answer()             - LLM turns SQL results into a plain-English answer
  5. answer_question()             - top-level orchestrator chaining all of the above

Uses the Google Gemini API (google-genai SDK, gemini-2.5-flash model) since
this is the first LLM integration in the project.
"""

import os
import re
import sqlite3
import logging
import pandas as pd
from dotenv import load_dotenv
from google import genai

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "output", "analytics.db")

GEMINI_MODEL = "gemini-2.5-flash"

_gemini_client = None


def _get_gemini_client() -> genai.Client:
    """Lazily initialize the Gemini client (only once, on first use)."""
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. Add it to your .env file "
                "(get a free key from Google AI Studio)."
            )
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


# ---------------------------------------------------------------------------
# 1. Schema description (for grounding the text-to-SQL prompt)
# ---------------------------------------------------------------------------

def get_schema_description(db_path: str = DEFAULT_DB_PATH) -> str:
    """
    Build a text description of all tables and their columns in analytics.db,
    formatted for inclusion in an LLM prompt.

    Args:
        db_path (str): Path to the SQLite database.

    Returns:
        str: Human-readable schema description.
    """
    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

        lines = ["Database schema:"]
        for (table_name,) in tables:
            columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            col_descriptions = [f"{col[1]} ({col[2]})" for col in columns]
            lines.append(f"\nTable: {table_name}")
            lines.append(f"Columns: {', '.join(col_descriptions)}")

        return "\n".join(lines)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2. Natural language -> SQL (via Gemini)
# ---------------------------------------------------------------------------

def natural_language_to_sql(question: str, schema_description: str) -> str:
    """
    Send the user's question + schema description to Gemini and get back a
    SQL query string.

    Args:
        question (str): The user's natural language question.
        schema_description (str): Output of get_schema_description().

    Returns:
        str: A raw SQL query (no markdown, no explanation).
    """
    prompt = f"""You are a SQL generator for a SQLite database. Given the schema below and a
question, generate ONE SQL query that answers the question.

STRICT RULES:
- Only generate SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP,
  ALTER, ATTACH, PRAGMA, CREATE, or any other statement that modifies data or schema.
- Only reference tables and columns that appear in the schema below. Do not invent
  table or column names.
- Return ONLY the raw SQL query. No markdown code fences, no explanation, no
  commentary, no trailing semicolon commentary - just the SQL itself.

{schema_description}

Question: {question}

SQL query:"""

    client = _get_gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    sql = response.text.strip()

    # Strip markdown code fences if the model added them despite instructions
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql)
    sql = sql.strip()

    logger.info(f"Generated SQL for question '{question}': {sql}")
    return sql


# ---------------------------------------------------------------------------
# 3. SQL safety validation + execution
# ---------------------------------------------------------------------------

FORBIDDEN_KEYWORDS = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "ATTACH", "PRAGMA"]


def is_safe_sql(sql: str) -> tuple:
    """
    Validate that a SQL query is a safe, single, read-only SELECT statement.

    Args:
        sql (str): The SQL query to validate.

    Returns:
        (bool, str): (is_safe, reason_if_unsafe_else_empty_string)
    """
    if not sql or not sql.strip():
        return False, "Empty query."

    stripped = sql.strip()

    # Remove a single trailing semicolon (harmless) before checking for
    # multiple statements
    body = stripped[:-1] if stripped.endswith(";") else stripped

    # Block multiple statements (e.g. "SELECT ...; DROP TABLE ...")
    if ";" in body:
        return False, "Multiple SQL statements are not allowed."

    # Must start with SELECT (case-insensitive)
    if not re.match(r"^\s*SELECT\b", stripped, flags=re.IGNORECASE):
        return False, "Only SELECT statements are allowed."

    # Word-boundary check for forbidden keywords, so column names like
    # 'updated_at' don't falsely trigger on 'UPDATE'
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", stripped, flags=re.IGNORECASE):
            return False, f"Query contains forbidden keyword: {keyword}"

    return True, ""


def run_query(sql: str, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Validate and execute a SQL query against analytics.db.

    Args:
        sql (str): The SQL query to run.
        db_path (str): Path to the SQLite database.

    Returns:
        pd.DataFrame: Query results. On error or unsafe query, returns a
                      single-row DataFrame with an 'error' column instead
                      of raising, so callers can handle it gracefully.
    """
    is_safe, reason = is_safe_sql(sql)
    if not is_safe:
        logger.warning(f"Blocked unsafe query: {reason} | SQL: {sql}")
        return pd.DataFrame({"error": [f"Unsafe query blocked: {reason}"]})

    conn = sqlite3.connect(db_path)
    try:
        result_df = pd.read_sql_query(sql, conn)
        return result_df
    except Exception as e:
        logger.error(f"Error executing SQL: {e} | SQL: {sql}")
        return pd.DataFrame({"error": [f"Query execution failed: {e}"]})
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 4. Results -> natural language answer (via Gemini)
# ---------------------------------------------------------------------------

def generate_answer(question: str, query_results: pd.DataFrame, max_sample_rows: int = 20) -> str:
    """
    Summarize SQL query results into a natural language answer via Gemini.

    Args:
        question (str): The original user question.
        query_results (pd.DataFrame): Results from run_query().
        max_sample_rows (int): Max rows to include in the LLM prompt, to
                                keep the prompt small for large result sets.

    Returns:
        str: A natural language answer.
    """
    if "error" in query_results.columns and len(query_results) == 1:
        return f"I couldn't answer that: {query_results['error'].iloc[0]}"

    if query_results.empty:
        return "The query ran successfully but returned no results."

    sample = query_results.head(max_sample_rows)
    results_text = sample.to_string(index=False)

    truncated_note = ""
    if len(query_results) > max_sample_rows:
        truncated_note = f"\n(Showing {max_sample_rows} of {len(query_results)} total rows.)"

    prompt = f"""A user asked the following question about an Instagram creator engagement dataset:

Question: {question}

The SQL query results are:
{results_text}
{truncated_note}

Write a clear, concise natural language answer to the question based on these results.
Do not mention SQL or databases - just answer the question directly, as if
explaining the finding to someone reading a report."""

    client = _get_gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    return response.text.strip()


# ---------------------------------------------------------------------------
# 5. Top-level orchestrator
# ---------------------------------------------------------------------------

def answer_question(question: str, db_path: str = DEFAULT_DB_PATH) -> dict:
    """
    Full pipeline: question -> schema -> SQL -> execute -> natural language answer.

    Args:
        question (str): The user's natural language question.
        db_path (str): Path to the SQLite database.

    Returns:
        dict: {"question": str, "sql": str, "raw_results": pd.DataFrame, "answer": str}
    """
    try:
        schema_description = get_schema_description(db_path)
        sql = natural_language_to_sql(question, schema_description)
        raw_results = run_query(sql, db_path)
        answer = generate_answer(question, raw_results)

        return {
            "question": question,
            "sql": sql,
            "raw_results": raw_results,
            "answer": answer,
        }
    except Exception as e:
        logger.error(f"Error in answer_question pipeline: {e}", exc_info=True)
        return {
            "question": question,
            "sql": "",
            "raw_results": pd.DataFrame({"error": [str(e)]}),
            "answer": f"Sorry, something went wrong answering that question: {e}",
        }
