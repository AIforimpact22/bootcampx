# Streamlit POS + Inventory (Neon Postgres)

Streamlit-based POS + inventory app backed by Postgres (Neon).

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Configure database

Set `DATABASE_URL` (Neon typically requires `sslmode=require` in the URL).

Option A (Windows PowerShell):
```powershell
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require"
```

Option B: create a local `.env` file (see `.env.example`). The app loads it via `python-dotenv` if installed.

Option C: create `.streamlit/secrets.toml` (see `.streamlit/secrets.toml.example`).

## Run

```bash
streamlit run app.py
```

## Notes

- The app expects these tables to already exist: `cashiers`, `items`, `sales`.
- Triggers are assumed to exist:
  - `prevent_oversell` (blocks inserting sales beyond stock)
  - `decrement_stock_after_sale` (reduces stock after a sale)
