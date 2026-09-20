# Changhe

Historical knowledge backend for the Changhe app.

## Development

Requires Python 3.13.

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest -q
```

Start PostgreSQL for local development:

```powershell
docker compose up -d db
```

Health check: `GET http://localhost:8000/health/` returns `{"status": "ok"}`.
