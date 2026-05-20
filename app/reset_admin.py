from getpass import getpass
import os
import sqlite3

from passlib.hash import pbkdf2_sha256 as hasher

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

username = os.getenv("ADMIN_USER", "admin")
password = os.getenv("ADMIN_PASSWORD")

if not password:
    password = getpass("New admin password: ")
    confirm = getpass("Confirm admin password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")

if not password:
    raise SystemExit("Admin password is required.")

pw = hasher.hash(password)

conn.execute("""
INSERT INTO users(username, password_hash, role)
VALUES (?, ?, ?)
ON CONFLICT(username)
DO UPDATE SET password_hash=excluded.password_hash, role=excluded.role
""", (username, pw, "admin"))

conn.commit(); conn.close()
print(f"Admin user is ready: username={username}")
