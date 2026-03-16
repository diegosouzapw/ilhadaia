"""
T22 — Memória Persistente entre Sessões.

Serializa e desserializa AgentMemory no SQLite para que agentes registrados
(com owner_id) mantenham memória entre sessões.
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger("BBB_IA.MemoryStore")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_memories (
    owner_id      TEXT NOT NULL,
    agent_name    TEXT NOT NULL,
    profile_id    TEXT NOT NULL DEFAULT 'unknown',
    memory_json   TEXT NOT NULL,
    updated_at    REAL NOT NULL,
    PRIMARY KEY (owner_id, agent_name)
);
"""


class MemoryStore:
    """Persiste e recupera AgentMemory entre sessões para agentes com owner_id."""

    def __init__(self, db_path: str = "data/ilhadaia.db"):
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        # Migração: Garantir que profile_id existe se a tabela for antiga
        try:
            self.conn.execute("ALTER TABLE agent_memories ADD COLUMN profile_id TEXT NOT NULL DEFAULT 'unknown'")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass # Coluna já existe
        self.conn.commit()

    def save(self, agent) -> None:
        """
        Salva a memória de um agente com owner_id no SQLite.
        Ignora agentes sem owner_id (NPCs do jogo).
        """
        owner_id = getattr(agent, "owner_id", "")
        if not owner_id:
            return
        agent_memory = getattr(agent, "agent_memory", None)
        if agent_memory is None:
            return

        import time
        memory_dict = agent_memory.to_dict()
        # Inclui também o benchmark histórico
        memory_dict["benchmark_history"] = agent.benchmark.copy()

        self.conn.execute(
            """INSERT OR REPLACE INTO agent_memories
               (owner_id, agent_name, profile_id, memory_json, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (owner_id, agent.name, getattr(agent, "profile_id", "unknown"), json.dumps(memory_dict), time.time()),
        )
        self.conn.commit()
        logger.debug(f"Saved memory for {agent.name} (owner={owner_id})")

    def load(self, agent) -> bool:
        """
        Carrega a memória de um agente com owner_id do SQLite e a injeta no agent_memory.
        Retorna True se encontrou memória, False caso contrário.
        """
        owner_id = getattr(agent, "owner_id", "")
        if not owner_id:
            return False
        agent_memory = getattr(agent, "agent_memory", None)
        if agent_memory is None:
            return False

        row = self.conn.execute(
            "SELECT memory_json FROM agent_memories WHERE owner_id=? AND agent_name=?",
            (owner_id, agent.name),
        ).fetchone()
        if not row:
            return False

        try:
            data = json.loads(row[0])
            self._restore_memory(agent_memory, data)
            # Restaura benchmark histórico se disponível
            if "benchmark_history" in data:
                agent.benchmark.update(data["benchmark_history"])
            logger.info(f"Restored memory for {agent.name} (owner={owner_id}): "
                       f"{len(agent_memory.short_term)} short_term, "
                       f"{len(agent_memory.episodic)} episodic, "
                       f"{len(agent_memory.relational)} relational entries")
            return True
        except Exception as e:
            logger.error(f"Failed to restore memory for {agent.name}: {e}")
            return False

    def _restore_memory(self, agent_memory, data: dict) -> None:
        """Desserializa e injeta dados no AgentMemory."""
        from runtime.memory import ShortTermEntry, EpisodicEntry, RelationalEntry

        # Short-term
        for item in data.get("short_term", []):
            agent_memory.short_term.append(ShortTermEntry(
                tick=item.get("tick", 0),
                action=item.get("action", ""),
                thought=item.get("thought", ""),
                result=item.get("result", ""),
            ))
        # Manter limite
        if len(agent_memory.short_term) > agent_memory.SHORT_TERM_MAX:
            agent_memory.short_term = agent_memory.short_term[-agent_memory.SHORT_TERM_MAX:]

        # Episodic
        for item in data.get("episodic", []):
            agent_memory.episodic.append(EpisodicEntry(
                tick=item.get("tick", 0),
                event_type=item.get("type", ""),
                description=item.get("desc", ""),
                agents_involved=item.get("agents", []),
            ))
        if len(agent_memory.episodic) > agent_memory.EPISODIC_MAX:
            agent_memory.episodic = agent_memory.episodic[-agent_memory.EPISODIC_MAX:]

        # Relational
        for name, rel_data in data.get("relational", {}).items():
            agent_memory.relational[name] = RelationalEntry(
                agent_name=name,
                opinion=rel_data.get("opinion", 0.0),
                interactions=rel_data.get("interactions", 0),
                notes=rel_data.get("notes", ""),
            )

    def list_agents_with_memory(self) -> list[dict]:
        """Lista todos os agentes que possuem memória salva."""
        rows = self.conn.execute(
            "SELECT owner_id, agent_name, profile_id, updated_at FROM agent_memories ORDER BY updated_at DESC"
        ).fetchall()
        return [{"owner_id": r[0], "agent_name": r[1], "profile_id": r[2], "updated_at": r[3]} for r in rows]

    def delete(self, owner_id: str, agent_name: str) -> bool:
        """Remove a memória de um agente específico."""
        cur = self.conn.execute(
            "DELETE FROM agent_memories WHERE owner_id=? AND agent_name=?",
            (owner_id, agent_name),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        self.conn.close()
