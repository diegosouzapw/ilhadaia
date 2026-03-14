"""
Session Store — persiste sessões, scores históricos e metadados de replay em SQLite WAL.
"""
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    started_at  REAL NOT NULL,
    ended_at    REAL,
    world_settings TEXT,
    winner_agent_id TEXT,
    winner_model    TEXT,
    status      TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS agent_scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          TEXT REFERENCES sessions(id),
    agent_id            TEXT NOT NULL,
    agent_name          TEXT NOT NULL,
    owner_id            TEXT DEFAULT '',
    model               TEXT DEFAULT 'gemini',
    provider            TEXT DEFAULT 'gemini',
    profile_id          TEXT DEFAULT 'default',
    ticks_alive         INTEGER DEFAULT 0,
    score_survival      REAL DEFAULT 0,
    score_social        REAL DEFAULT 0,
    score_efficiency    REAL DEFAULT 0,
    score_total         REAL DEFAULT 0,
    tokens_used         INTEGER DEFAULT 0,
    cost_usd            REAL DEFAULT 0,
    decisions_made      INTEGER DEFAULT 0,
    invalid_actions     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS world_settings_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    changed_at  REAL NOT NULL,
    settings    TEXT NOT NULL
);
"""


class SessionStore:
    """SQLite-backed store para sessões e scoreboard histórico."""

    def __init__(self, db_path: str = "data/ilhadaia.db"):
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # ── Sessions ────────────────────────────────────────────────────────────

    def create_session(self, world_settings: dict) -> str:
        session_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO sessions (id, started_at, world_settings, status) VALUES (?, ?, ?, 'active')",
            (session_id, time.time(), json.dumps(world_settings)),
        )
        self.conn.commit()
        return session_id

    def end_session(self, session_id: str, winner_id: Optional[str],
                    winner_model: Optional[str]) -> None:
        self.conn.execute(
            """UPDATE sessions
               SET ended_at = ?, winner_agent_id = ?, winner_model = ?, status = 'completed'
               WHERE id = ?""",
            (time.time(), winner_id, winner_model, session_id),
        )
        self.conn.commit()

    def get_sessions(self, limit: int = 20) -> list[dict]:
        cur = self.conn.execute(
            """SELECT id, started_at, ended_at, winner_model, status
               FROM sessions ORDER BY started_at DESC LIMIT ?""",
            (limit,),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    # ── Agent Scores ─────────────────────────────────────────────────────────

    def upsert_agent_score(self, session_id: str, agent) -> None:
        """Insere ou atualiza o score de um agente na sessão atual."""
        benchmark = getattr(agent, "benchmark", {})
        existing = self.conn.execute(
            "SELECT id FROM agent_scores WHERE session_id=? AND agent_id=?",
            (session_id, agent.id),
        ).fetchone()

        if existing:
            self.conn.execute(
                """UPDATE agent_scores SET
                   ticks_alive=?, score_total=?, tokens_used=?,
                   cost_usd=?, decisions_made=?, invalid_actions=?
                   WHERE session_id=? AND agent_id=?""",
                (
                    benchmark.get("ticks_survived", 0),
                    benchmark.get("score", 0.0),
                    getattr(agent, "tokens_used", 0),
                    benchmark.get("cost_usd", 0.0),
                    benchmark.get("decisions_made", 0),
                    benchmark.get("invalid_actions", 0),
                    session_id, agent.id,
                ),
            )
        else:
            profile_id = getattr(agent, "profile_id", "default")
            self.conn.execute(
                """INSERT INTO agent_scores
                   (session_id, agent_id, agent_name, owner_id, model, provider,
                    profile_id, ticks_alive, score_total, tokens_used, cost_usd,
                    decisions_made, invalid_actions)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    session_id, agent.id, agent.name,
                    getattr(agent, "owner_id", ""),
                    getattr(agent, "model_name", "gemini"),
                    getattr(agent, "provider", "gemini"),
                    profile_id,
                    benchmark.get("ticks_survived", 0),
                    benchmark.get("score", 0.0),
                    getattr(agent, "tokens_used", 0),
                    benchmark.get("cost_usd", 0.0),
                    benchmark.get("decisions_made", 0),
                    benchmark.get("invalid_actions", 0),
                ),
            )
        self.conn.commit()

    def get_scoreboard(self, limit: int = 50) -> list[dict]:
        cur = self.conn.execute(
            """SELECT agent_name, model, provider, profile_id,
                      score_total, tokens_used, cost_usd, decisions_made
               FROM agent_scores
               ORDER BY score_total DESC LIMIT ?""",
            (limit,),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def close(self) -> None:
        self.conn.close()
