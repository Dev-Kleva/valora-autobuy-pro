import uuid
import sqlite3
import os
from typing import Optional

import tempfile

DB_PATH = os.environ.get("SQLITE_DB_PATH")
if not DB_PATH:
    DB_PATH = os.path.join(tempfile.gettempdir(), "autobuy.db")


def init_db():
    """Initialize database with users and sessions tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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
    try:
        conn = sqlite3.connect(DB_PATH)
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
        return None


def authenticate_user(username: str, password: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return None
    
    token = str(uuid.uuid4())
    cursor.execute("INSERT INTO sessions (token, username) VALUES (?, ?)", (token, username))
    conn.commit()
    conn.close()
    return token


def get_user_by_token(token: str) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
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
