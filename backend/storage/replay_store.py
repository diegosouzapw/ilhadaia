"""
Replay Store — salva snapshots do estado do mundo em NDJSON para replay posterior.
"""
import json
import time
from pathlib import Path
from typing import Optional


class ReplayStore:
    """Salva frames do world_state para replay de sessões passadas."""

    def __init__(self, replay_dir: str = "data/replays", snapshot_interval: int = 5):
        self.replay_dir = Path(replay_dir)
        self.replay_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_interval = snapshot_interval
        self._file = None
        self._session_id: Optional[str] = None

    def start_session(self, session_id: str) -> None:
        if self._file:
            self._file.close()
        self._session_id = session_id
        path = self.replay_dir / f"{session_id}.replay.ndjson"
        self._file = open(path, "w", encoding="utf-8")

    def maybe_snapshot(self, tick: int, world_state: dict) -> None:
        """Salva snapshot apenas nos ticks de intervalo."""
        if tick % self.snapshot_interval == 0:
            self._write(tick, world_state)

    def force_snapshot(self, tick: int, world_state: dict) -> None:
        """Salva snapshot independente do intervalo (ex: ao final da sessão)."""
        self._write(tick, world_state)

    def _write(self, tick: int, world_state: dict) -> None:
        if not self._file:
            return
        entry = {"tick": tick, "timestamp": time.time(), "state": world_state}
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None

    def load_replay(self, session_id: str) -> list[dict]:
        """Carrega todos os frames de uma sessão."""
        path = self.replay_dir / f"{session_id}.replay.ndjson"
        if not path.exists():
            return []
        frames = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        frames.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return frames

    def list_sessions(self) -> list[str]:
        """Lista todos os session_ids com replay disponível."""
        return [f.stem.replace(".replay", "") for f in self.replay_dir.glob("*.replay.ndjson")]
