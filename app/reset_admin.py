from passlib.hash import pbkdf2_sha256 as hasher
import sqlite3, os

DB = os.path.join("app", "app.db")
os.makedirs("app", exist_ok=True)

conn = sqlite3.connect(DB)
conn.execute("""
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'admin'
)
""")

username = "admin"
password = "admin123"
pw = hasher.hash(password)

conn.execute("""
INSERT INTO users(username, password_hash, role)
VALUES (?, ?, ?)
ON CONFLICT(username)
DO UPDATE SET password_hash=excluded.password_hash, role=excluded.role
""", (username, pw, "admin"))

conn.commit(); conn.close()
print("Admin user is ready: username=admin / password=admin123")
