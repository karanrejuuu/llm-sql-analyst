# LLM SQL Analyst

A lightweight, production-focused Streamlit app that turns natural language questions into SQL for any uploaded CSV/Excel dataset.

Users can upload a file, ask a question in plain English, and instantly get:
- generated SQL,
- executed results,
- and cleanly rendered output in the UI.

---

## Why This Project

Most NL-to-SQL demos work only on one fixed schema.  
This project is built for **dynamic datasets**:

- Upload any tabular file (`.csv`, `.xlsx`, `.xls`)
- Auto-load it into SQLite
- Auto-detect schema
- Generate schema-aware SQL using a local LLM (Ollama + Mistral)

---

## Core Features

- **Dynamic Dataset Upload**
  - Supports CSV and Excel files.
- **Schema-Aware SQL Generation**
  - Prompts the LLM with strict live schema from uploaded data.
- **Safety Validation Layer**
  - Enforces read-only SQL and target-table checks.
- **Output Sanitization**
  - Cleans model noise (markdown fences, `SQL:` prefixes) before execution.
- **Column Normalization + Friendly Display**
  - Internally normalizes column names for SQL stability.
  - Displays output with readable headers in the UI.
- **Resilient File Parsing**
  - Handles malformed CSV rows with fallback parsing.

---

## Tech Stack

- **Frontend:** Streamlit
- **Backend:** Python
- **Database:** SQLite
- **LLM Runtime:** Ollama
- **Default Model:** Mistral

---

## Project Structure

```text
llm-sql-analyst/
├── app/
│   ├── ui/
│   │   └── app.py                 # Streamlit app flow (upload -> ask -> SQL -> results)
│   ├── services/
│   │   ├── llm_service.py         # NL->SQL generation, sanitization, repair logic
│   │   └── db_service.py          # SQLite query execution helper
│   └── db/
│       └── .gitkeep               # Keeps db folder in repo (runtime DB is ignored)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Setup

### 1) Clone repository

```bash
git clone https://github.com/YOUR_USERNAME/llm-sql-analyst.git
cd llm-sql-analyst
```

### 2) Create and activate virtual environment

```bash
python -m venv venv
```

Windows (PowerShell):

```bash
venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Start Ollama and pull model

```bash
ollama pull mistral
ollama serve
```

---

## Run

From project root:

```bash
streamlit run app/ui/app.py
```

Then in the app:
1. Upload dataset
2. Ask question in natural language
3. Click **Run Analysis**
4. Review generated SQL + result table

---

## Request Flow (Architecture)

1. File upload is read into a pandas DataFrame
2. DataFrame is stored as SQLite table `uploaded_data`
3. Live schema is extracted from SQLite
4. LLM receives strict system+user prompt with schema constraints
5. SQL output is sanitized and validated
6. Query executes through DB service
7. Results are rendered in Streamlit

---

## Safety and Reliability Choices

- Only analysis-style SQL is allowed (`SELECT`/CTE-style reads)
- Guardrails block unsafe operations (`DROP`, `DELETE`, `UPDATE`, etc.)
- Generated SQL must target uploaded table
- Repair pass attempts to fix invalid first draft SQL

---

## Known Limitations

- Quality depends on selected local model
- Very messy datasets may still require better normalization rules
- Complex multi-hop business logic questions can produce imperfect SQL

---

## Troubleshooting

- **`ModuleNotFoundError: streamlit`**
  - Install dependencies in active venv: `pip install -r requirements.txt`

  - Ensure Ollama is running and `mistral` is available
  - Check `OLLAMA_URL` in `.env` or `app/services/llm_service.py`

- **CSV parsing issues**
  - App retries malformed CSV with fallback parser and skips broken rows

- **Wrong SQL table references**
  - App validates table target and rejects invalid SQL before execution

---

## Roadmap

- Query history sidebar
- Schema explorer panel in UI
- Result charting for aggregate queries
- Stronger column-level SQL validator

---

## License

MIT (or update based on your preferred license).
