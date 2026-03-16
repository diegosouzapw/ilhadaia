"""
Decision Log — registra cada decisão de IA em NDJSON por sessão.
Campos: session_id, tick, agent_id, model, provider, latency_ms,
        prompt_tokens, completion_tokens, thought, speech, action,
        action_params, result, score_delta, timestamp.
"""
import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional


@dataclass
class DecisionRecord:
    session_id: str
    tick: int
    agent_id: str
    agent_name: str
    model: str
    provider: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    thought: str
    speech: str
    action: str
    action_params: dict
    result: str          # "success" | "invalid" | "skip_cooldown" | "skip_budget" | "error"
    score_delta: float = 0.0
    timestamp: float = field(default_factory=time.time)


class DecisionLog:
    """Grava decisões de agentes em NDJSON, uma linha por decisão."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._session_id: Optional[str] = None

    def start_session(self, session_id: str) -> None:
        if self._file:
            self._file.close()
        self._session_id = session_id
        path = self.log_dir / f"{session_id}.ndjson"
        self._file = open(path, "a", encoding="utf-8")

    def log(self, record: DecisionRecord) -> None:
        if self._file:
            self._file.write(json.dumps(asdict(record)) + "\n")
            self._file.flush()

    def log_skip(self, session_id: str, tick: int, agent_id: str,
                 agent_name: str, reason: str) -> None:
        """Atalho para registrar skips de cooldown/budget sem chamar a IA."""
        self.log(DecisionRecord(
            session_id=session_id,
            tick=tick,
            agent_id=agent_id,
            agent_name=agent_name,
            model="",
            provider="",
            latency_ms=0.0,
            prompt_tokens=0,
            completion_tokens=0,
            thought="",
            speech="",
            action="wait",
            action_params={},
            result=reason,
        ))

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None
