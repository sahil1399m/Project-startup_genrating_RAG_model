"""
mentor_db.py
────────────
Mentor conversation persistence.
Kept in a SEPARATE file so history_db.py is never touched.
Uses the same blueprint_history.db file via a new table.

Schema
------
mentor_sessions      — one row per mentor session (linked to blueprint)
mentor_messages      — individual turns in the conversation
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("blueprint_history.db")


# ── Connection ─────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_mentor_db() -> None:
    """
    Creates mentor tables in the existing blueprint_history.db.
    Safe to call multiple times — uses IF NOT EXISTS.
    """
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS mentor_sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT    NOT NULL UNIQUE,
            blueprint_id    INTEGER,
            user_email      TEXT,
            sector          TEXT,
            stage           TEXT,
            created_at      TEXT    NOT NULL,
            last_active     TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mentor_messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT    NOT NULL
                            REFERENCES mentor_sessions(session_id)
                            ON DELETE CASCADE,
            role            TEXT    NOT NULL,
            content         TEXT    NOT NULL,
            intent          TEXT,
            citations       TEXT,
            tools_used      TEXT,
            timestamp       TEXT    NOT NULL
        );
        """)


# ── Write ──────────────────────────────────────────────────────────────────────

def save_mentor_session(
    *,
    session_id: str,
    blueprint_id: int | None,
    user_email: str,
    sector: str,
    stage: str,
) -> None:
    """
    Upsert a mentor session row.
    Call this when a session is first created.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute("""
            INSERT INTO mentor_sessions
                (session_id, blueprint_id, user_email, sector, stage, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET last_active=excluded.last_active
        """, (session_id, blueprint_id, user_email, sector, stage, now, now))
        c.commit()


def save_mentor_message(
    *,
    session_id: str,
    role: str,
    content: str,
    intent: str = "",
    citations: list | None = None,
    tools_used: list | None = None,
) -> None:
    """
    Append one message turn to a session.
    role: 'user' or 'assistant'
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute("""
            INSERT INTO mentor_messages
                (session_id, role, content, intent, citations, tools_used, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            role,
            content,
            intent,
            json.dumps(citations or []),
            json.dumps(tools_used or []),
            now,
        ))
        # Update last_active on session
        c.execute(
            "UPDATE mentor_sessions SET last_active=? WHERE session_id=?",
            (now, session_id)
        )
        c.commit()


# ── Read ───────────────────────────────────────────────────────────────────────

def get_mentor_messages(session_id: str) -> list[dict]:
    """
    Returns all messages for a session in chronological order.
    """
    with _conn() as c:
        rows = c.execute("""
            SELECT role, content, intent, citations, tools_used, timestamp
            FROM mentor_messages
            WHERE session_id = ?
            ORDER BY id ASC
        """, (session_id,)).fetchall()

    result = []
    for r in rows:
        result.append({
            "role":       r["role"],
            "content":    r["content"],
            "intent":     r["intent"] or "",
            "citations":  json.loads(r["citations"] or "[]"),
            "tools_used": json.loads(r["tools_used"] or "[]"),
            "timestamp":  r["timestamp"],
        })
    return result


def get_sessions_for_blueprint(blueprint_id: int) -> list[dict]:
    """
    Returns all mentor sessions linked to a blueprint.
    """
    with _conn() as c:
        rows = c.execute("""
            SELECT * FROM mentor_sessions
            WHERE blueprint_id = ?
            ORDER BY last_active DESC
        """, (blueprint_id,)).fetchall()
    return [dict(r) for r in rows]


def get_sessions_for_user(user_email: str) -> list[dict]:
    """
    Returns all mentor sessions for a user ordered by most recent.
    """
    with _conn() as c:
        rows = c.execute("""
            SELECT * FROM mentor_sessions
            WHERE user_email = ?
            ORDER BY last_active DESC
        """, (user_email,)).fetchall()
    return [dict(r) for r in rows]


# ── Init on import ─────────────────────────────────────────────────────────────
init_mentor_db()