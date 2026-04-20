import requests
import sqlite3
import re
import requests
import sqlite3
import re
import os
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")

DEFAULT_SYSTEM_PROMPT = """
You are a strict SQLite query generator. Your only job is to output a single valid SQLite SELECT statement.

RULES — follow every one, no exceptions:
1. Output ONLY the raw SQL. No explanations, no prose, no preamble.
2. Do NOT wrap the SQL in markdown fences (no ```sql, no ```, no backticks of any kind).
3. Do NOT prefix with labels like "SQL:", "Query:", "Answer:", "SELECT query:" or anything similar.
4. The first character of your response must be the letter S (from SELECT).
5. The last character of your response must be a semicolon (;).
6. Only use the table name: uploaded_data
7. Only use column names that exist in the schema provided below.
8. Never use columns, tables, or aliases not present in the schema.
9. Use only standard SQLite syntax — no window functions like ROW_NUMBER() unless explicitly supported.
10. For "top N" questions, use ORDER BY + LIMIT N.
11. For aggregate questions (average, total, count), use the appropriate aggregate function.
12. Never output UPDATE, INSERT, DELETE, DROP, or any non-SELECT statement.
13. If the question cannot be answered with the available columns, output exactly: SELECT 'insufficient schema' AS error;

SCHEMA:
{schema_placeholder}

Now generate the SQL for the following question. Remember: raw SQL only, starting with SELECT.
"""

# Configuration defaults
DEFAULT_DB_PATH = "app/db/app.db"

def get_schema(table_name, db_path=DEFAULT_DB_PATH):
    # dynamically fetches table schema from sqlite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    safe_table_name = table_name.replace('"', '""')
    #table info
    cursor.execute(f'PRAGMA table_info("{safe_table_name}")')
    columns_info = cursor.fetchall()

    conn.close()

    columns = [col[1] for col in columns_info]
    schema = f"""
    Table : {table_name}
    Columns:
    """
    for col in columns:
        schema+=f"- {col}\n"
    return schema

def get_table_columns(table_name, db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    safe_table_name = table_name.replace('"', '""')
    cursor.execute(f'PRAGMA table_info("{safe_table_name}")')
    columns_info = cursor.fetchall()
    conn.close()
    return [col[1] for col in columns_info]

def _call_ollama(system_prompt, user_prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "options": {
                    "temperature": 0
                }
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "No response from model").strip()
    except Exception as e:
        return f"Error calling Ollama: {e}"

def _extract_sql(raw_text):
    # 1) Try to extract from triple-backtick markdown fences.
    fence_match = re.search(r"```(sql)?\s*(.*?)\s*```", raw_text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(2).strip()
    else:
        text = raw_text.strip()

    # 2) Strip common prose prefixes that models often include even in "code-only" mode.
    prefixes_to_strip = [
        r"^sql\s*:\s*",
        r"^select\s+query\s*:\s*",
        r"^here\s+is\s+the\s+sql\s*:\s*",
        r"^query\s*:\s*"
    ]
    for pattern in prefixes_to_strip:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    # 3) Ensure we start at the first SQL keyword if there's still leading noise.
    lowered = text.lower()
    keywords = ["select", "with"]
    start_indices = [lowered.find(kw) for kw in keywords if lowered.find(kw) != -1]

    if start_indices:
        start_idx = min(start_indices)
        if start_idx > 0:
            text = text[start_idx:]

    # 4) Keep only the first SQL statement (stop at first semicolon).
    first_semicolon = text.find(";")
    if first_semicolon != -1:
        text = text[: first_semicolon + 1]

    return text.strip()

def _basic_sql_sanity(sql_query, table_name):
    lowered = sql_query.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False, "Only SELECT SQL is allowed."
    if f" from {table_name.lower()}" not in lowered and f' from "{table_name.lower()}"' not in lowered:
        return False, f"SQL must query table `{table_name}` only."
    for blocked in [" drop ", " delete ", " update ", " insert ", " alter ", " truncate "]:
        if blocked in f" {lowered} ":
            return False, "Only read-only SQL is allowed."
    return True, ""


def generate_sql(user_query, table_name, db_path=DEFAULT_DB_PATH, custom_system_prompt=None):
    schema = get_schema(table_name=table_name, db_path=db_path)
    columns = get_table_columns(table_name=table_name, db_path=db_path)

    if custom_system_prompt:
        system_prompt = custom_system_prompt
    else:
        system_prompt = DEFAULT_SYSTEM_PROMPT
    
    # Fill in the schema placeholder
    system_prompt = system_prompt.replace("{schema_placeholder}", schema)

    user_prompt = f"User question: {user_query}"
    sql_query = _extract_sql(_call_ollama(system_prompt, user_prompt))
    is_valid, reason = _basic_sql_sanity(sql_query, table_name)
    if is_valid:
        return sql_query

    # Second pass: repair SQL when first draft violates table/safety rules.
    repair_prompt = f"""
You generated invalid SQL.

Failure reason:
{reason}

Allowed table:
{table_name}

Allowed columns:
{", ".join(columns)}

Original user question:
{user_query}

Invalid SQL:
{sql_query}

Return a corrected SQLite SELECT query only.
"""
    repaired_sql = _extract_sql(_call_ollama(system_prompt, repair_prompt))
    repaired_valid, _ = _basic_sql_sanity(repaired_sql, table_name)
    if repaired_valid:
        return repaired_sql
    return sql_query

