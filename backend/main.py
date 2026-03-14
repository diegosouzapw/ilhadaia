import asyncio
import json
import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from world import World
from agent import Agent

# Authorization
load_dotenv()
AUTHORIZED_IDS = [id.strip() for id in os.getenv("AUTHORIZED_IDS", "777").split(",") if id.strip()]
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev_token_123")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

class JoinRequest(BaseModel):
    agent_id: str = Field(..., example="777")
    name: str = Field(..., example="Visitante")
    personality: str = Field(..., example="Curioso e amigável")

class ActionRequest(BaseModel):
    thought: str = ""
    action: str = "wait"
    speak: str = ""
    target_name: str = ""
    params: dict = {}

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BBB_IA")

# Configuration (Already loaded at the top)

app = FastAPI(title="BBB de IA - Backend Engine")

# Security dependency
async def verify_admin_token(x_admin_token: str = Header(None)):
    if x_admin_token != ADMIN_TOKEN:
        logger.warning(f"Unauthorized access attempt with token: {x_admin_token}")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing Admin Token")
    return x_admin_token

# Allow CORS for dynamic origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global world instance
world = World()

# Setup Initial Agents (respecting saved settings)
world.reset_agents(Agent)

# Tracking active websocket connections for the "God mode" frontend observers
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")
        # Send initial world state upon connection
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

@app.on_event("startup")
async def startup_event():
    # Start the world simulation loop in the background
    asyncio.create_task(world_loop())
    logger.info("World simulation loop started.")

async def world_loop():
    while True:
        try:
            # 1. Update the world state (tick)
            events = await world.tick()
            
            # Handle Auto-Reset Signal
            if events == "AUTO_RESET":
                world.reset_agents(Agent)
                events = [] # Clear so it sends as a normal update for the reset state
                await manager.broadcast({"type": "reset", "data": world.get_state()})

            # 2. Broadcast the new state to all connected frontends
            if events or world.ticks % 1 == 0: # send state periodically or on events
                await manager.broadcast({"type": "update", "data": world.get_state(), "events": events if isinstance(events, list) else []})
                
        except Exception as e:
            logger.error(f"Error in world loop: {e}")
            
            # Tick delay (1 second per tick now for smooth movement)
        await asyncio.sleep(1)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect much input from the observer yet, but we keep the connection open
            data = await websocket.receive_text()
            logger.debug(f"Received message from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
def read_root():
    return {"status": "World engine is running", "ticks": world.ticks}

@app.post("/reset", dependencies=[Depends(verify_admin_token)])
async def reset_game(player_count: int = 4):
    world.reset_agents(Agent, player_count=player_count)
    await manager.broadcast({"type": "reset", "data": world.get_state()})
    return {"status": "World reset successful", "player_count": player_count}

@app.post("/settings/ai_interval", dependencies=[Depends(verify_admin_token)])
async def set_ai_interval(interval: int):
    world.ai_interval = max(0, interval)
    world._save_history() # Persist change
    logger.info(f"AI decision interval updated to: {world.ai_interval}")
    return {"status": "Interval updated", "new_interval": world.ai_interval}

# --- Remote Agent API ---

@app.post("/join")
async def join_island(req: JoinRequest):
    # 1. Validar se o ID está na lista de autorizados
    if req.agent_id not in AUTHORIZED_IDS:
        logger.warning(f"Tentativa de entrada com ID não autorizado.")
        raise HTTPException(status_code=401, detail="ID de Acesso não autorizado.")

    # 2. Verificar se o ID já está em uso na ilha
    if any(a.id == req.agent_id for a in world.agents):
        raise HTTPException(status_code=400, detail="Este ID já está em uso na ilha.")

    # Create a new remote agent
    new_agent = Agent(req.name, req.personality, 10, 10, is_remote=True, agent_id=req.agent_id)
    world.add_agent(new_agent)
    logger.info(f"Remote agent joined: {new_agent.name}")
    
    # Broadcast join event
    await manager.broadcast({
        "type": "update", 
        "data": world.get_state(), 
        "events": [{"action": "join", "event_msg": f"{new_agent.name} CHEGOU NA ILHA!", "agent_id": new_agent.id, "name": new_agent.name}]
    })
    
    return {
        "status": "Joined successfully",
        "agent_id": new_agent.id,
        "name": new_agent.name,
        "personality": new_agent.personality,
        "coords": [new_agent.x, new_agent.y]
    }

@app.get("/agent/{agent_id}/context")
async def get_agent_context(agent_id: str):
    agent = next((a for a in world.agents if a.id == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    context = world._get_context_for_agent(agent)
    # Add status info to context for the remote agent
    context["status"] = {
        "hp": agent.hp,
        "hunger": agent.hunger,
        "thirst": agent.thirst,
        "is_alive": agent.is_alive,
        "is_zombie": getattr(agent, "is_zombie", False),
        "inventory": agent.inventory,
        "pos": [agent.x, agent.y]
    }
    return context

@app.post("/agent/{agent_id}/action")
async def agent_action(agent_id: str, req: ActionRequest):
    agent = next((a for a in world.agents if a.id == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not agent.is_alive:
        return {"status": "Agent is dead", "action": "ignored"}

    # Construct the internal action format
    action_data = {
        "agent_id": agent.id,
        "name": agent.name,
        "thought": req.thought,
        "action": req.action,
        "speak": req.speak,
        "target_name": req.target_name
    }
    # Merge params (dx, dy, target_x, target_y)
    for k, v in req.params.items():
        action_data[k] = v
        
    # Apply action to the world
    world._apply_action(agent, action_data)
    
    # Send event to world events list so frontends see it
    world.ai_events.append(action_data)
    
    if req.speak:
        logger.info(f"[REMOTE CHAT] {agent.name}: {req.speak}")
        
    return {"status": "Action processed", "action": req.action}

@app.delete("/agent/{agent_id}")
async def delete_agent(agent_id: str):
    success = world.remove_agent(agent_id)
    if success:
        # Broadcast removal to frontends
        await manager.broadcast({
            "type": "update", 
            "data": world.get_state(),
            "events": [{"action": "busy", "event_msg": f"UM AGENTE FOI REMOVIDO PELO ADMINISTRADOR.", "agent_id": agent_id}]
        })
        return {"status": "Agent removed", "agent_id": agent_id}
    else:
        raise HTTPException(status_code=404, detail="Agent not found")
