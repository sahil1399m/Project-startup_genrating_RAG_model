"""
mentor_db.py — PostgreSQL (Supabase) persistence for Mentor conversations.
"""

import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


# ── Connection ─────────────────────────────────────────────────────────────────

def _conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode="require"
    )


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_mentor_db() -> None:
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


# ── Write ──────────────────────────────────────────────────────────────────────

def save_mentor_session(*, session_id, blueprint_id, user_email, sector, stage) -> None:
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
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM mentor_sessions
            WHERE blueprint_id = %s
            ORDER BY last_active DESC
        """, (blueprint_id,))
        return [dict(r) for r in cur.fetchall()]


def get_sessions_for_user(user_email: str) -> list[dict]:
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