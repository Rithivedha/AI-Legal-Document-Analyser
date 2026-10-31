import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "analysis.db"

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            result TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

_init_db()

def store_result(doc_id: str, result: dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO documents (id, result) VALUES (?, ?)', (doc_id, json.dumps(result)))
    conn.commit()
    conn.close()

def get_result(doc_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT result FROM documents WHERE id = ?', (doc_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None
