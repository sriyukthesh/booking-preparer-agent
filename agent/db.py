import sqlite3
import json

DB_PATH = "agent_state.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Trace logs for Agent UI
    c.execute('''
        CREATE TABLE IF NOT EXISTS trace_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            node_name TEXT,
            state_data TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Idempotency and recovery tracking
    c.execute('''
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            key TEXT PRIMARY KEY,
            action TEXT,
            status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Test runner results
    c.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_case TEXT,
            expected TEXT,
            actual TEXT,
            status TEXT,
            evidence TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_trace(session_id: str, node_name: str, state_data: dict, message: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO trace_logs (session_id, node_name, state_data, message) VALUES (?, ?, ?, ?)',
              (session_id, node_name, json.dumps(state_data), message))
    conn.commit()
    conn.close()

def get_traces(session_id: str = None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if session_id:
        c.execute('SELECT * FROM trace_logs WHERE session_id = ? ORDER BY timestamp ASC', (session_id,))
    else:
        c.execute('SELECT * FROM trace_logs ORDER BY timestamp DESC LIMIT 100')
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

def save_test_result(test_case: str, expected: str, actual: str, status: str, evidence: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO test_results (test_case, expected, actual, status, evidence) VALUES (?, ?, ?, ?, ?)',
              (test_case, expected, actual, status, json.dumps(evidence)))
    conn.commit()
    conn.close()

def check_idempotency(key: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT status FROM idempotency_keys WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    return row is not None

def set_idempotency(key: str, action: str, status: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO idempotency_keys (key, action, status) VALUES (?, ?, ?)',
              (key, action, status))
    conn.commit()
    conn.close()