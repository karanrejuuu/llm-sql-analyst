import sys
import os
import streamlit as st

# Add the `app` directory to Python path for local imports.
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from services.llm_service import generate_sql

# Ensure the import path is correct relative to the project structure.
st.set_page_config(
    page_title="SQL Analyst",
    layout = "wide"
)

st.title("LLM SQL Analyst")
st.markdown("Ask questions in plain English and get SQL-powered insights.")
st.write("")

#sec 1 : csv upload
st.subheader("📂 Upload Dataset")
st.info("CSV upload will be added here.")
st.write("")

#sec 2: query input
st.subheader("🤔 Ask Your Question")
user_query = st.text_input(
    "Enter your questions : ",
    placeholder="e.g., Show top 5 high protein foods"
)
run_button = st.button("Run Query")
if run_button:
    if user_query.strip()=="":
        st.warning('Please enter a query.')
    else:
        sql_query = generate_sql(user_query)
        st.subheader("📃 Generated SQL")
        st.code(sql_query,language="sql")
st.write("")

#sec 3 : results
st.subheader("📊 Results ")
st.info("Query results will appear here.")