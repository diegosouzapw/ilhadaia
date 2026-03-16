import asyncio
import json
import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import httpx
from pydantic import BaseModel, Field

from world import World
from agent import Agent

# Authorization
load_dotenv()
AUTHORIZED_IDS = [id.strip() for id in os.getenv("AUTHORIZED_IDS", "777").split(",") if id.strip()]
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev_token_123")
OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY")
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

class AISettingsRequest(BaseModel):
    ai_provider: str
    ai_model: str
    omniroute_url: str

@app.get("/settings/ai")
async def get_ai_settings():
    return {
        "ai_provider": world.ai_provider,
        "ai_model": world.ai_model,
        "omniroute_url": world.omniroute_url
    }

@app.post("/settings/ai", dependencies=[Depends(verify_admin_token)])
async def set_ai_settings(req: AISettingsRequest):
    world.ai_provider = req.ai_provider
    world.ai_model = req.ai_model
    world.omniroute_url = req.omniroute_url
    world._save_history()
    logger.info(f"AI settings updated: provider={world.ai_provider}, model={world.ai_model}, url={world.omniroute_url}")
    return {"status": "AI settings updated"}
@app.get("/models")
async def get_models(provider: Optional[str] = None, url: Optional[str] = None):
    """Proxy or return a list of available models for the specified or active provider."""
    target_provider = provider or world.ai_provider
    target_url = url or world.omniroute_url
    
    curated_gemini = [
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
        {"id": "gemini-2.0-flash-lite-preview-02-05", "name": "Gemini 2.0 Flash Lite"},
        {"id": "gemini-2.0-pro-exp-02-05", "name": "Gemini 2.0 Pro Experimental"},
        {"id": "gemini-2.0-flash-thinking-exp-01-21", "name": "Gemini 2.0 Thinking Exp"},
        {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash Exp"},
        {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
        {"id": "gemini-1.5-flash-8b", "name": "Gemini 1.5 Flash-8B"},
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
        {"id": "gemini-1.0-pro", "name": "Gemini 1.0 Pro"},
    ]
    
    curated_omni = [
        {"id": "qwen/qwen-2.5-72b-instruct", "name": "Qwen 2.5 72B (OpenRouter)"},
        {"id": "qwen/qwen-2.5-7b-instruct", "name": "Qwen 2.5 7B (OpenRouter)"},
        {"id": "qwen/qwen-2-vl-72b-instruct", "name": "Qwen 2 VL 72B"},
        {"id": "qwen/qwen-2-5-coder-32b-instruct", "name": "Qwen 2.5 Coder 32B"},
        {"id": "qwen-2.5-72b-instruct", "name": "Qwen 2.5 72B (Local)"},
        {"id": "qwen-2.5-32b-instruct", "name": "Qwen 2.5 32B (Local)"},
        {"id": "qwen-2.5-14b-instruct", "name": "Qwen 2.5 14B (Local)"},
        {"id": "qwen-2.5-7b-instruct", "name": "Qwen 2.5 7B (Local)"},
        {"id": "gpt-4o", "name": "GPT-4o"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
        {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet"},
        {"id": "claude-3-5-haiku", "name": "Claude 3.5 Haiku"},
        {"id": "meta-llama/llama-3.1-70b-instruct", "name": "Llama 3.1 70B"},
        {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B"},
        {"id": "mistralai/mistral-large-2407", "name": "Mistral Large 2"},
        {"id": "mistralai/pixtral-12b-2409", "name": "Pixtral 12B"},
        {"id": "gryphe/mythomax-l2-13b", "name": "MythoMax L2 13B"},
    ]

    final_models = []
    seen_ids = set()

    if target_provider == "gemini":
        # 1. Try to fetch dynamic models from SDK
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                for m in client.models.list():
                    mid = m.name.replace("models/", "")
                    # Filter: Only models starting with "gemini" or "gemma", excluding common non-chat ones
                    starts_with_allowed = mid.startswith("gemini") or mid.startswith("gemma")
                    is_not_aux = all(x not in mid.lower() for x in ["embedding", "vision", "image", "aqa"])
                    
                    if starts_with_allowed and is_not_aux and mid not in seen_ids:
                        final_models.append({"id": mid, "name": m.display_name})
                        seen_ids.add(mid)
            except Exception as e:
                logger.error(f"Error fetching dynamic Gemini models: {e}")
        
        # 2. Supplementary merge with Curated Gemini
        for m in curated_gemini:
            if m["id"] not in seen_ids:
                final_models.append(m)
                seen_ids.add(m["id"])
                
    else:
        # OMNIROUTE / OpenAI style
        base_url = target_url.replace("/chat/completions", "")
        models_url = f"{base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {}
                if OMNIROUTE_API_KEY:
                    headers["Authorization"] = f"Bearer {OMNIROUTE_API_KEY}"
                
                resp = await client.get(models_url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # OpenAI /models usually returns a list in "data"
                    api_data = data.get("data", []) if isinstance(data, dict) else []
                    for m in api_data:
                        mid = m["id"]
                        if mid not in seen_ids:
                            final_models.append({"id": mid, "name": m.get("name", mid)})
                            seen_ids.add(mid)
                    
                    # If we got results from API, return them immediately (no fallback merging)
                    if final_models:
                        final_models.sort(key=lambda x: x["id"])
                        return {"models": final_models}
                else:
                    logger.warning(f"Failed to fetch OMNIROUTE models: {resp.status_code}")
        except Exception as e:
            logger.error(f"Error proxying OMNIROUTE models: {e}")

        # 2. Last resort fallback (only if API fails or is empty)
        for m in curated_omni:
            if m["id"] not in seen_ids:
                final_models.append(m)
                seen_ids.add(m["id"])

    # Stabilize the list order
    final_models.sort(key=lambda x: x["id"])

    # Always ensure a default
    if not final_models:
        final_models.append({"id": "default", "name": "Padrão do Provedor"})

    return {"models": final_models}


# --- Remote Agent API ---

@app.post("/join")
async def join_island(req: JoinRequest):
    # 1. Validar se o ID está na lista de autorizados
    if req.agent_id not in AUTHORIZED_IDS:
        logger.warning(f"Tentativa de entrada com ID não autorizado.")
        raise HTTPException(status_code=401, detail="ID de Acesso não autorizado.")

    # 2. Verificar se o ID já está em uso na ilha
    existing_agent = next((a for a in world.agents if a.id == req.agent_id), None)
    if existing_agent:
        if existing_agent.is_alive:
            raise HTTPException(status_code=400, detail="Este ID já está em uso por um agente Vivo.")
        else:
            # Se está morto, removemos o corpo antigo para dar lugar à nova entrada
            logger.info(f"Agent {existing_agent.name} with ID {req.agent_id} is dead. Removing to allow replacement.")
            world.remove_agent(req.agent_id)

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
