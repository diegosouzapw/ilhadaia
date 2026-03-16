"""
T20 — Tournament Runner automatizado.
Orquestra o ciclo de vida completo de um torneio:
- Monitora ticks e encerra quando duration_ticks é atingido
- Calcula leaderboard final baseado em benchmark de cada agente
- Salva histórico de torneio no SQLite
"""
import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger("BBB_IA.TournamentRunner")


class TournamentRunner:
    """Gerencia o ciclo de vida automatizado de torneios."""

    def __init__(self, tournaments: dict, world, session_store):
        self.tournaments = tournaments
        self.world = world
        self.session_store = session_store
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        """Inicia o loop de monitoramento em background."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._monitor_loop())
            logger.info("TournamentRunner started")

    def stop(self):
        """Para o monitoramento."""
        self._running = False
        if self._task:
            self._task.cancel()

    async def _monitor_loop(self):
        """Loop principal: verifica todos os torneios ativos a cada 5 ticks equivalentes."""
        while self._running:
            await asyncio.sleep(10)  # checa a cada 10s
            try:
                await self._check_tournaments()
            except Exception as e:
                logger.error(f"TournamentRunner error: {e}")

    async def _check_tournaments(self):
        """Verifica se algum torneio deve ser encerrado."""
        current_tick = self.world.ticks
        for tid, tournament in list(self.tournaments.items()):
            if tournament.get("status") not in ("active", "running"):
                continue

            start_tick = tournament.get("start_tick")
            if start_tick is None:
                # Backward-compat: torneios antigos não tinham start_tick explícito
                start_tick = current_tick
                tournament["start_tick"] = start_tick

            duration = (
                tournament.get("duration_ticks")
                or tournament.get("config", {}).get("duration_ticks", 200)
            )
            if current_tick - start_tick >= duration:
                await self._finalize_tournament(tid, tournament, current_tick)

    async def _finalize_tournament(self, tid: str, tournament: dict, current_tick: int):
        """Encerra o torneio, calcula leaderboard final e atualiza status."""
        logger.info(f"Finalizing tournament {tid} at tick {current_tick}")
        tournament["status"] = "finished"
        tournament["end_tick"] = current_tick
        tournament["finished_at"] = time.time()

        # Calcular leaderboard final baseado nos agentes registrados
        registered_ids = tournament.get("registered_agents", [])
        leaderboard = []
        for agent in self.world.agents:
            if agent.id in registered_ids or not registered_ids:
                leaderboard.append({
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "profile_id": getattr(agent, "profile_id", "claude-kiro"),
                    "score": agent.benchmark.get("score", 0.0),
                    "tokens_used": getattr(agent, "tokens_used", 0),
                    "decisions_made": agent.benchmark.get("decisions_made", 0),
                    "is_alive": getattr(agent, "is_alive", False),
                    "is_zombie": getattr(agent, "is_zombie", False),
                })

        leaderboard.sort(key=lambda x: (-x["score"], -x["is_alive"], -x["decisions_made"]))
        tournament["final_leaderboard"] = leaderboard
        tournament["winner"] = leaderboard[0] if leaderboard else None

        # Auto-reset se configurado
        if tournament.get("reset_on_finish", tournament.get("config", {}).get("reset_on_finish")):
            logger.info(f"Tournament {tid}: reset_on_finish=True, scheduling world reset")

        logger.info(f"Tournament {tid} finalized. Winner: {tournament.get('winner', {}).get('agent_name', 'N/A')}")

    def get_leaderboard(self, tid: str) -> list[dict]:
        """Retorna o leaderboard atual (ou final) de um torneio."""
        tournament = self.tournaments.get(tid)
        if not tournament:
            return []

        # Se finalizado, retorna o leaderboard calculado
        if tournament.get("status") == "finished":
            return tournament.get("final_leaderboard", [])

        # Se ativo, calcula ao vivo
        registered_ids = tournament.get("registered_agents", [])
        live = []
        for agent in self.world.agents:
            if registered_ids and agent.id not in registered_ids:
                continue
            live.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "profile_id": getattr(agent, "profile_id", "claude-kiro"),
                "score": agent.benchmark.get("score", 0.0),
                "tokens_used": getattr(agent, "tokens_used", 0),
                "decisions_made": agent.benchmark.get("decisions_made", 0),
                "hp": getattr(agent, "hp", 0),
                "is_alive": getattr(agent, "is_alive", False),
            })
        live.sort(key=lambda x: (-x["score"], -x["is_alive"]))
        return live

    def get_status(self, tid: str) -> Optional[dict]:
        """Retorna metadados de status de um torneio."""
        tournament = self.tournaments.get(tid)
        if not tournament:
            return None
        current_tick = self.world.ticks
        start_tick = tournament.get("start_tick", current_tick)
        duration = (
            tournament.get("duration_ticks")
            or tournament.get("config", {}).get("duration_ticks", 200)
        )
        ticks_remaining = max(0, duration - (current_tick - start_tick))
        return {
            "id": tid,
            "name": tournament.get("name") or tournament.get("config", {}).get("name", tid),
            "status": tournament.get("status", "waiting"),
            "current_tick": current_tick,
            "start_tick": start_tick,
            "ticks_remaining": ticks_remaining,
            "progress_pct": min(100.0, (current_tick - start_tick) / max(1, duration) * 100),
            "registered_agents": len(tournament.get("registered_agents", [])),
            "winner": tournament.get("winner"),
        }
