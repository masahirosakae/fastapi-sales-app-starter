from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3, os, json
from datetime import datetime
from starlette.middleware.sessions import SessionMiddleware
from passlib.hash import pbkdf2_sha256 as hasher
# from passlib.hash import bcrypt


APP_DIR = os.path.dirname(__file__)
# DB_PATH = os.path.join(APP_DIR, "app.db")
SCHEMA = os.path.join(APP_DIR, "schema.sql")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
DB_URL = os.getenv("DATABASE_URL", os.path.join(APP_DIR, "app.db"))
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


def get_db():
    conn = sqlite3.connect(DB_URL)   # DB_PATH
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    with open(SCHEMA, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit(); conn.close()

if not os.path.exists(DB_URL):   # DB_PATH
    init_db()

def current_user(request: Request):
    return request.session.get("user")

def require_login(request: Request):
    if not current_user(request):
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)

app = FastAPI(title="Customer & Cast Sales")
# app.add_middleware(SessionMiddleware, secret_key="change-this-to-a-long-random-string")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory=os.path.join(APP_DIR,"static")), name="static")
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))

def init_db_if_needed():
    conn = get_db()
    with open(os.path.join(APP_DIR, "schema.sql"), "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT DEFAULT 'admin'
    );
    """)

    cnt = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if cnt == 0:
        if ADMIN_PASSWORD:
            conn.execute(
                "INSERT INTO users(username, password_hash, role) VALUES (?,?,?)",
                (ADMIN_USER, hasher.hash(ADMIN_PASSWORD), "admin")
            )
            print(f"[INIT] admin user created: {ADMIN_USER} / (password set from env)")
        else:
            print("[INIT] no admin user created. Set ADMIN_PASSWORD or run app/reset_admin.py.")

    conn.commit(); conn.close()

init_db_if_needed()

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, next: str = "/"):
    # すでにログインしていればリダイレクト
    if current_user(request):
        return RedirectResponse(url=next or "/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "next": next, "error": ""})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), next: str = Form("/")):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    # if not row or not bcrypt.verify(password, row["password_hash"]):
    if not row or not hasher.verify(password, row["password_hash"]):
        # エラー表示
        return templates.TemplateResponse("login.html", {"request": request, "next": next, "error": "ユーザー名またはパスワードが違います。"})
    # セッションに保存
    request.session["user"] = {"id": row["id"], "username": row["username"], "role": row["role"]}
    return RedirectResponse(url=next or "/", status_code=303)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, start: str | None = None, end: str | None = None):
    redir = require_login(request)
    if redir: return redir
    """
    start / end は 'YYYY-MM' または 'YYYY-MM-DD' を想定。
    month指定('YYYY-MM')の場合は自動で月初〜月末になるように扱います。
    """
    def normalize(d: str | None, is_start=True):
        if not d: return None
        if len(d) == 7:  # 'YYYY-MM'
            return f"{d}-01" if is_start else f"{d}-31"
        return d

    start_d = normalize(start, True)
    end_d   = normalize(end, False)

    where = "WHERE 1=1"
    params: list = []
    if start_d:
        where += " AND date >= ?"
        params.append(start_d)
    if end_d:
        where += " AND date <= ?"
        params.append(end_d)

    conn = get_db()

    total_sales = conn.execute(
        f"SELECT IFNULL(SUM(amount),0) AS s FROM sales {where}",
        params
    ).fetchone()["s"]

    rows = conn.execute(
        f"""
        SELECT substr(date,1,7) AS ym, SUM(amount) AS total
        FROM sales
        {where}
        GROUP BY ym
        ORDER BY ym
        """,
        params
    ).fetchall()
    monthly = [{"ym": r["ym"], "total": r["total"]} for r in rows]

    rows = conn.execute(
        f"""
        SELECT c.name AS cast, SUM(s.amount) AS total
        FROM sales s
        JOIN casts c ON c.id = s.cast_id
        {where.replace('date','s.date')}
        GROUP BY c.id
        ORDER BY total DESC
        """,
        params
    ).fetchall()
    by_cast = [{"cast": r["cast"], "total": r["total"]} for r in rows]

    rows = conn.execute(
        f"""
        SELECT cu.name AS name,
               COUNT(*)      AS visits,
               AVG(s.amount) AS avg_amount,
               SUM(s.amount) AS total_amount
        FROM sales s
        JOIN customers cu ON cu.id = s.customer_id
        {where.replace('date','s.date')}
        GROUP BY cu.id
        HAVING visits > 0
        ORDER BY total_amount DESC
        """,
        params
    ).fetchall()
    customers = [
        {"name": r["name"], "visits": r["visits"], "avg_amount": r["avg_amount"], "total_amount": r["total_amount"]}
        for r in rows
    ]

    months = conn.execute(
        "SELECT DISTINCT substr(date,1,7) AS ym FROM sales ORDER BY ym DESC"
    ).fetchall()
    month_list = [r["ym"] for r in months]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_sales": total_sales,
        "monthly_json": json.dumps(monthly, ensure_ascii=False),
        "cast_json": json.dumps(by_cast, ensure_ascii=False),
        "customers_json": json.dumps(customers, ensure_ascii=False),
        "start": start or "",
        "end": end or "",
        "month_list": month_list
    })


@app.get("/customers", response_class=HTMLResponse)
def customers(request: Request, q: str|None=None):
    redir = require_login(request)
    if redir: return redir
    conn = get_db()
    rows = conn.execute("SELECT * FROM customers WHERE (? IS NULL) OR name LIKE ? ORDER BY name", (q, f"%{q}%" if q else None)).fetchall()
    return templates.TemplateResponse("customers.html", {"request": request, "rows": rows, "q": q or ""})

@app.post("/customers/add")
def add_customer(name: str = Form(...), birthday: str = Form(None)):
    conn = get_db()
    age = None
    if birthday:
        try:
            b = datetime.strptime(birthday, "%Y-%m-%d").date()
            td = datetime.today().date()
            age = td.year - b.year - ((td.month, td.day) < (b.month, b.day))
        except: pass
    conn.execute("INSERT OR IGNORE INTO customers(name, birthday, age) VALUES (?,?,?)", (name, birthday, age))
    conn.commit()
    return RedirectResponse(url="/customers", status_code=303)

@app.get("/casts", response_class=HTMLResponse)
def casts(request: Request):
    redir = require_login(request)
    if redir: return redir
    conn = get_db()
    rows = conn.execute("SELECT * FROM casts ORDER BY name").fetchall()
    return templates.TemplateResponse("casts.html", {"request": request, "rows": rows})

@app.post("/casts/add")
def add_cast(name: str = Form(...), joined_year: int = Form(None)):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO casts(name, joined_year) VALUES (?,?)", (name, joined_year))
    conn.commit()
    return RedirectResponse(url="/casts", status_code=303)

@app.get("/sales", response_class=HTMLResponse)
def sales(request: Request):
    redir = require_login(request)
    if redir: return redir
    conn = get_db()
    sales = conn.execute("SELECT s.id, s.date, cu.name customer, ca.name cast, s.amount FROM sales s JOIN customers cu ON cu.id=s.customer_id JOIN casts ca ON ca.id=s.cast_id ORDER BY s.date DESC, s.id DESC").fetchall()
    customers = conn.execute("SELECT id,name FROM customers ORDER BY name").fetchall()
    casts = conn.execute("SELECT id,name FROM casts ORDER BY name").fetchall()
    return templates.TemplateResponse("sales.html", {"request": request, "sales": sales, "customers": customers, "casts": casts})

@app.post("/sales/add")
def add_sale(date: str = Form(...), customer_id: int = Form(...), cast_id: int = Form(...), amount: int = Form(...)):
    conn = get_db()
    conn.execute("INSERT INTO sales(date, customer_id, cast_id, amount) VALUES (?,?,?,?)", (date, int(customer_id), int(cast_id), int(amount)))
    conn.execute("""UPDATE customers SET 
        visit_count=(SELECT COUNT(*) FROM sales WHERE customer_id=customers.id),
        total_amount=(SELECT IFNULL(SUM(amount),0) FROM sales WHERE customer_id=customers.id),
        avg_amount=(SELECT IFNULL(AVG(amount),0) FROM sales WHERE customer_id=customers.id),
        first_visit=(SELECT MIN(date) FROM sales WHERE customer_id=customers.id)""")
    conn.commit()
    return RedirectResponse(url="/sales", status_code=303)
