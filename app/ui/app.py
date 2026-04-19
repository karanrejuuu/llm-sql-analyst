import streamlit as st
import pandas as pd
import sqlite3
import re
import sys
import os
import inspect

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from services.llm_service import generate_sql
from services.db_service import execute_query

DB_PATH = "app/db/nutrition.db"
TABLE_NAME = "uploaded_data"

def normalize_column_name(column_name):
    # Convert user-facing headers into SQL-safe snake_case names.
    normalized = re.sub(r"[^0-9a-zA-Z]+", "_", str(column_name).strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        normalized = "column"
    if normalized[0].isdigit():
        normalized = f"col_{normalized}"
    return normalized

def build_column_mapping(columns):
    # Ensure every normalized column name is unique for SQLite.
    used = set()
    mapping = {}
    for original in columns:
        base = normalize_column_name(original)
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        used.add(candidate)
        mapping[original] = candidate
    return mapping

def persist_uploaded_data(df):
    # Save normalized data to SQLite so LLM can query predictable names.
    column_mapping = build_column_mapping(df.columns)
    normalized_df = df.rename(columns=column_mapping)
    conn = sqlite3.connect(DB_PATH)
    normalized_df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
    conn.close()
    reverse_mapping = {v: k for k, v in column_mapping.items()}
    return column_mapping, reverse_mapping

def make_result_header_from_query(user_query):
    # Build a short, readable header from the user's question.
    q = user_query.lower().strip()
    tokens = re.findall(r"[a-zA-Z0-9]+", q)
    stop_words = {
        "show", "the", "a", "an", "of", "for", "to", "in", "on", "with",
        "and", "or", "is", "are", "was", "were", "what", "how", "many",
        "number", "count", "me", "give", "get", "list", "tell",
    }
    meaningful = [token for token in tokens if token not in stop_words]

    if any(word in q for word in ["surviv", "alive"]):
        return "Survival Count" if "number" in q or "count" in q else "Survival Rate"
    if any(word in q for word in ["average", "avg", "mean"]):
        return "Average Value"
    if any(word in q for word in ["sum", "total"]):
        return "Total Value"
    if any(word in q for word in ["max", "highest", "top"]):
        return "Top Result"
    if any(word in q for word in ["min", "lowest"]):
        return "Lowest Result"
    if any(word in q for word in ["percent", "percentage", "rate"]):
        return "Percentage"

    if not meaningful:
        return "Result"
    return " ".join(token.capitalize() for token in meaningful[:3])

def format_result_headers(df, user_query):
    # For single-metric outputs, replace noisy SQL aliases with a neat label.
    if len(df.columns) != 1:
        return df

    current_header = str(df.columns[0]).strip()
    looks_noisy = (
        len(current_header) > 24
        or "(" in current_header
        or "_" in current_header
        or current_header.lower() in {"result", "value"}
    )
    if not looks_noisy:
        return df

    better_header = make_result_header_from_query(user_query)
    return df.rename(columns={current_header: better_header})

def generate_sql_for_uploaded_table(user_query):
    # Support both old and new llm_service signatures during hot-reload.
    params = inspect.signature(generate_sql).parameters
    if "table_name" in params and "db_path" in params:
        return generate_sql(
            user_query,
            table_name=TABLE_NAME,
            db_path=DB_PATH,
        )
    return generate_sql(user_query)

def validate_generated_sql(sql_query, allowed_table, allowed_columns):
    # Block unsafe or incorrect SQL before execution.
    lowered = sql_query.strip().lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return "Only SELECT queries are allowed."
    if f"from {allowed_table.lower()}" not in lowered and f'from "{allowed_table.lower()}"' not in lowered:
        return f"Generated SQL must query only `{allowed_table}`."
    if " from nutrition" in lowered or " join nutrition" in lowered:
        return "Generated SQL referenced `nutrition`, but uploaded dataset uses `uploaded_data`."
    for blocked in ["drop ", "delete ", "update ", "insert ", "alter ", "truncate "]:
        if blocked in lowered:
            return "Only read-only SQL is allowed."
    if not allowed_columns:
        return "No columns detected from uploaded file."
    return None

st.set_page_config(
    page_title="LLM SQL Analyst",
    layout="wide",
)

st.title("LLM SQL Analyst")
st.caption("Upload a CSV, ask questions in plain English, get SQL-powered answers.")
st.write("")

# ---- Section 1: Upload ----
st.subheader("1) Upload Dataset")
uploaded_file = st.file_uploader(
    "Choose a CSV or Excel file",
    type=["csv", "xlsx", "xls"],
    help="Upload a dataset to start analysis.",
)
df = None

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    try:
        if file_name.endswith(".csv"):
            # Parse CSV uploads with fallback for malformed rows.
            try:
                df = pd.read_csv(uploaded_file)
            except pd.errors.ParserError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, engine="python", on_bad_lines="skip")
                st.warning("Some malformed CSV rows were skipped while reading the file.")
        elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
            # Parse Excel uploads.
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file format.")
            df = None

        if df is not None:
            st.success(f"Uploaded: {uploaded_file.name}")
            st.write("Preview (first 5 rows):")
            st.dataframe(df.head(), use_container_width=True)
            st.caption(f"Rows: {len(df)} | Columns: {len(df.columns)}")
            st.session_state["uploaded_df"] = df
    except Exception as e:
        st.error(f"Failed to read file: {e}")
else:
    st.info("No file uploaded yet.")

st.write("")

# ---- Section 2: Query ----
st.subheader("2) Ask a question")
user_query = st.text_input(
    "What do you want to know from this data?",
    placeholder="e.g., Top 5 products by sales",
)
run_button = st.button("Run Analysis")

st.write("")

# ---- Section 4: Results ----
st.subheader("3) Results")
if run_button:
    if df is None:
        st.warning("Please upload a CSV or Excel file first.")
    elif not user_query.strip():
        st.warning("Please enter a question before running analysis.")
    else:
        try:
            with st.spinner("Analyzing your data... this can take a few seconds."):
                column_mapping, reverse_mapping = persist_uploaded_data(df)
                sql_query = generate_sql_for_uploaded_table(user_query)
                sql_error = validate_generated_sql(
                    sql_query,
                    allowed_table=TABLE_NAME,
                    allowed_columns=set(column_mapping.values()),
                )
                if sql_error:
                    raise ValueError(sql_error)
                query_result = execute_query(sql_query, db_path=DB_PATH)

            st.subheader("Generated SQL")
            st.code(sql_query, language="sql")

            if isinstance(query_result, str):
                st.error(query_result)
            else:
                display_df = query_result.rename(
                    columns={col: reverse_mapping.get(col, col) for col in query_result.columns}
                )
                display_df = format_result_headers(display_df, user_query)
                if len(display_df.columns) == 1 and len(display_df) <= 20:
                    # Compact table keeps single-value answers left-aligned.
                    st.table(display_df)
                elif len(display_df) <= 20:
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        height=420,
                    )
        except Exception as e:
            st.error(f"Analysis failed: {e}")
else:
    st.caption("Upload a file, type a question, then click Run Analysis.")