import kagglehub
import os
import pandas as pd

# Download dataset
path = kagglehub.dataset_download("adilshamim8/daily-food-and-nutrition-dataset")

print("Dataset path:", path)

# List files inside the folder
files = os.listdir(path)
print("Files in dataset:", files)

# Find CSV file
csv_file = None
for file in files:
    if file.endswith(".csv"):
        csv_file = file
        break

if csv_file is None:
    print("No CSV file found!")
else:
    csv_path = os.path.join(path, csv_file)
    print("CSV file found:", csv_path)

    # Load into pandas
    df = pd.read_csv(csv_path, on_bad_lines='skip')  # skips broken rows
    # Show first 5 rows
    print("\nFirst 5 rows:")
    print(df.head())

    # Show column names
    print("\nColumns:")
    print(df.columns)

#loading into database

import sqlite3

def normalize_nutrition_columns(conn):
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

#creates a db if it doesnt exist
conn = sqlite3.connect("app/db/nutrition.db")
#store dataframe as table
df.to_sql(
    "nutrition",
    conn, 
    if_exists="replace",
    index=False
)
normalize_nutrition_columns(conn)
print("\n Data succesfully stored in SQLite database..")
conn.close()