import asyncio
import csv
import io
import json
import logging
import os
import random
import time
import uuid
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional

# T18: Rate Limiting
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMIT_ENABLED = True
except ImportError:
    limiter = None
    _rate_limit_exceeded_handler = None
    RateLimitExceeded = None
    RATE_LIMIT_ENABLED = False

from world import World
from agent import Agent
from storage.decision_log import DecisionLog
from storage.session_store import SessionStore
from storage.replay_store import ReplayStore
from storage.memory_store import MemoryStore           # T22
from storage.webhook_manager import WebhookManager     # T24
from runtime.thinker import Thinker
from runtime.profiles import list_profiles, get_profile, BUILTIN_PROFILES
from runtime.tournament_runner import TournamentRunner  # T20

# ── Configuração ──────────────────────────────────────────────────────────────
load_dotenv()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev_token_123")
AUTHORIZED_IDS = [id.strip() for id in os.getenv("AUTHORIZED_IDS", "777").split(",") if id.strip()]
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BBB_IA")

# ── Módulos de storage e runtime ──────────────────────────────────────────────
decision_log = DecisionLog(log_dir="logs")
session_store = SessionStore(db_path="data/ilhadaia.db")
replay_store = ReplayStore(replay_dir="data/replays", snapshot_interval=5)
memory_store = MemoryStore(db_path="data/ilhadaia.db")  # T22
webhook_manager = WebhookManager(db_path="data/ilhadaia.db")  # T24
thinker: Optional[Thinker] = None

# ── Estado global ─────────────────────────────────────────────────────────────
world = World()
world.reset_agents(Agent)

_current_session_id: Optional[str] = None

# Torneios em memória + runner
TOURNAMENTS: dict[str, dict] = {}
tournament_runner: Optional[TournamentRunner] = None
_notified_finished_tournaments: set[str] = set()

# ── Models ────────────────────────────────────────────────────────────────────
class JoinRequest(BaseModel):
    agent_id: str = Field(..., json_schema_extra={"example": "777"})
    name: str = Field(..., json_schema_extra={"example": "Visitante"})
    personality: str = Field(..., json_schema_extra={"example": "Curioso e amigável"})

class ActionRequest(BaseModel):
    thought: str = ""
    action: str = "wait"
    speak: str = ""
    target_name: str = ""
    params: dict = {}

class AgentRegistration(BaseModel):
    owner_id: str
    owner_name: str = ""
    agent_name: str
    persona: str = "Estratégico e adaptável"
    profile_id: str = "claude-kiro"

class TournamentConfig(BaseModel):
    name: str
    max_agents: int = 8
    duration_ticks: int = 500
    allowed_profiles: list[str] = []
    reset_on_finish: bool = True

# ── Auth ───────────────────────────────────────────────────────────────────────
async def verify_admin_token(x_admin_token: str = Header(None)):
    if x_admin_token != ADMIN_TOKEN:
        logger.warning(f"Unauthorized access attempt with token: {x_admin_token}")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing Admin Token")
    return x_admin_token

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _current_session_id, thinker, tournament_runner
    # === STARTUP ===
    thinker = Thinker(decision_log=decision_log)

    async def _thinker_decider(agent, context, tick):
        if thinker is None or _current_session_id is None:
            return await agent.act(context)
        return await thinker.think(
            agent=agent,
            world_context=context,
            current_tick=tick,
            session_id=_current_session_id,
        )

    world.set_ai_decider(_thinker_decider)
    _world_settings = {"ai_interval": world.ai_interval, "player_count": world.player_count}
    _current_session_id = session_store.create_session(_world_settings)
    world.set_session_id(_current_session_id)
    decision_log.start_session(_current_session_id)
    replay_store.start_session(_current_session_id)
    task = asyncio.create_task(world_loop())
    # T20: iniciar tournament runner
    tournament_runner = TournamentRunner(TOURNAMENTS, world, session_store)
    tournament_runner.start()
    logger.info(f"🌍 World simulation started — session: {_current_session_id}")

    yield

    # === SHUTDOWN ===
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    replay_store.close()
    decision_log.close()
    tournament_runner.stop() if tournament_runner else None
    memory_store.close()
    webhook_manager.close()
    session_store.close()
    logger.info("🛑 World simulation stopped cleanly.")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="BBB de IA - Backend Engine", lifespan=lifespan)

# T18: inicialização de rate limiting (quando slowapi estiver instalado)
if RATE_LIMIT_ENABLED and limiter and _rate_limit_exceeded_handler and RateLimitExceeded:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def _rate_limit(limit: str):
    """Decorator condicional de rate limit."""
    def decorator(func):
        if RATE_LIMIT_ENABLED and limiter:
            return limiter.limit(limit)(func)
        return func
    return decorator

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["null"],  # "null" = file:// origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Frontend estático ─────────────────────────────────────────────────────────
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/frontend", StaticFiles(directory=_frontend_dir), name="frontend")

# ── WebSocket ─────────────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")
        await websocket.send_text(json.dumps({"type": "init", "data": world.get_state()}))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("Client disconnected.")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        msg_str = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(msg_str)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()

async def _dispatch_webhooks_from_events(events: list[dict]) -> None:
    """Dispara webhooks para eventos críticos sem impactar o game loop."""
    tasks = []
    for event in events:
        action = event.get("action")
        if action == "die":
            tasks.append(webhook_manager.fire_event("death", {
                "agent_id": event.get("agent_id", ""),
                "agent_name": event.get("name", ""),
                "tick": world.ticks,
                "event_msg": event.get("event_msg", ""),
            }))
        elif action == "zombie":
            tasks.append(webhook_manager.fire_event("zombie", {
                "agent_id": event.get("agent_id", ""),
                "agent_name": event.get("name", ""),
                "tick": world.ticks,
                "event_msg": event.get("event_msg", ""),
            }))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

# ── Game Loop ─────────────────────────────────────────────────────────────────
async def world_loop():
    while True:
        try:
            events = await world.tick()

            if events == "AUTO_RESET":
                world.reset_agents(Agent)
                events = []
                await manager.broadcast({"type": "reset", "data": world.get_state()})
            else:
                # Atualizar scores no SQLite a cada 10 ticks
                if world.ticks % 10 == 0 and _current_session_id:
                    for agent in world.agents:
                        try:
                            session_store.upsert_agent_score(_current_session_id, agent)
                            if getattr(agent, "owner_id", ""):
                                memory_store.save(agent)
                        except Exception:
                            pass
                    # Snapshot de replay
                    replay_store.maybe_snapshot(world.ticks, world.get_state())

            if isinstance(events, list) and events:
                asyncio.create_task(_dispatch_webhooks_from_events(events))

            # Notifica fim de torneio uma única vez por torneio
            for tournament_id, tournament in TOURNAMENTS.items():
                if tournament.get("status") == "finished" and tournament_id not in _notified_finished_tournaments:
                    _notified_finished_tournaments.add(tournament_id)
                    asyncio.create_task(webhook_manager.fire_event("tournament_end", {
                        "tournament_id": tournament_id,
                        "winner": tournament.get("winner", {}),
                        "tick": world.ticks,
                    }))

            if events or world.ticks % 1 == 0:
                await manager.broadcast({
                    "type": "update",
                    "data": world.get_state(),
                    "events": events if isinstance(events, list) else []
                })
        except Exception as e:
            logger.error(f"Error in world loop: {e}")
        await asyncio.sleep(1)

# ── Endpoints básicos ─────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received message from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
def read_root():
    return {
        "status": "World engine is running",
        "ticks": world.ticks,
        "session_id": _current_session_id,
        "agents": len(world.agents),
    }

@app.post("/reset", dependencies=[Depends(verify_admin_token)])
async def reset_game(player_count: int = 4):
    global _current_session_id
    if _current_session_id:
        for agent in world.agents:
            if getattr(agent, "owner_id", ""):
                memory_store.save(agent)
        replay_store.force_snapshot(world.ticks, world.get_state())
        session_store.end_session(_current_session_id, None, None)
    _world_settings = {"ai_interval": world.ai_interval, "player_count": world.player_count}
    _current_session_id = session_store.create_session(_world_settings)
    world.set_session_id(_current_session_id)
    decision_log.start_session(_current_session_id)
    replay_store.start_session(_current_session_id)
    world.reset_agents(Agent, player_count=player_count)
    await manager.broadcast({"type": "reset", "data": world.get_state()})
    return {"status": "World reset successful", "player_count": player_count, "session_id": _current_session_id}

@app.post("/settings/ai_interval", dependencies=[Depends(verify_admin_token)])
async def set_ai_interval(interval: int):
    world.ai_interval = max(0, interval)
    world._save_history()
    return {"status": "Interval updated", "new_interval": world.ai_interval}

# ── Sessions, Scoreboard & Replay ─────────────────────────────────────────────

@app.get("/sessions")
async def list_sessions(limit: int = 20):
    return {"sessions": session_store.get_sessions(limit=limit)}

@app.get("/sessions/{session_id}/replay")
async def get_replay(session_id: str):
    frames = replay_store.load_replay(session_id)
    if not frames:
        raise HTTPException(404, "Sessão não encontrada ou sem dados de replay")
    return {"session_id": session_id, "total_frames": len(frames), "frames": frames}

@app.get("/sessions/{session_id}/replay/frame/{tick}")
async def get_replay_frame(session_id: str, tick: int):
    frames = replay_store.load_replay(session_id)
    frame = next((f for f in frames if f["tick"] == tick), None)
    if not frame:
        raise HTTPException(404, f"Frame tick={tick} não encontrado")
    return frame

@app.get("/world/scoreboard")
async def get_scoreboard(limit: int = 50):
    return {"scoreboard": session_store.get_scoreboard(limit=limit)}

# ── Profiles ──────────────────────────────────────────────────────────────────

@app.get("/profiles")
async def get_profiles():
    return {"profiles": list_profiles()}

# ── Agent Registration (T14) ──────────────────────────────────────────────────

@app.post("/agents/register")
@_rate_limit("10/minute")
async def register_agent(request: Request, reg: AgentRegistration):
    """Owner registra um agente customizado na ilha."""
    if reg.profile_id not in BUILTIN_PROFILES:
        raise HTTPException(400, f"Profile '{reg.profile_id}' não existe. Disponíveis: {list(BUILTIN_PROFILES.keys())}")

    max_agents = getattr(world, 'player_count', 12) + 4  # permite agentes externos além dos NPCs
    if len(world.agents) >= max_agents:
        raise HTTPException(409, "Limite de agentes atingido")

    profile = get_profile(reg.profile_id)
    agent_id = f"agent_{reg.owner_id}_{int(time.time())}"

    new_agent = Agent(
        name=reg.agent_name[:30],
        personality=reg.persona[:200],
        start_x=random.randint(2, 17),
        start_y=random.randint(2, 17),
        agent_id=agent_id,
    )
    new_agent.profile_id = reg.profile_id
    new_agent.owner_id = reg.owner_id
    new_agent.token_budget = profile.token_budget
    new_agent.cooldown_ticks = profile.cooldown_ticks

    memory_store.load(new_agent)
    world.add_agent(new_agent)
    logger.info(f"🤖 Registered agent: {reg.agent_name} [{reg.profile_id}] by {reg.owner_id}")
    asyncio.create_task(webhook_manager.fire_event("agent_registered", {
        "agent_id": agent_id,
        "agent_name": reg.agent_name,
        "owner_id": reg.owner_id,
        "profile_id": reg.profile_id,
        "tick": world.ticks,
    }))

    await manager.broadcast({
        "type": "update", "data": world.get_state(),
        "events": [{"action": "join", "event_msg": f"{reg.agent_name} ENTROU NA ILHA! (Modelo: {profile.model})", "agent_id": agent_id}]
    })

    return {
        "agent_id": agent_id,
        "message": f"{reg.agent_name} entrou na ilha!",
        "profile": reg.profile_id,
        "model": profile.model,
        "token_budget": profile.token_budget,
    }

@app.get("/agents/{agent_id}/state")
async def get_agent_state(agent_id: str):
    agent = next((a for a in world.agents if a.id == agent_id), None)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return {
        "id": agent.id,
        "name": agent.name,
        "health": agent.hp,
        "position": {"x": agent.x, "y": agent.y},
        "tokens_used": getattr(agent, "tokens_used", 0),
        "token_budget": getattr(agent, "token_budget", 10000),
        "profile_id": getattr(agent, "profile_id", "claude-kiro"),
        "benchmark": getattr(agent, "benchmark", {}),
        "recent_memory": agent.memory[-5:] if hasattr(agent, "memory") else [],
    }

# ── Tournaments (T15) ─────────────────────────────────────────────────────────

@app.post("/tournaments", dependencies=[Depends(verify_admin_token)])
@_rate_limit("5/minute")
async def create_tournament(request: Request, config: TournamentConfig):
    t_id = f"tournament_{int(time.time())}"
    config_data = config.model_dump()
    TOURNAMENTS[t_id] = {
        "id": t_id,
        "name": config.name,
        "status": "waiting",
        "config": config_data,
        "max_agents": config.max_agents,
        "duration_ticks": config.duration_ticks,
        "reset_on_finish": config.reset_on_finish,
        "allowed_profiles": config.allowed_profiles or list(BUILTIN_PROFILES.keys()),
        "start_tick": None,
        "started_at": None,
        "end_tick": None,
        "registered_agents": [],
    }
    return {"tournament_id": t_id, "config": config_data}

@app.post("/tournaments/{t_id}/join")
async def join_tournament(request: Request, t_id: str, reg: AgentRegistration):
    t = TOURNAMENTS.get(t_id)
    if not t:
        raise HTTPException(404, "Torneio não existe")
    if t["status"] != "waiting":
        raise HTTPException(409, "Torneio já começou")
    if len(t["registered_agents"]) >= t["max_agents"]:
        raise HTTPException(409, "Torneio lotado")
    if t["allowed_profiles"] and reg.profile_id not in t["allowed_profiles"]:
        raise HTTPException(400, f"Perfil não permitido. Permitidos: {t['allowed_profiles']}")

    result = await register_agent(request, reg)
    t["registered_agents"].append(result["agent_id"])
    return result

@app.post("/tournaments/{t_id}/start", dependencies=[Depends(verify_admin_token)])
async def start_tournament(t_id: str):
    t = TOURNAMENTS.get(t_id)
    if not t:
        raise HTTPException(404, "Torneio não existe")
    t["status"] = "active"
    t["start_tick"] = world.ticks
    t["started_at"] = time.time()
    t["end_tick"] = world.ticks + t["duration_ticks"]
    world.active_tournament_id = t_id
    world.tournament_end_tick = t["end_tick"]
    _notified_finished_tournaments.discard(t_id)
    return {"message": "Torneio iniciado!", "end_tick": t["end_tick"]}

@app.get("/tournaments")
async def list_tournaments():
    return {"tournaments": list(TOURNAMENTS.values())}

# ── Remote Agent API (mantido) ────────────────────────────────────────────────

@app.post("/join")
async def join_island(req: JoinRequest):
    if req.agent_id not in AUTHORIZED_IDS:
        raise HTTPException(status_code=401, detail="ID de Acesso não autorizado.")

    existing_agent = next((a for a in world.agents if a.id == req.agent_id), None)
    if existing_agent:
        if existing_agent.is_alive:
            raise HTTPException(status_code=400, detail="Este ID já está em uso por um agente Vivo.")
        else:
            world.remove_agent(req.agent_id)

    new_agent = Agent(req.name, req.personality, 10, 10, is_remote=True, agent_id=req.agent_id)
    world.add_agent(new_agent)

    await manager.broadcast({
        "type": "update", "data": world.get_state(),
        "events": [{"action": "join", "event_msg": f"{new_agent.name} CHEGOU NA ILHA!", "agent_id": new_agent.id, "name": new_agent.name}]
    })

    return {"status": "Joined successfully", "agent_id": new_agent.id, "name": new_agent.name,
            "personality": new_agent.personality, "coords": [new_agent.x, new_agent.y]}

@app.get("/agent/{agent_id}/context")
async def get_agent_context(agent_id: str):
    agent = next((a for a in world.agents if a.id == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    context = world._get_context_for_agent(agent)
    context["status"] = {
        "hp": agent.hp,
        "hunger": agent.hunger,
        "thirst": agent.thirst,
        "is_alive": agent.is_alive,
        "is_zombie": getattr(agent, "is_zombie", False),
        "inventory": agent.inventory,
        "pos": [agent.x, agent.y],
        "tokens_used": getattr(agent, "tokens_used", 0),
        "token_budget": getattr(agent, "token_budget", 10000),
    }
    return context

@app.post("/agent/{agent_id}/action")
async def agent_action(agent_id: str, req: ActionRequest):
    agent = next((a for a in world.agents if a.id == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.is_alive:
        return {"status": "Agent is dead", "action": "ignored"}

    action_data = {"agent_id": agent.id, "name": agent.name, "thought": req.thought,
                   "action": req.action, "speak": req.speak, "target_name": req.target_name}
    for k, v in req.params.items():
        action_data[k] = v

    world._apply_action(agent, action_data)
    world.ai_events.append(action_data)
    return {"status": "Action processed", "action": req.action}

@app.delete("/agent/{agent_id}", dependencies=[Depends(verify_admin_token)])
async def delete_agent(agent_id: str):
    """Remove um agente da ilha. Requer X-Admin-Token."""
    success = world.remove_agent(agent_id)
    if success:
        await manager.broadcast({
            "type": "update", "data": world.get_state(),
            "events": [{"action": "busy", "event_msg": "UM AGENTE FOI REMOVIDO PELO ADMINISTRADOR.", "agent_id": agent_id}]
        })
        return {"status": "Agent removed", "agent_id": agent_id}
    raise HTTPException(status_code=404, detail="Agent not found")

# ═══════════════════════════════════════════════════════════════════════
# T18 — Rate Limiting (slowapi)
# ═══════════════════════════════════════════════════════════════════════

@app.get("/rate-limit/status")
async def rate_limit_status(request: Request):
    """Informa se o rate limit está ativo e as regras configuradas."""
    return {
        "rate_limit_enabled": RATE_LIMIT_ENABLED,
        "limits": {
            "POST /agents/register": "10/minute per IP",
            "POST /tournaments": "5/minute per IP (admin)",
            "POST /webhooks/register": "20/hour per IP",
        } if RATE_LIMIT_ENABLED else "Rate limiting not active (slowapi not installed)"
    }

# ═══════════════════════════════════════════════════════════════════════
# T19 — Exportação CSV/JSON
# ═══════════════════════════════════════════════════════════════════════

@app.get("/sessions/{session_id}/export")
async def export_session(session_id: str, format: str = "json"):
    """
    Exporta os frames de replay de uma sessão como JSON ou CSV.
    Query param: ?format=json (default) | csv
    """
    frames = replay_store.load_replay(session_id)
    if not frames:
        raise HTTPException(404, f"Sessão '{session_id}' não encontrada ou sem frames.")

    if format == "csv":
        output = io.StringIO()
        if frames:
            # Flatten frames para CSV
            fieldnames = ["tick", "session_id", "agent_count"]
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for frame in frames:
                writer.writerow({
                    "tick": frame.get("tick", ""),
                    "session_id": session_id,
                    "agent_count": len(frame.get("state", {}).get("agents", [])),
                })
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}.csv"}
        )

    # JSON default
    return {"session_id": session_id, "frame_count": len(frames), "frames": frames}

@app.get("/world/scoreboard/export")
async def export_scoreboard(format: str = "json"):
    """
    Exporta o scoreboard global como JSON ou CSV.
    Query param: ?format=json | csv
    """
    board = session_store.get_scoreboard(limit=200)
    if format == "csv":
        output = io.StringIO()
        if board:
            writer = csv.DictWriter(output, fieldnames=list(board[0].keys()))
            writer.writeheader()
            writer.writerows(board)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=scoreboard.csv"}
        )
    return {"scoreboard": board, "total": len(board)}

@app.get("/sessions/{session_id}/decisions/export")
async def export_decisions(session_id: str, format: str = "json"):
    """Exporta o decision log NDJSON de uma sessão como JSON ou CSV."""
    import os
    log_files = [f for f in os.listdir("logs") if session_id in f and f.endswith(".ndjson")]
    if not log_files:
        raise HTTPException(404, f"Decision log para sessão '{session_id}' não encontrado.")

    records = []
    with open(os.path.join("logs", log_files[0])) as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    if format == "csv" and records:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(records[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=decisions_{session_id}.csv"}
        )
    return {"session_id": session_id, "decisions": records, "total": len(records)}

# ═══════════════════════════════════════════════════════════════════════
# T20 — Tournament Status & Leaderboard aprimorado
# ═══════════════════════════════════════════════════════════════════════

@app.get("/tournaments/{tournament_id}/status")
async def tournament_status(tournament_id: str):
    """Retorna status detalhado de um torneio com progresso e estimativa de encerramento."""
    if tournament_runner is None:
        raise HTTPException(503, "TournamentRunner não iniciado")
    status = tournament_runner.get_status(tournament_id)
    if not status:
        raise HTTPException(404, f"Torneio '{tournament_id}' não encontrado")
    return status

@app.get("/tournaments/{tournament_id}/leaderboard")
async def tournament_leaderboard(tournament_id: str):
    """Retorna leaderboard ao vivo ou final do torneio."""
    if tournament_id not in TOURNAMENTS:
        raise HTTPException(404, f"Torneio '{tournament_id}' não encontrado")
    leaderboard = tournament_runner.get_leaderboard(tournament_id) if tournament_runner else []
    return {
        "tournament_id": tournament_id,
        "status": TOURNAMENTS[tournament_id].get("status", "unknown"),
        "leaderboard": leaderboard,
    }

# ═══════════════════════════════════════════════════════════════════════
# T22 — Memória Persistente entre sessões
# ═══════════════════════════════════════════════════════════════════════

@app.get("/memories")
async def list_memories(owner_id: Optional[str] = None):
    """Lista agentes com memória persistente salva."""
    agents_with_memory = memory_store.list_agents_with_memory()
    if owner_id:
        agents_with_memory = [m for m in agents_with_memory if m["owner_id"] == owner_id]
    return {"memories": agents_with_memory, "total": len(agents_with_memory)}

@app.post("/memories/save/{agent_id}")
async def save_agent_memory(agent_id: str):
    """Salva manualmente a memória de um agente no SQLite."""
    agent = next((a for a in world.agents if a.id == agent_id), None)
    if not agent:
        raise HTTPException(404, "Agente não encontrado")
    if not getattr(agent, "owner_id", ""):
        raise HTTPException(400, "Agente não tem owner_id — memória persistente requer owner")
    memory_store.save(agent)
    return {"status": "memory_saved", "agent_id": agent_id, "agent_name": agent.name}

@app.delete("/memories/{owner_id}/{agent_name}", dependencies=[Depends(verify_admin_token)])
async def delete_agent_memory(owner_id: str, agent_name: str):
    """Remove a memória persistente de um agente (admin)."""
    deleted = memory_store.delete(owner_id, agent_name)
    if not deleted:
        raise HTTPException(404, "Memória não encontrada")
    return {"status": "deleted", "owner_id": owner_id, "agent_name": agent_name}

# ═══════════════════════════════════════════════════════════════════════
# T24 — Webhooks de Notificação
# ═══════════════════════════════════════════════════════════════════════

class WebhookRegistration(BaseModel):
    owner_id: str
    url: str
    events: list[str] = ["all"]
    secret: str = ""

@app.post("/webhooks/register")
@_rate_limit("20/hour")
async def register_webhook(request: Request, reg: WebhookRegistration):
    """
    Registra uma URL de webhook para receber notificações de eventos.
    Eventos válidos: death, win, zombie, tournament_end, agent_registered, all
    """
    result = webhook_manager.register(
        owner_id=reg.owner_id,
        url=reg.url,
        events=reg.events,
        secret=reg.secret,
    )
    return result

@app.get("/webhooks/{owner_id}")
async def list_webhooks(owner_id: str):
    """Lista todos os webhooks registrados para um owner."""
    hooks = webhook_manager.list_for_owner(owner_id)
    return {"owner_id": owner_id, "webhooks": hooks}

@app.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, owner_id: str):
    """Remove um webhook pelo ID (requer owner_id para validação)."""
    deleted = webhook_manager.delete(webhook_id, owner_id)
    if not deleted:
        raise HTTPException(404, "Webhook não encontrado ou owner incorreto")
    return {"status": "deleted", "webhook_id": webhook_id}

@app.post("/webhooks/test/{owner_id}", dependencies=[Depends(verify_admin_token)])
async def test_webhook(owner_id: str):
    """Dispara um evento de teste para os webhooks do owner (admin)."""
    fired = await webhook_manager.fire_event("test", {
        "message": "BBBia webhook test",
        "owner_id": owner_id,
        "tick": world.ticks,
    })
    return {"status": "fired", "webhooks_notified": fired}

# ═══════════════════════════════════════════════════════════════════════
# Info geral do sistema (summary de todos os módulos ativos)
# ═══════════════════════════════════════════════════════════════════════

@app.get("/system/info")
async def system_info():
    """Retorna informações de todos os módulos ativos no backend."""
    return {
        "version": "turbinada-v0.5",
        "ticks": world.ticks,
        "session_id": _current_session_id,
        "modules": {
            "thinker": thinker is not None,
            "tournament_runner": tournament_runner is not None and tournament_runner._running,
            "memory_store": True,
            "webhook_manager": True,
            "replay_store": True,
            "decision_log": True,
        },
        "rate_limit": RATE_LIMIT_ENABLED,
        "active_tournaments": len([t for t in TOURNAMENTS.values() if t.get("status") in ("active", "running")]),
        "registered_webhooks": webhook_manager.conn.execute("SELECT COUNT(*) FROM webhooks").fetchone()[0],
        "agents_with_memory": len(memory_store.list_agents_with_memory()),
    }
