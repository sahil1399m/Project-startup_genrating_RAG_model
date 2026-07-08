"""
mentor_db.py — PostgreSQL (Supabase) persistence for Mentor conversations.
"""

import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime


# ── Secret Resolution (works locally AND on Streamlit Cloud) ──────────────────

def _get_secret(key: str, default: str = None) -> str:
    val = os.environ.get(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


# ── Connection ─────────────────────────────────────────────────────────────────

def _conn() -> psycopg2.extensions.connection:
    host = _get_secret("DB_HOST")
    if not host:
        raise RuntimeError(
            "DB_HOST is not set. Add it to Streamlit Cloud secrets or your .env file."
        )
    return psycopg2.connect(
        host=host,
        port=_get_secret("DB_PORT", "5432"),
        database=_get_secret("DB_NAME"),
        user=_get_secret("DB_USER"),
        password=_get_secret("DB_PASSWORD"),
        sslmode="require",
        connect_timeout=10,
    )


# ── Schema ─────────────────────────────────────────────────────────────────────

_db_initialized = False


def init_mentor_db() -> None:
    global _db_initialized
    if _db_initialized:
        return
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS mentor_sessions (
            id          SERIAL PRIMARY KEY,
            session_id  TEXT    NOT NULL UNIQUE,
            blueprint_id INTEGER,
            user_email  TEXT,
            sector      TEXT,
            stage       TEXT,
            created_at  TEXT    NOT NULL,
            last_active TEXT    NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS mentor_messages (
            id          SERIAL PRIMARY KEY,
            session_id  TEXT    NOT NULL REFERENCES mentor_sessions(session_id) ON DELETE CASCADE,
            role        TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            intent      TEXT,
            citations   TEXT,
            tools_used  TEXT,
            timestamp   TEXT    NOT NULL
        );
        """)
        c.commit()
    _db_initialized = True


# ── Write ──────────────────────────────────────────────────────────────────────

def save_mentor_session(*, session_id, blueprint_id, user_email, sector, stage) -> None:
    init_mentor_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO mentor_sessions
                (session_id, blueprint_id, user_email, sector, stage, created_at, last_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET last_active = EXCLUDED.last_active
        """, (session_id, blueprint_id, user_email, sector, stage, now, now))
        c.commit()


def save_mentor_message(*, session_id, role, content, intent="",
                        citations=None, tools_used=None) -> None:
    init_mentor_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO mentor_messages
                (session_id, role, content, intent, citations, tools_used, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session_id, role, content, intent,
            json.dumps(citations or []),
            json.dumps(tools_used or []),
            now,
        ))
        cur.execute(
            "UPDATE mentor_sessions SET last_active=%s WHERE session_id=%s",
            (now, session_id)
        )
        c.commit()


# ── Read ───────────────────────────────────────────────────────────────────────

def get_mentor_messages(session_id: str) -> list[dict]:
    init_mentor_db()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT role, content, intent, citations, tools_used, timestamp
            FROM mentor_messages
            WHERE session_id = %s
            ORDER BY id ASC
        """, (session_id,))
        result = []
        for r in cur.fetchall():
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
    init_mentor_db()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM mentor_sessions
            WHERE blueprint_id = %s
            ORDER BY last_active DESC
        """, (blueprint_id,))
        return [dict(r) for r in cur.fetchall()]


def get_sessions_for_user(user_email: str) -> list[dict]:
    init_mentor_db()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM mentor_sessions
            WHERE user_email = %s
            ORDER BY last_active DESC
        """, (user_email,))
        return [dict(r) for r in cur.fetchall()]


# ── Init on import ─────────────────────────────────────────────────────────────
init_mentor_db()