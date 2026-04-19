from .services.llm_service import generate_sql
from .services.db_service import execute_query

query = "Top 5 foods with highest protein"

# Step 1: Generate SQL
sql = generate_sql(query)
print("\nGenerated SQL:\n", sql)

# Step 2: Execute SQL
result = execute_query(sql)

print("\nQuery Result:\n")
print(result)