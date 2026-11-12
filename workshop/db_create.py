# db_create.py
import sqlite3

NUMBERS = [
    ("0412345678", "active"),
    ("0498765432", "inactive"),
    ("0423456789", "active"),
    ("0434567890", "inactive"),
    ("0445678901", "active"),
    ("0456789012", "inactive"),
    ("0467890123", "inactive"),
]

conn = sqlite3.connect("mcp-a2a.db")
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS numbers (number TEXT PRIMARY KEY, status TEXT NOT NULL)")
cur.executemany("INSERT INTO numbers (number, status) VALUES (?, ?)", NUMBERS)
conn.commit()
conn.close()
