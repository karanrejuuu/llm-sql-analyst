# LLM SQL Analyst

An interactive Streamlit app that lets users upload a CSV/Excel dataset, ask questions in natural language, generate SQL with a local LLM (Ollama), and view query results instantly.

## Features

- Upload CSV (`.csv`) and Excel (`.xlsx`, `.xls`) files
- Automatically loads uploaded data into SQLite (`uploaded_data` table)
- Normalizes column names internally for stable SQL generation
- Preserves original column names in displayed results
- Converts natural language to SQL using a strict, schema-aware prompt
- Validates generated SQL for safety (read-only, correct table)
- Shows generated SQL and result table in the UI

## Project Structure

```text
app/
├── ui/
│   └── app.py               # Streamlit UI + upload/query/result flow
├── services/
│   ├── llm_service.py       # NL -> SQL generation + repair/sanity checks
│   └── db_service.py        # SQL execution against SQLite
└── db/                      # Runtime DB files (gitignored)
```

## Requirements

- Python 3.10+
- Ollama running locally
- A pulled model compatible with your setup (default in code: `mistral`)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the App

From project root:

```bash
streamlit run app/ui/app.py
```

## How It Works

1. User uploads dataset in UI
2. App reads file into pandas DataFrame
3. DataFrame is written to SQLite table `uploaded_data`
4. App fetches table schema and sends strict prompt to LLM
5. LLM returns SQL
6. App validates SQL and executes it
7. Results are displayed in Streamlit

## Notes

- SQL generation is constrained to `SELECT`-style analysis.
- If the model returns noisy output (markdown/prefix text), the app sanitizes it before execution.
- Runtime DB files are intentionally ignored from git.

## Troubleshooting

- **`ModuleNotFoundError: streamlit`**
  - Install requirements in your active environment.
- **No response from model**
  - Ensure Ollama is running and the configured model is available.
- **Malformed CSV errors**
  - The app includes fallback CSV parsing and skips bad rows when needed.

## Future Improvements

- Query history sidebar
- Schema preview panel in UI
- Chart visualization for aggregate outputs
- Better typed SQL validation (column-level checks)
