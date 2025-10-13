import csv, sqlite3, os

APP_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(APP_DIR, "app.db")
DATA_DIR = os.path.join(os.path.dirname(APP_DIR), "data")

def upsert_customer(cur, name, birthday=None, age=None, first_visit=None, visit_count=None, avg_amount=None, total_amount=None):
    if not name: 
        return
    cur.execute("INSERT OR IGNORE INTO customers(name) VALUES (?)", (name,))
    cur.execute("""UPDATE customers
        SET birthday = COALESCE(?, birthday),
            age = COALESCE(?, age),
            first_visit = COALESCE(?, first_visit),
            visit_count = COALESCE(?, visit_count),
            avg_amount = COALESCE(?, avg_amount),
            total_amount = COALESCE(?, total_amount)
        WHERE name = ?""",
        (birthday or None,
         int(age) if (age or "").strip().isdigit() else None,
         first_visit or None,
         int(visit_count) if (visit_count or "").strip().isdigit() else None,
         float(avg_amount) if (avg_amount or "").strip() not in ("", None) else None,
         int(str(total_amount).replace(",","")) if (total_amount or "").strip() not in ("", None) else None,
         name))

def upsert_cast(cur, name, joined_year=None):
    if not name:
        return
    cur.execute("INSERT OR IGNORE INTO casts(name) VALUES (?)", (name,))
    if joined_year and str(joined_year).strip():
        cur.execute("UPDATE casts SET joined_year=? WHERE name=?", (int(joined_year), name))

def import_casts(path, cur):
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            upsert_cast(cur, row.get("キャスト名","").strip(), row.get("年（入店）","").strip())

def import_customers(path, cur):
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            upsert_customer(cur,
                row.get("顧客名","").strip(),
                row.get("誕生日","").strip(),
                row.get("年齢","").strip(),
                row.get("初回来店日","").strip(),
                row.get("来店回数","").strip(),
                row.get("平均単価","").strip(),
                row.get("累計単価","").strip(),
            )

def import_sales(path, cur):
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            date = (row.get("来店日","") or "").strip()
            cname = (row.get("顧客名","") or "").strip()
            cast = (row.get("指名キャスト","") or "").strip()
            amount_raw = (row.get("売上","") or "0").replace(",","").strip()
            if not (date and cname and cast and amount_raw):
                continue
            amount = int(amount_raw)
            cur.execute("INSERT OR IGNORE INTO customers(name) VALUES (?)", (cname,))
            cur.execute("INSERT OR IGNORE INTO casts(name) VALUES (?)", (cast,))
            cid = cur.execute("SELECT id FROM customers WHERE name=?", (cname,)).fetchone()["id"]
            caid = cur.execute("SELECT id FROM casts WHERE name=?", (cast,)).fetchone()["id"]
            cur.execute("INSERT INTO sales(date, customer_id, cast_id, amount) VALUES (?,?,?,?)", (date, cid, caid, amount))
            # KPI更新
            cur.execute("""
                UPDATE customers SET 
                    visit_count = (SELECT COUNT(*) FROM sales WHERE customer_id = customers.id),
                    total_amount = (SELECT IFNULL(SUM(amount),0) FROM sales WHERE customer_id = customers.id),
                    avg_amount = (SELECT IFNULL(AVG(amount),0) FROM sales WHERE customer_id = customers.id),
                    first_visit = (SELECT MIN(date) FROM sales WHERE customer_id = customers.id)
            """)

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    files = {
      "キャスト名入力.csv": import_casts,
      "顧客データ顧客名入力.csv": import_customers,
      "顧客来店入力.csv": import_sales,
    }
    for fname, fn in files.items():
        p = os.path.join(DATA_DIR, fname)
        if os.path.exists(p):
            print(f"Importing: {fname}")
            fn(p, cur)
        else:
            print(f"Skip (not found): {fname}")
    conn.commit(); conn.close()
    print("Import finished ✅")
