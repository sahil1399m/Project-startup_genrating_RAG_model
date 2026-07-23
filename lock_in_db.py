"""
lock_in_db.py — PostgreSQL persistence for LOCK IN feature.
Matches history_db.py pattern exactly (psycopg2, same _conn()).
"""

import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime


def _get_secret(key: str, default: str = None) -> str:
    val = os.environ.get(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


def _conn():
    return psycopg2.connect(
        host=_get_secret("DB_HOST"),
        port=_get_secret("DB_PORT", "5432"),
        database=_get_secret("DB_NAME"),
        user=_get_secret("DB_USER"),
        password=_get_secret("DB_PASSWORD"),
        sslmode="require",
        connect_timeout=10,
    )


_initialized = False

def init_tables() -> None:
    global _initialized
    if _initialized:
        return
    with _conn() as c:
        cur = c.cursor()

        # Founder profile
        cur.execute("""
        CREATE TABLE IF NOT EXISTS lock_in_profiles (
            id              SERIAL PRIMARY KEY,
            blueprint_id    INTEGER REFERENCES blueprints(id) ON DELETE CASCADE,
            user_email      TEXT,
            founder_data    JSONB,
            created_at      TIMESTAMPTZ DEFAULT now()
        );
        """)

        # Generated roadmap + agent outputs
        cur.execute("""
        CREATE TABLE IF NOT EXISTS lock_in_roadmaps (
            id                  SERIAL PRIMARY KEY,
            profile_id          INTEGER REFERENCES lock_in_profiles(id) ON DELETE CASCADE,
            blueprint_id        INTEGER,
            user_email          TEXT,
            market_research     JSONB,
            competitor_intel    JSONB,
            roadmap             JSONB,
            created_at          TIMESTAMPTZ DEFAULT now()
        );
        """)

        # Task progress
        cur.execute("""
        CREATE TABLE IF NOT EXISTS lock_in_tasks (
            id          SERIAL PRIMARY KEY,
            roadmap_id  INTEGER REFERENCES lock_in_roadmaps(id) ON DELETE CASCADE,
            task_id     TEXT,
            status      TEXT DEFAULT 'pending',
            notes       TEXT DEFAULT '',
            updated_at  TIMESTAMPTZ DEFAULT now()
        );
        """)

        c.commit()
    _initialized = True


# ── Profile ───────────────────────────────────────────────────────────────────

def save_profile(blueprint_id: int, user_email: str, founder_data: dict) -> int:
    init_tables()
    with _conn() as c:
        cur = c.cursor()
        # Upsert — one profile per blueprint
        cur.execute(
            "SELECT id FROM lock_in_profiles WHERE blueprint_id=%s AND user_email=%s",
            (blueprint_id, user_email)
        )
        existing = cur.fetchone()
        if existing:
            cur.execute(
                "UPDATE lock_in_profiles SET founder_data=%s WHERE id=%s RETURNING id",
                (json.dumps(founder_data), existing[0])
            )
            profile_id = existing[0]
        else:
            cur.execute(
                "INSERT INTO lock_in_profiles (blueprint_id, user_email, founder_data) VALUES (%s,%s,%s) RETURNING id",
                (blueprint_id, user_email, json.dumps(founder_data))
            )
            profile_id = cur.fetchone()[0]
        c.commit()
    return profile_id


def get_profile(blueprint_id: int, user_email: str) -> dict | None:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT * FROM lock_in_profiles WHERE blueprint_id=%s AND user_email=%s",
            (blueprint_id, user_email)
        )
        row = cur.fetchone()
        if not row:
            return None
        result = dict(row)
        result["founder_data"] = result["founder_data"] if isinstance(result["founder_data"], dict) else json.loads(result["founder_data"] or "{}")
        return result


# ── Roadmap ───────────────────────────────────────────────────────────────────

def save_roadmap(profile_id: int, blueprint_id: int, user_email: str,
                 market_research: dict, competitor_intel: dict, roadmap: dict) -> int:
    init_tables()
    with _conn() as c:
        cur = c.cursor()
        cur.execute(
            "SELECT id FROM lock_in_roadmaps WHERE profile_id=%s",
            (profile_id,)
        )
        existing = cur.fetchone()
        if existing:
            cur.execute(
                """UPDATE lock_in_roadmaps SET
                   market_research=%s, competitor_intel=%s, roadmap=%s
                   WHERE id=%s""",
                (json.dumps(market_research), json.dumps(competitor_intel),
                 json.dumps(roadmap), existing[0])
            )
            roadmap_id = existing[0]
        else:
            cur.execute(
                """INSERT INTO lock_in_roadmaps
                   (profile_id, blueprint_id, user_email, market_research, competitor_intel, roadmap)
                   VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                (profile_id, blueprint_id, user_email,
                 json.dumps(market_research), json.dumps(competitor_intel), json.dumps(roadmap))
            )
            roadmap_id = cur.fetchone()[0]
        c.commit()
    return roadmap_id


def get_roadmap(profile_id: int) -> dict | None:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM lock_in_roadmaps WHERE profile_id=%s", (profile_id,))
        row = cur.fetchone()
        if not row:
            return None
        result = dict(row)
        for field in ["market_research", "competitor_intel", "roadmap"]:
            val = result.get(field)
            if isinstance(val, str):
                try:
                    result[field] = json.loads(val)
                except Exception:
                    result[field] = {}
        return result


# ── Task Progress ─────────────────────────────────────────────────────────────

def get_task_statuses(roadmap_id: int) -> dict:
    """Returns {task_id: {status, notes}}"""
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM lock_in_tasks WHERE roadmap_id=%s", (roadmap_id,))
        rows = cur.fetchall()
    return {r["task_id"]: {"status": r["status"], "notes": r["notes"]} for r in rows}


def update_task(roadmap_id: int, task_id: str, status: str, notes: str = "") -> None:
    init_tables()
    with _conn() as c:
        cur = c.cursor()
        cur.execute(
            "SELECT id FROM lock_in_tasks WHERE roadmap_id=%s AND task_id=%s",
            (roadmap_id, task_id)
        )
        existing = cur.fetchone()
        if existing:
            cur.execute(
                "UPDATE lock_in_tasks SET status=%s, notes=%s, updated_at=now() WHERE id=%s",
                (status, notes, existing[0])
            )
        else:
            cur.execute(
                "INSERT INTO lock_in_tasks (roadmap_id, task_id, status, notes) VALUES (%s,%s,%s,%s)",
                (roadmap_id, task_id, status, notes)
            )
        c.commit()