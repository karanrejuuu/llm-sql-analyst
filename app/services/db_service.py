import sqlite3
import pandas as pd

def execute_query(sql, db_path="app/db/nutrition.db"):
    #executes sql on database and return dataframe

    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(sql,conn)
        return df
    except Exception as e:
        return f"Error: {e}"
    finally:
        conn.close()