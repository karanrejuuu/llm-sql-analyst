import sqlite3
import pandas as pd

conn = sqlite3.connect("app/db/nutrition.db")
query = "SELECT * FROM nutrition LIMIT 5"

df = pd.read_sql_query(query, conn)

print("\n Query result")
print(df)

conn.close()