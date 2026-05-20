# FastAPI Sales App Starter

## Overview

FastAPI Sales App Starter is a small learning project for building a sales management web application with FastAPI, SQLite, server-side templates, and session-based login.

It is intended as a portfolio-friendly starter app that demonstrates basic backend structure, database initialization, authentication flow, and simple sales/customer screens without adding unnecessary production complexity.

## Features

- FastAPI application with HTML pages rendered by Jinja2
- SQLite schema for local development
- Login and logout using server-side sessions
- Sales/customer data views for a small business workflow
- CSV import helper for sample data setup
- Admin password reset script that avoids hard-coded passwords

## Tech Stack

- Python
- FastAPI
- Uvicorn
- Jinja2
- SQLite
- Passlib
- Starlette SessionMiddleware

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the initial database:

```bash
python - <<'PY'
import pathlib
import sqlite3

pathlib.Path("app").mkdir(exist_ok=True)
conn = sqlite3.connect("app/app.db")
conn.executescript(open("app/schema.sql", "r", encoding="utf-8").read())
conn.commit()
conn.close()
print("DB ready")
PY
```

Set admin credentials before the first run:

```bash
export ADMIN_USERNAME="replace-with-your-local-username"
export ADMIN_PASSWORD="replace-with-your-local-password"
```

On Windows PowerShell:

```powershell
$env:ADMIN_USERNAME = "replace-with-your-local-username"
$env:ADMIN_PASSWORD = "replace-with-your-local-password"
```

Start the app:

```bash
uvicorn app.main:app --reload
```

If you need to create or reset the admin user later, run:

```bash
python app/reset_admin.py
```

The reset script reads `ADMIN_USERNAME` and `ADMIN_PASSWORD` from environment variables. Both values are required.

## Security Note

This repository is prepared for public portfolio viewing. Local-only files such as `.venv/`, `.env`, SQLite database files, Python cache files, and pytest cache files are excluded from Git.

Do not commit real credentials, production secrets, or local database contents. For local development, pass secrets through environment variables.

## Portfolio Purpose

This project is a compact learning app that shows practical FastAPI fundamentals: routing, templates, SQLite persistence, session login, and simple operational screens. It is intentionally kept small so the code remains easy to read during portfolio review.
