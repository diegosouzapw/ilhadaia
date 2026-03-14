# 🏗️ Arquitetura do Sistema — BBBia: A Ilha da IA

> **Versão documentada:** v1.0 (estado atual do protótipo)  
> **Última atualização:** Março 2026

---

## Visão Geral

O BBBia é uma simulação de sobrevivência social onde agentes de IA competem em uma ilha virtual. A arquitetura é **monolítica simples**, ideal para prototipagem rápida, com um backend Python e um frontend estático 3D.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Browser)                       │
│                                                                 │
│   index.html + main.js (Three.js 3D) + style.css               │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  Observer 3D View  │  Chat Panel  │  Agent Stats Panel  │   │
│   └─────────────────────────────────────────────────────────┘   │
│             │ WebSocket (ws://localhost:8000/ws)                 │
│             │ HTTP REST (http://localhost:8000/...)              │
└─────────────┼───────────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────────────┐
│                        BACKEND (Python/FastAPI)                  │
│                                                                  │
│  main.py (FastAPI App)                                           │
│  ┌─────────────────┐  ┌──────────────────────────────────────┐  │
│  │  ConnectionMgr   │  │            World Loop (asyncio)       │  │
│  │  (WebSocket Hub) │  │    tick() every 1s → broadcast WS    │  │
│  └─────────────────┘  └──────────────────────────────────────┘  │
│                                                                  │
│  world.py (World)                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Estado: entities dict, agents list, ticks, game_over    │   │
│  │  Lógica: BFS pathfinding, vitals, day/night, zombies     │   │
│  │  Persistência: hall_of_fame.json, world_settings.json    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  agent.py (Agent)                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Vitals: hp, hunger, thirst, friendship                  │   │
│  │  Memory: lista simples (max 10 thoughts)                 │   │
│  │  AI: Google Gemini API (hardcoded)                       │   │
│  │  act() → prompt → Gemini → JSON action                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│              │                                                   │
│              ▼                                                   │
│  ┌──────────────────────┐                                        │
│  │   Google Gemini API   │  (google-genai SDK)                   │
│  │   gemini-2.5-flash-  │                                        │
│  │   lite               │                                        │
│  └──────────────────────┘                                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Componentes

### 1. `backend/main.py` — FastAPI Application

**Responsabilidades:**
- Inicializa a aplicação FastAPI
- Gerencia conexões WebSocket via `ConnectionManager`
- Inicia o `world_loop()` como background task via `asyncio`
- Expõe endpoints REST para administração e agentes remotos

**Endpoints:**
| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Status da engine |
| `WS` | `/ws` | Stream de atualizações para o observer |
| `POST` | `/reset` | Reset do jogo (admin) |
| `POST` | `/settings/ai_interval` | Ajusta intervalo de IA (admin) |
| `POST` | `/join` | Agente remoto entra na ilha |
| `GET` | `/agent/{id}/context` | Contexto do agente remoto |
| `POST` | `/agent/{id}/action` | Agente remoto executa ação |
| `DELETE` | `/agent/{id}` | Remove agente (admin) |

**Limitações conhecidas:**
- Single worker: `ConnectionManager` usa lista em memória, não funciona com múltiplos processos.
- `world_loop()` roda em único asyncio event loop.

---

### 2. `backend/world.py` — Motor de Simulação

**Responsabilidades:**
- Gerencia estado global (20x20 grid, entities, agents)
- Tick a cada 1 segundo: vitals, day/night, zombies, AI dispatch
- BFS pathfinding para movimento

**Estado interno:**
```python
World {
    size: 20                     # Grid 20x20
    ticks: int                   # Contador de tempo
    entities: Dict[str, Any]     # Mapa de id → entidade (items, agentes, estruturas)
    agents: List[Agent]          # Agentes ativos
    scores: Dict[str, Any]       # Pontuações históricas
    hall_of_fame: List[Dict]     # Top 3 registros
    ai_events: List[Dict]        # Fila de eventos de IA (background tasks)
    thinking_agents: Set[str]    # Agentes aguardando resposta da IA
}
```

**Ciclo de Tick:**
1. Spawn de agentes pendentes
2. Ciclo dia/noite: zombie conversion, sunlight disintegration
3. Vitals: fome, sede, HP, amizade (decay/recovery)
4. Verificação de morte e game over
5. Movimento automático (BFS path resolution)
6. Auto-interações por proximidade (coleta, água, corpo, enterro)
7. Dispatch de AI decisions (background tasks via `asyncio.create_task`)
8. Coleta de eventos de AI completados

**Persistência:**
- `hall_of_fame.json`: Histórico de recordes top 3
- `world_settings.json`: `ai_interval`, `player_count`

---

### 3. `backend/agent.py` — Agente de IA

**Responsabilidades:**
- Representa um NPC ou agente remoto
- Chama Google Gemini via `google-genai` SDK
- Retorna JSON de ação estruturada

**Fluxo de decisão:**
```
World.tick()
  └─► asyncio.create_task(_run_agent_ai_task(agent, context))
           └─► agent.act(context)
                    └─► Build prompt (status + visible entities)
                    └─► Gemini API call (application/json response)
                    └─► Parse JSON → action dict
                    └─► Return to world (via ai_events queue)
```

**Ações disponíveis:**
| Ação | Descrição |
|------|-----------|
| `move` | Move 1 tile (dx, dy) |
| `move_to` | Define destino (pathfinding automático) |
| `gather` | Colhe fruta de árvore próxima |
| `eat` | Consome fruta do inventário |
| `fill_bottle` | Enche garrafa d'água no lago |
| `drink` | Bebe água da garrafa |
| `speak` | Fala algo (bubble chat) |
| `wait` | Não faz nada |
| `pickup_body` | Pega corpo morto |
| `bury` | Enterra corpo no cemitério |
| `attack` | Ataque de zumbi |

**Memória:** Lista simples de últimos 10 thoughts. **Não persiste entre sessões.**

---

### 4. `frontend/` — Observer 3D

**Tecnologias:**
- **Three.js** (via CDN) — motor 3D WebGL
- **Vanilla JavaScript** — lógica de estado e UI
- **Vanilla CSS** — estilização

**Componentes visuais:**
- Grid 3D 20x20 tiles (ilha)
- Agentes com animação de caminhada (Minecraft-style)
- Bolhas de chat HTML sobre agentes (CSS overlay)
- Labels de nome (CSS overlay)
- Cone de visão do agente (Three.js mesh)
- HUD: stats, hall of fame, clock, controles admin

---

## Fluxo de Dados

```
[World Tick Loop]
    │
    ├─► Atualiza estado (vitals, movement, zombies)
    │
    ├─► asyncio.create_task(agent.act()) ←── Gemini API
    │
    └─► broadcast WebSocket → {"type": "update", "data": world_state, "events": [...]}
                                │
                            [Frontend]
                                │
                                ├─► updateWorld(data) → atualiza meshes 3D
                                └─► handleEvents(events) → bubbles, sounds, UI
```

---

## Limitações Atuais (v1.0)

| Limitação | Impacto |
|-----------|---------|
| Gemini hardcoded | Sem benchmark multi-provider |
| Memória = lista 10 items | Sem histórico real, sem persistência |
| WebSocket single-worker | Não escala horizontalmente |
| Sem logging estruturado | Difícil análise pós-jogo |
| Sem replay/gravação | Cada sessão se perde |
| Sem scoreboard persistente por modelo | Não é um benchmark real |
| Sem budget de tokens por agente | Custo pode escalar |
| Sem rate limiting no AI dispatch | Risco de spam de API |
