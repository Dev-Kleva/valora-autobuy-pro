import uuid
import sqlite3
import os
from typing import Optional
import time

import tempfile

DB_PATH = os.environ.get("SQLITE_DB_PATH")
if not DB_PATH:
    DB_PATH = os.path.join(tempfile.gettempdir(), "autobuy.db")


def _connect():
    """Create a sqlite3 connection with recommended pragmas for concurrency."""
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    try:
        # set busy timeout in milliseconds (30s) as a fallback
        conn.execute("PRAGMA busy_timeout = 30000;")
    except Exception:
        pass
    return conn


def init_db():
    """Initialize database with users and sessions tables"""
    # Open with a longer timeout and allow access from multiple threads/processes
    conn = _connect()
    cursor = conn.cursor()
    # Reduce locking contention by enabling WAL journal mode
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        # If PRAGMA fails, continue; WAL may not be supported on every filesystem
        pass
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)
    
    conn.commit()
    conn.close()


# Initialize database on import
init_db()


def register_user(username: str, password: str):
    attempts = 5
    delay = 0.05
    for i in range(attempts):
        conn = None
        try:
            conn = _connect()
            cursor = conn.cursor()
            user_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO users (id, username, password) VALUES (?, ?, ?)",
                (user_id, username, password)
            )
            conn.commit()
            conn.close()
            return {
                "id": user_id,
                "username": username,
                "password": password
            }
        except sqlite3.IntegrityError:
            if conn:
                conn.close()
            return None
        except sqlite3.OperationalError as e:
            # retry on busy/locked errors
            msg = str(e).lower()
            if conn:
                conn.close()
            if "database is locked" in msg and i < attempts - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    return None


def authenticate_user(username: str, password: str):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return None

    token = str(uuid.uuid4())
    attempts = 5
    delay = 0.05
    for i in range(attempts):
        try:
            cursor.execute("INSERT INTO sessions (token, username) VALUES (?, ?)", (token, username))
            conn.commit()
            conn.close()
            return token
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if "database is locked" in msg and i < attempts - 1:
                time.sleep(delay)
                delay *= 2
                continue
            conn.close()
            raise


def get_user_by_token(token: str) -> Optional[dict]:
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT u.id, u.username FROM users u JOIN sessions s ON u.username = s.username WHERE s.token = ?",
        (token,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return None
    
    return {
        "id": result[0],
        "username": result[1]
    }
