import requests
import sqlite3
import re
OLLAMA_URL = "http://localhost:11434/api/generate"

def normalize_nutrition_columns(db_path="app/db/nutrition.db"):
    rename_map = {
        "Food_Item": "food_item",
        "Category": "category",
        "Calories (kcal)": "calories",
        "Protein (g)": "protein",
        "Carbohydrates (g)": "carbs",
        "Fat (g)": "fat",
        "Fiber (g)": "fiber",
        "Sugars (g)": "sugars",
        "Sodium (mg)": "sodium",
        "Cholesterol (mg)": "cholesterol",
        "Meal_Type": "meal_type",
        "Water_Intake (ml)": "water_intake",
    }

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(nutrition)")
    current_columns = {row[1] for row in cursor.fetchall()}

    for old_name, new_name in rename_map.items():
        if old_name in current_columns and new_name not in current_columns:
            cursor.execute(
                f'ALTER TABLE nutrition RENAME COLUMN "{old_name}" TO "{new_name}"'
            )
            current_columns.remove(old_name)
            current_columns.add(new_name)

    conn.commit()
    conn.close()

def get_schema(table_name="nutrition", db_path="app/db/nutrition.db"):
    #dynamically fetches table schema from sqlite
    if table_name == "nutrition":
        normalize_nutrition_columns(db_path=db_path)
    conn=sqlite3.connect(db_path)
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

def get_table_columns(table_name="nutrition", db_path="app/db/nutrition.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    safe_table_name = table_name.replace('"', '""')
    cursor.execute(f'PRAGMA table_info("{safe_table_name}")')
    columns_info = cursor.fetchall()
    conn.close()
    return [col[1] for col in columns_info]

def _call_ollama(system_prompt, user_prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "mistral",
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": 0
            }
        }
    )
    result = response.json()
    return result.get("response", "No response from model").strip()

def _extract_sql(raw_text):
    # Handle model outputs like "SQL: ...", markdown fences, or extra prose.
    text = raw_text.strip()
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"^\s*sql\s*:\s*", "", text, flags=re.IGNORECASE)

    lowered = text.lower()
    select_idx = lowered.find("select")
    with_idx = lowered.find("with")

    start_idx = -1
    if select_idx != -1 and with_idx != -1:
        start_idx = min(select_idx, with_idx)
    elif select_idx != -1:
        start_idx = select_idx
    elif with_idx != -1:
        start_idx = with_idx

    if start_idx > 0:
        text = text[start_idx:]

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

def generate_sql(user_query, table_name="nutrition", db_path="app/db/nutrition.db"):
    schema = get_schema(table_name=table_name, db_path=db_path)
    columns = get_table_columns(table_name=table_name, db_path=db_path)

    system_prompt = f"""
You are a strict SQLite SQL generator.

Your output is evaluated automatically. You will be penalized for using incorrect column names.
Treat the schema as STRICT, mandatory constraints (not guidance).

Hard rules:
1) Use ONLY table `{table_name}`.
   - NEVER use any other table name (for example: nutrition, data, dataset, table1).
2) Use ONLY column names that appear in the schema.
3) Always copy column names exactly as provided.
4) Do not simplify, shorten, or rename columns.
   - Invalid: protein_value
   - Valid: protein
5) Use snake_case names exactly as defined in schema.
6) For text comparisons, use case-insensitive matching:
   - LOWER(column_name) = 'value_in_lowercase'
7) For percentage/rate calculations, avoid NULL results:
   - Use NULLIF(denominator, 0) for division safety
   - Wrap final metric with COALESCE(..., 0)
8) Return ONLY executable SQLite SQL.
9) Do not output markdown, comments, or explanations.
"""

    user_prompt = f"""
Schema (STRICT):
{schema}

User question:
{user_query}

Generate exactly one SQLite SQL query that follows all rules.
"""
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

