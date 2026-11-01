import sqlite3
import json
import os
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "analysis.db"
_memory_cache = {}

def _init_db():
    try:
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
    except Exception as e:
        print(f"[analysis_cache] SQLite init note: {e}")

_init_db()

def store_result(doc_id: str, result: dict):
    _memory_cache[doc_id] = result
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('INSERT OR REPLACE INTO documents (id, result) VALUES (?, ?)', (doc_id, json.dumps(result)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[analysis_cache] SQLite store note: {e}. Stored in memory.")

def get_result(doc_id: str) -> dict | None:
    if doc_id in _memory_cache:
        return _memory_cache[doc_id]
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT result FROM documents WHERE id = ?', (doc_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception as e:
        print(f"[analysis_cache] SQLite get note: {e}")
    return None
