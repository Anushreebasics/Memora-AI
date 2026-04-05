import json
import os
import sqlite3
import re
from contextlib import contextmanager

from .config import settings


def ensure_db() -> None:
    os.makedirs(os.path.dirname(settings.sqlite_path), exist_ok=True)
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                checksum TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                trust_level TEXT DEFAULT 'medium',
                source_type TEXT DEFAULT 'document'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_memory (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                preferences TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_graph (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object_node TEXT NOT NULL,
                FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()
        
        # Safely add new columns if they don't exist
        try:
            conn.execute("ALTER TABLE sources ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
            conn.commit()
        except:
            pass
        try:
            conn.execute("ALTER TABLE sources ADD COLUMN trust_level TEXT DEFAULT 'medium'")
            conn.commit()
        except:
            pass
        try:
            conn.execute("ALTER TABLE sources ADD COLUMN source_type TEXT DEFAULT 'document'")
            conn.commit()
        except:
            pass


@contextmanager
def get_conn():
    conn = sqlite3.connect(settings.sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_source_by_path(path: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM sources WHERE path = ?", (path,)).fetchone()
        return row


def upsert_source(path: str, title: str, doc_type: str, checksum: str, trust_level: str = "medium", source_type: str = "document") -> tuple[int, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT id, created_at FROM sources WHERE path = ?", (path,)).fetchone()
        if row:
            source_id = int(row["id"])
            created_at = str(row["created_at"])
            conn.execute(
                "UPDATE sources SET title = ?, doc_type = ?, checksum = ?, trust_level = ?, source_type = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, doc_type, checksum, trust_level, source_type, source_id),
            )
            conn.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
            return source_id, created_at

        cur = conn.execute(
            "INSERT INTO sources(path, title, doc_type, checksum, trust_level, source_type) VALUES(?, ?, ?, ?, ?, ?)",
            (path, title, doc_type, checksum, trust_level, source_type),
        )
        source_id = int(cur.lastrowid)
        created_at_row = conn.execute("SELECT created_at FROM sources WHERE id = ?", (source_id,)).fetchone()
        return source_id, str(created_at_row["created_at"])


def insert_chunks(source_id: int, chunks: list[str]) -> list[int]:
    ids: list[int] = []
    with get_conn() as conn:
        for idx, chunk in enumerate(chunks):
            cur = conn.execute(
                "INSERT INTO chunks(source_id, chunk_index, chunk_text) VALUES(?, ?, ?)",
                (source_id, idx, chunk),
            )
            ids.append(int(cur.lastrowid))
    return ids


def lexical_search_chunks(query: str, limit: int = 24):
    terms = [t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) >= 3]
    if not terms:
        return []

    terms = terms[:10]
    where_clause = " OR ".join(["LOWER(c.chunk_text) LIKE ?" for _ in terms])
    params = [f"%{t}%" for t in terms]

    sql = f"""
        SELECT
            c.id AS chunk_id,
            c.chunk_text,
            c.chunk_index,
            s.id AS source_id,
            s.path,
            s.title,
            s.trust_level,
            s.source_type,
            s.created_at
        FROM chunks c
        JOIN sources s ON s.id = c.source_id
        WHERE {where_clause}
        LIMIT 400
    """

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    scored: list[dict] = []
    for row in rows:
        text = (row["chunk_text"] or "").lower()
        score = 0.0
        for term in terms:
            score += float(text.count(term))

        coverage = sum(1 for term in terms if term in text) / max(1, len(terms))
        blended = score + (coverage * 4.0)
        scored.append(
            {
                "chunk_id": int(row["chunk_id"]),
                "chunk_text": str(row["chunk_text"]),
                "chunk_index": int(row["chunk_index"]),
                "source_id": int(row["source_id"]),
                "path": str(row["path"]),
                "title": str(row["title"]),
                "trust_level": str(row["trust_level"]),
                "source_type": str(row["source_type"]),
                "created_at": str(row["created_at"]),
                "lexical_raw": blended,
            }
        )

    if not scored:
        return []

    max_score = max(item["lexical_raw"] for item in scored) or 1.0
    for item in scored:
        item["lexical_score"] = min(1.0, item["lexical_raw"] / max_score)

    scored.sort(key=lambda x: x["lexical_raw"], reverse=True)
    return scored[:limit]


def list_sources(limit: int = 200):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, path, title, doc_type, created_at, trust_level, source_type FROM sources ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def search_sources_by_date_and_trust(start_date: str = None, end_date: str = None, trust_levels: list[str] = None, limit: int = 200):
    """Search sources by date range and trust levels."""
    if not start_date and not end_date and not trust_levels:
        return []

    with get_conn() as conn:
        query = "SELECT id, path, title, doc_type, created_at, trust_level, source_type FROM sources WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date)
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date)
        if trust_levels:
            placeholders = ",".join("?" * len(trust_levels))
            query += f" AND trust_level IN ({placeholders})"
            params.extend(trust_levels)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def save_chat(question: str, answer: str, citations: list[dict]) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chats(question, answer, citations_json) VALUES(?, ?, ?)",
            (question, answer, json.dumps(citations)),
        )


def get_recent_sources(days: int = 7):
    """Get sources ingested in the past N days."""
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT id, path, title, doc_type, created_at, trust_level, source_type 
               FROM sources 
               WHERE datetime(created_at) >= datetime('now', '-{days} days')
               ORDER BY created_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def get_recent_questions(days: int = 7, limit: int = 50):
    """Get questions asked in the past N days."""
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT question, answer, citations_json, created_at 
               FROM chats 
               WHERE datetime(created_at) >= datetime('now', '-{days} days')
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_chunks_from_sources(source_ids: list[int], limit: int = 100):
    """Get all chunks from a list of source IDs."""
    if not source_ids:
        return []
    placeholders = ",".join("?" * len(source_ids))
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT c.chunk_text, s.title, s.path 
               FROM chunks c 
               JOIN sources s ON s.id = c.source_id 
               WHERE c.source_id IN ({placeholders})
               LIMIT ?""",
            (*source_ids, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_user_memory() -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT preferences FROM user_memory WHERE id = 1").fetchone()
        return str(row["preferences"]) if row else ""


def get_chunk_by_id(chunk_id: int) -> dict | None:
    """Fetch a single chunk by ID with source metadata."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                c.id,
                c.chunk_text,
                c.chunk_index,
                c.source_id,
                s.title,
                s.path,
                s.doc_type,
                s.trust_level,
                s.source_type,
                s.created_at
            FROM chunks c
            JOIN sources s ON s.id = c.source_id
            WHERE c.id = ?
            """,
            (chunk_id,),
        ).fetchone()
        if row:
            return dict(row)
        return None


def upsert_user_memory(preferences: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_memory (id, preferences) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET preferences = excluded.preferences",
            (preferences,)
        )


def insert_triplets(source_id: int, triplets: list[dict]) -> None:
    if not triplets:
        return
    with get_conn() as conn:
        # clear old ones
        conn.execute("DELETE FROM knowledge_graph WHERE source_id = ?", (source_id,))
        for t in triplets:
            conn.execute(
                "INSERT INTO knowledge_graph (source_id, subject, predicate, object_node) VALUES (?, ?, ?, ?)",
                (source_id, str(t.get("s", "")), str(t.get("p", "")), str(t.get("o", "")))
            )


def search_graph_triplets(query: str, limit: int = 20) -> list[dict]:
    terms = [t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) >= 4]
    if not terms:
        return []
    
    where_clause = " OR ".join(["LOWER(subject) LIKE ? OR LOWER(object_node) LIKE ?" for _ in terms])
    params = []
    for t in terms:
        params.extend([f"%{t}%", f"%{t}%"])
        
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT subject, predicate, object_node FROM knowledge_graph WHERE {where_clause} LIMIT ?",
            (*params, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def list_graph_triplets(limit: int = 2000) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                kg.subject,
                kg.predicate,
                kg.object_node,
                s.title AS source_title,
                s.path AS source_path
            FROM knowledge_graph kg
            LEFT JOIN sources s ON s.id = kg.source_id
            ORDER BY kg.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
