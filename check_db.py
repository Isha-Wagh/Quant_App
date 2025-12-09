import sqlite3, os

path = os.path.join("data", "ticks.db")
print("DB exists:", os.path.exists(path))

conn = sqlite3.connect(path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables:", cur.fetchall())

cur.execute("SELECT symbol, COUNT(*) FROM ticks GROUP BY symbol;")
print("Counts per symbol:", cur.fetchall())
