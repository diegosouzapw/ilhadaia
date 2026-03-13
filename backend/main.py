import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import logging

from world import World
from agent import Agent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BBB_IA")

app = FastAPI(title="BBB de IA - Backend Engine")

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
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

@app.post("/reset")
async def reset_game(player_count: int = 4):
    world.reset_agents(Agent, player_count=player_count)
    await manager.broadcast({"type": "reset", "data": world.get_state()})
    return {"status": "World reset successful", "player_count": player_count}

@app.post("/settings/ai_interval")
async def set_ai_interval(interval: int):
    world.ai_interval = max(0, interval)
    world._save_history() # Persist change
    logger.info(f"AI decision interval updated to: {world.ai_interval}")
    return {"status": "Interval updated", "new_interval": world.ai_interval}
