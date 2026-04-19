import sqlite3
import pandas as pd

def execute_query(sql):
    #executes sql on database and return dataframe

    conn = sqlite3.connect("app/db/nutrition.db")
    try:
        df = pd.read_sql_query(sql,conn)
        return df
    except Exception as e:
        return f"Error: {e}"
    finally:
        conn.close()