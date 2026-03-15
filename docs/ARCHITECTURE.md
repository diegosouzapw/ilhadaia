# 🏗️ Arquitetura — BBBia Versão Turbinada v0.5

> Estado: **Produção** (março 2026) | Backend: FastAPI 0.115 | Python 3.12

---

## Visão Geral

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Browser)                           │
│   index.html           dashboard.html                               │
│   ├── Three.js 3D      ├── Chart.js                                 │
│   ├── main.js          ├── KPIs ao vivo                             │
│   ├── benchmark.js     ├── Scoreboard + Gráficos                    │
│   └── WebSocket WS     └── Export CSV/JSON                          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ HTTP REST + WebSocket /ws
┌─────────────────────────────▼───────────────────────────────────────┐
│                     BACKEND (FastAPI + asyncio)                     │
│                      Porta 8001 | Single Worker                     │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   World     │  │   Thinker    │  │   TournamentRunner       │  │
│  │  (Motor)    │  │ (Orquestrador│  │  (auto-lifecycle)        │  │
│  │  20×20 grid │  │  de decisões)│  │  leaderboard + finalize  │  │
│  └──────┬──────┘  └──────┬───────┘  └──────────────────────────┘  │
│         │                │                                           │
│  ┌──────▼──────────────────▼────────────────────────────────────┐  │
│  │                    Agent                                      │  │
│  │  vitals   inventory   can_think()   token_budget              │  │
│  │  AgentMemory: short_term + episodic + relational + benchmark  │  │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────┐  ┌────────────────────────────────────────────┐  │
│  │   Profiles   │  │         AI Adapters                        │  │
│  │ 6 perfis IA  │  │  GeminiAdapter  OpenAICompatibleAdapter     │  │
│  └──────────────┘  └────────────────┬───────────────────────────┘  │
│                                     │                                │
└─────────────────────────────────────┼────────────────────────────── ┘
                                      │ HTTPS
┌─────────────────────────────────────▼───────────────────────────────┐
│                        PROVIDERS DE IA                               │
│  Google Gemini API           OmniRouter (http://localhost:20128)    │
│  gemini-2.5-flash-lite       → Gemini, GPT-4o-mini, Llama, Claude  │
└──────────────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────────┐
│                       STORAGE (SQLite WAL)                          │
│  ilhadaia.db                                                         │
│  ├── sessions          (criação, encerramento, winner)              │
│  ├── agent_scores      (scoreboard multi-sessão)                    │
│  ├── world_settings_history                                          │
│  ├── agent_memories    (memória persistente entre sessões)          │
│  └── webhooks          (URLs + eventos + HMAC secret)               │
│                                                                      │
│  logs/*.ndjson         (decision log por sessão)                    │
│  data/replays/*.ndjson (snapshots a cada 5 ticks)                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Módulos do Backend

### `world.py` — Motor de Simulação
- Grid 20×20 com BFS pathfinding
- Ciclo dia/noite, zumbis, desintegração solar
- Distribuição de turnos por `ai_interval`
- Broadcast de eventos via WebSocket

### `agent.py` — Agente IA
- Vitals: hp, hunger, thirst, friendship
- Budget: `token_budget`, `tokens_used`, `cooldown_ticks`, `can_think()`
- Memória: `AgentMemory` (4 camadas, T10)
- Benchmark: score, decisions_made, cost_usd, invalid_actions

### `runtime/thinker.py` — Orquestrador
1. Verifica `can_think()` (budget + cooldown)
2. Constrói contexto (world state + memória relevante via T21)
3. Chama adapter (Gemini ou OmniRouter)
4. Valida resposta com `ActionDecision` (T11)
5. Atualiza memória e benchmark
6. Loga decisão em NDJSON (T03)

### `runtime/memory.py` — AgentMemory (T10)
| Camada | Tipo | Limite |
|--------|------|--------|
| `short_term` | Ações recentes | deque max 10 |
| `episodic` | Eventos marcantes (morte, ataque, aliança) | max 50 |
| `relational` | Opiniões sobre outros agentes (-1..+1) | sem limite |
| `benchmark` | Métricas de performance | dict herdado do Agent |

### `runtime/relevance.py` — Busca Episódica (T21)
- TF-IDF simplificado + pesos por tipo de evento
- Decaimento temporal exponencial (`exp(-rate * ticks_ago)`)
- Retorna top-K episódios mais relevantes para o contexto atual
- Sem dependências externas (sem ChromaDB)

### `runtime/tournament_runner.py` — TournamentRunner (T20)
- Loop assíncrono que verifica todos os torneios ativos a cada 10s
- Finaliza automaticamente quando `duration_ticks` é atingido
- Calcula leaderboard final (score + alive + decisions)
- Suporte a `reset_on_finish`

### `storage/` — Persistência
| Módulo | Tecnologia | O que armazena |
|--------|-----------|----------------|
| `session_store.py` | SQLite WAL | sessões, scores, world_settings |
| `decision_log.py` | NDJSON | decisões de IA por sessão |
| `replay_store.py` | NDJSON | snapshots por tick (a cada 5) |
| `memory_store.py` | SQLite WAL | AgentMemory serializada por owner |
| `webhook_manager.py` | SQLite WAL | URLs, eventos, fire_count |

---

## Fluxo de uma Decisão de IA

```
tick N
  └─ World seleciona agente (por ai_interval ou paralelo)
      └─ agent.can_think()? (budget + cooldown)
          └─ Thinker.think(agent, world_context)
              ├─ Relevance.get_relevant(episodes, context, tick)
              ├─ SchemaPrompt = ActionDecision.get_json_schema_prompt()
              ├─ Adapter.complete(messages) → raw_response
              ├─ ActionDecision.from_dict(parsed_json) → validação Pydantic
              ├─ agent.agent_memory.add_short_term(action, thought, result)
              ├─ agent.update_benchmark(tokens, cost, latency)
              └─ DecisionLog.log(session, agent, action, tokens)
```

---

## Rate Limiting (T18)

Implementado via `slowapi` com chave por IP:

| Endpoint | Limite |
|----------|--------|
| `POST /agents/register` | 10 req/min |
| `POST /tournaments` | 5 req/min |
| `POST /webhooks/register` | 20 req/hora |

---

## Sistema de Webhooks (T24)

```
Evento (death/win/zombie/tournament_end)
  └─ WebhookManager.fire_event(event_type, payload)
      └─ Para cada webhook registrado que escuta esse evento:
          ├─ Monta body JSON: { event, timestamp, payload }
          ├─ Assina com HMAC-SHA256 se secret configurado
          └─ POST async (httpx, timeout=5s)
```

---

## Limitações Conhecidas

| Limitação | Status | Plano |
|-----------|--------|-------|
| Single worker (não escala horizontalmente) | Ativo | T17 (Redis pub/sub — Backlog) |
| Frontend via `file://` tem CORS `null` habilitado | Ativo, controlado | Produção via nginx |
| SQLite não é adequado para >1000 writes/seg | Não é o caso | Usar WAL, ok para escala atual |

---

## Dependências

```
fastapi, uvicorn          # Framework web + ASGI
pydantic                  # Validação de schemas
python-dotenv             # Config por env
google-genai              # Adapter Gemini nativo
openai                    # Adapter OmniRouter/OpenAI-compat
slowapi                   # Rate limiting
httpx                     # HTTP async para webhooks
pytest                    # Testes unitários (31 casos)
```
