import os
import json
import sqlite3

from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app.db"
)

DB_PATH = DATABASE_URL.replace("sqlite:///", "", 1)

Path(DB_PATH).parent.mkdir(
    parents=True,
    exist_ok=True
)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                system_prompt TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session
            ON messages(session_id, id)
        """)


def get_system_prompt(session_id):
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT system_prompt FROM sessions
            WHERE session_id = ?
            """,
            (session_id,)
        ).fetchone()

    return row["system_prompt"] if row else None


def get_messages(session_id):
    with get_db() as conn:

        rows = conn.execute(
            """
            SELECT role, content, metadata
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,)
        ).fetchall()

    messages = []

    for row in rows:
        message = {
            "role": row["role"],
            "content": row["content"]
        }

        if row["metadata"]:
            message["metadata"] = json.loads(
                row["metadata"]
            )

        messages.append(message)

    return messages


def save_exchange(
    session_id,
    system_prompt,
    user_message,
    assistant_reply,
    metadata
):
    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    with get_db() as conn:

        conn.execute(
            """
            INSERT INTO sessions (
                session_id, system_prompt
            )
            VALUES (?, ?)
            ON CONFLICT(session_id)
            DO UPDATE SET
                system_prompt = excluded.system_prompt
            """,
            (session_id, system_prompt)
        )

        conn.executemany(
            """
            INSERT INTO messages (
                session_id,
                role,
                content,
                metadata,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    session_id,
                    "user",
                    user_message,
                    None,
                    timestamp
                ),
                (
                    session_id,
                    "assistant",
                    assistant_reply,
                    json.dumps(metadata),
                    timestamp
                )
            ]
        )


def session_exists(session_id):
    with get_db() as conn:

        row = conn.execute(
            """
            SELECT 1 FROM sessions
            WHERE session_id = ?
            """,
            (session_id,)
        ).fetchone()

    return row is not None


def check_database():
    with get_db() as conn:
        conn.execute("SELECT 1")

    return True