"""
history_db.py  — SQLite persistence for Blueprint History.

Schema
------
blueprints         — one row per blueprint (metadata)
blueprint_sections — named JSON content sections per blueprint
blueprint_sources  — source links per blueprint
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("blueprint_history.db")


# ── Connection ────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db() -> None:
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS blueprints (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT    NOT NULL,
            original_query  TEXT    NOT NULL,
            rewritten_query TEXT,
            sector          TEXT,
            stage           TEXT,
            business_model  TEXT,
            market          TEXT,
            confidence      TEXT,
            is_favorite     INTEGER DEFAULT 0,
            user_email      TEXT,
            timestamp       TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS blueprint_sections (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            blueprint_id INTEGER NOT NULL REFERENCES blueprints(id) ON DELETE CASCADE,
            section_name TEXT    NOT NULL,
            content      TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS blueprint_sources (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            blueprint_id INTEGER NOT NULL REFERENCES blueprints(id) ON DELETE CASCADE,
            source_name  TEXT,
            source_url   TEXT
        );
        """)


# ── Write ─────────────────────────────────────────────────────────────────────

def save_blueprint(*, title, original_query, rewritten_query, sector, stage,
                   business_model, market, confidence, user_email,
                   sections: dict, sources: list) -> int:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO blueprints
               (title,original_query,rewritten_query,sector,stage,
                business_model,market,confidence,user_email,timestamp)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (title, original_query, rewritten_query, sector, stage,
             business_model, market, confidence, user_email, ts),
        )
        bp_id = cur.lastrowid
        for name, content in sections.items():
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            c.execute(
                "INSERT INTO blueprint_sections (blueprint_id,section_name,content) VALUES (?,?,?)",
                (bp_id, name, content),
            )
        for src in sources:
            c.execute(
                "INSERT INTO blueprint_sources (blueprint_id,source_name,source_url) VALUES (?,?,?)",
                (bp_id, src.get("name",""), src.get("url","")),
            )
        c.commit()
    return bp_id


# ── Read ──────────────────────────────────────────────────────────────────────

def list_blueprints(user_email=None) -> list:
    with _conn() as c:
        if user_email:
            rows = c.execute(
                "SELECT * FROM blueprints WHERE user_email=? ORDER BY id DESC",
                (user_email,),
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM blueprints ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def get_blueprint(blueprint_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM blueprints WHERE id=?", (blueprint_id,)).fetchone()
        if row is None:
            return None
        bp = dict(row)
        sec_rows = c.execute(
            "SELECT section_name,content FROM blueprint_sections WHERE blueprint_id=?",
            (blueprint_id,),
        ).fetchall()
        bp["sections"] = {}
        for sr in sec_rows:
            content = sr["content"]
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                pass
            bp["sections"][sr["section_name"]] = content
        src_rows = c.execute(
            "SELECT source_name,source_url FROM blueprint_sources WHERE blueprint_id=?",
            (blueprint_id,),
        ).fetchall()
        bp["sources"] = [{"name": r["source_name"], "url": r["source_url"]} for r in src_rows]
    return bp


def search_blueprints(query: str, user_email=None) -> list:
    like = f"%{query}%"
    with _conn() as c:
        if user_email:
            rows = c.execute(
                """SELECT * FROM blueprints
                   WHERE user_email=? AND (title LIKE ? OR original_query LIKE ?)
                   ORDER BY id DESC""",
                (user_email, like, like),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM blueprints WHERE title LIKE ? OR original_query LIKE ? ORDER BY id DESC",
                (like, like),
            ).fetchall()
    return [dict(r) for r in rows]


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_blueprint(blueprint_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM blueprints WHERE id=?", (blueprint_id,))
        c.commit()


def delete_all_blueprints(user_email=None) -> None:
    with _conn() as c:
        if user_email:
            c.execute("DELETE FROM blueprints WHERE user_email=?", (user_email,))
        else:
            c.execute("DELETE FROM blueprints")
        c.commit()


# ── Favourite ─────────────────────────────────────────────────────────────────

def toggle_favorite(blueprint_id: int) -> bool:
    with _conn() as c:
        row = c.execute("SELECT is_favorite FROM blueprints WHERE id=?", (blueprint_id,)).fetchone()
        if row is None:
            return False
        new_val = 0 if row["is_favorite"] else 1
        c.execute("UPDATE blueprints SET is_favorite=? WHERE id=?", (new_val, blueprint_id))
        c.commit()
    return bool(new_val)


# Initialise on import
init_db()
