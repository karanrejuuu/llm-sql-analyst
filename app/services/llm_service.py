import requests
import sqlite3
OLLAMA_URL = "http://localhost:11434/api/generate"

def normalize_nutrition_columns():
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

    conn = sqlite3.connect("app/db/nutrition.db")
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

def get_schema():
    #dynamically fetches table schema from sqlite
    normalize_nutrition_columns()
    conn=sqlite3.connect("app/db/nutrition.db")
    cursor = conn.cursor()

    #table info
    cursor.execute("PRAGMA table_info(nutrition)")
    columns_info = cursor.fetchall()

    conn.close()

    columns = [col[1] for col in columns_info]
    schema = f"""
    Table : nutrition
    Columns:
    """
    for col in columns:
        schema+=f"- {col}\n"
    return schema

def generate_sql(user_query):
    schema = get_schema()

    system_prompt = """
You are a strict SQLite SQL generator.

Your output is evaluated automatically. You will be penalized for using incorrect column names.
Treat the schema as STRICT, mandatory constraints (not guidance).

Hard rules:
1) Use ONLY table `nutrition`.
2) Use ONLY column names that appear in the schema.
3) Always copy column names exactly as provided.
4) Do not simplify, shorten, or rename columns.
   - Invalid: protein_value
   - Valid: protein
5) Use snake_case names exactly as defined in schema.
6) Return ONLY executable SQLite SQL.
7) Do not output markdown, comments, or explanations.
"""

    user_prompt = f"""
Schema (STRICT):
{schema}

User question:
{user_query}

Generate exactly one SQLite SQL query that follows all rules.
"""

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

