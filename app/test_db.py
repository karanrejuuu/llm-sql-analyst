from app.services.db_service import execute_query

# Get table schema
query = "PRAGMA table_info(nutrition);"

result = execute_query(query)

print("\n=== TABLE SCHEMA ===\n")
print(result)