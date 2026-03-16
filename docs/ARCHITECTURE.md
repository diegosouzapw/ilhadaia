# Arquitetura — BBBia v0.6 (feature-diego)

> Estado: **Produção** | Backend: FastAPI 0.111 | Python 3.12 | Março 2026

---

## Visão Geral

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Browser)                              │
│                                                                          │
│  index.html          dashboard.html        models.html                   │
│  ├── Three.js 3D     ├── Chart.js          ├── Testar modelos            │
│  ├── main.js         ├── KPIs ao vivo      ├── Registrar agentes         │
│  ├── benchmark.js    ├── Scoreboard        └── Inspecionar perfis        │
│  ├── Nav global      └── Export CSV/JSON                                 │
│  ├── Sidebar (Replay, Timeline, Benchmark HUD, Atalhos)                  │
│  └── WebSocket /ws                                                       │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │ HTTP REST + WebSocket /ws
┌────────────────────────────▼─────────────────────────────────────────────┐
│                       BACKEND (FastAPI + asyncio)                        │
│                         Porta 8001 | Single Worker                       │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────────┐     │
│  │   World     │  │   Thinker    │  │   TournamentRunner          │     │
│  │  (Motor)    │  │ (Orquestrador│  │  (auto-lifecycle T20)       │     │
│  │  20×20 grid │  │  de decisões)│  │  leaderboard + finalize     │     │
│  └──────┬──────┘  └──────┬───────┘  └─────────────────────────────┘     │
│         │                │                                                │
│  ┌──────▼────────────────▼─────────────────────────────────────────┐    │
│  │                         Agent                                   │    │
│  │  vitals  inventory  can_think()  token_budget  profile_id       │    │
│  │  AgentMemory: short_term + episodic + relational + benchmark    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌──────────────┐  ┌────────────────────────────────────────────────┐   │
│  │   Profiles   │  │         AI Adapters                            │   │
│  │  7 perfis IA │  │  OpenAICompatibleAdapter (OmniRoute + qualquer │   │
│  │  (OmniRoute) │  │  endpoint OpenAI-compatible)                   │   │
│  └──────────────┘  └────────────────┬───────────────────────────────┘   │
│                                     │ HTTPS                              │
└─────────────────────────────────────┼────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼────────────────────────────────────┐
│                      PROVIDERS DE IA (via OmniRoute)                     │
│                                                                          │
│  OmniRoute  http://192.168.0.15:20128/v1  (ou OMNIROUTER_URL)           │
│  ├── kr/ → Kiro (Claude Sonnet/Haiku 4.5 — grátis, ilimitado)           │
│  ├── if/ → iFlow (Kimi K2, Qwen3 — grátis, ilimitado)                   │
│  ├── gc/ → Gemini CLI (Gemini 2.5 Flash — 180K tok/mês grátis)          │
│  └── groq/ → Groq API (Llama 3.3 70B, Kimi K2 — 30 RPM grátis)         │
└──────────────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────────────┐
│                        STORAGE (SQLite WAL)                              │
│  backend/data/ilhadaia.db  (não versionado)                              │
│  ├── sessions          (criação, encerramento, winner)                   │
│  ├── agent_scores      (scoreboard multi-sessão)                         │
│  ├── world_settings_history                                              │
│  ├── agent_memories    (memória persistente entre sessões)               │
│  └── webhooks          (URLs + eventos + HMAC secret)                    │
│                                                                          │
│  backend/logs/*.ndjson         (decision log por sessão)                 │
│  backend/data/replays/*.ndjson (snapshots a cada 5 ticks)                │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Frontend — 3 Interfaces

### `index.html` — Ilha ao Vivo
- Three.js 3D rendering com OrbitControls
- WebSocket `/ws` para estado em tempo real
- `benchmark.js`: HUD de benchmark, replay, modal de agente, timeline de eventos
- Sidebar direita: atalhos rápidos (Dashboard/Modelos), Benchmark HUD, Timeline, Replay
- Nav global flutuante com links para as 3 telas
- Modal `settings-modal` para catálogo de IA (preset auxiliar da UI via `/settings/ai` + `/models`)
- Botão ⚙️ para abrir catálogo de modelos do OmniRoute dinamicamente

### `dashboard.html` — Análise de Sessões
- KPIs ao vivo (ticks, sessões, agentes, torneios, rate limit)
- Gráficos Chart.js: tokens por agente, scores, distribuição de perfis
- Scoreboard global com filtros
- Export CSV/JSON de sessões e decisões
- Nav padronizada (Dashboard ativo em amarelo)

### `models.html` — Gerenciador de Modelos
- Lista de perfis builtin via `GET /profiles` (sincronizada com backend)
- Testes de modelo individuais ou em massa com log de latência
- Tabela de agentes ativos (via WebSocket temporário)
- Formulário de registro dinâmico — dropdown de perfis vem do backend
- Nav padronizada (Modelos ativo em roxo)

---

## Backend — Módulos

### `world.py` — Motor de Simulação
- Grid 20×20 com BFS pathfinding
- Ciclo dia/noite, zumbis, desintegração solar
- Distribuição de turnos por `ai_interval`
- Broadcast de eventos via WebSocket
- Campos auxiliares: `ai_provider`, `ai_model`, `omniroute_url` (preset de catálogo da UI)

### `agent.py` — Agente IA
- Vitals: hp, hunger, thirst, friendship
- Budget: `token_budget`, `tokens_used`, `cooldown_ticks`, `can_think()`
- Memória: `AgentMemory` (4 camadas)
- Benchmark: score, decisions_made, cost_usd, invalid_actions
- `profile_id` — vincula ao perfil de IA do catálogo

### `runtime/profiles.py` — Catálogo de Perfis
7 perfis builtin, todos via OmniRoute (mesmo endpoint, modelo diferente):

| Perfil | Modelo | Provider | Custo |
|--------|--------|----------|-------|
| `claude-kiro` ⭐ padrão | `kr/claude-sonnet-4.5` | Kiro | grátis |
| `claude-haiku` | `kr/claude-haiku-4.5` | Kiro | grátis |
| `kimi-thinking` | `if/kimi-k2` | iFlow | grátis |
| `qwen-coder` | `if/qwen3-coder-plus` | iFlow | grátis |
| `kimi-groq` | `groq/moonshotai/kimi-k2-instruct` | Groq | grátis |
| `gemini-flash` | `gc/gemini-2.5-flash` | Gemini CLI | grátis |
| `llama-groq` | `groq/llama-3.3-70b-versatile` | Groq | grátis |

Configuração:
- `OMNIROUTER_URL` (aliases: `OMNIROUTE_URL`, `OPENAI_BASE_URL`)
- `OMNIROUTER_API_KEY` (aliases: `OMNIROUTE_API_KEY`, `OPENAI_API_KEY`)

### `runtime/thinker.py` — Orquestrador
1. Verifica `can_think()` (budget + cooldown)
2. Constrói contexto (world state + memória relevante via T21)
3. Chama `OpenAICompatibleAdapter` com o perfil do agente
4. Valida resposta com `ActionDecision` (Pydantic)
5. Atualiza memória e benchmark
6. Loga decisão em NDJSON

### `runtime/memory.py` — AgentMemory (T10)
| Camada | Tipo | Limite |
|--------|------|--------|
| `short_term` | Ações recentes | deque max 10 |
| `episodic` | Eventos marcantes | max 50 |
| `relational` | Opiniões sobre outros agentes | sem limite |
| `benchmark` | Métricas de performance | dict |

### `runtime/relevance.py` — Busca Episódica (T21)
- TF-IDF simplificado + pesos por tipo de evento
- Decaimento temporal exponencial
- Retorna top-K episódios mais relevantes
- Sem dependências externas

### `runtime/tournament_runner.py` — TournamentRunner (T20)
- Loop assíncrono (a cada 10s)
- Finaliza automaticamente quando `duration_ticks` é atingido
- Calcula leaderboard final e dispara webhook `tournament_end`

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
              ├─ OpenAICompatibleAdapter.complete(messages, profile)
              ├─ ActionDecision.from_dict(parsed_json) → validação Pydantic
              ├─ agent.agent_memory.add_short_term(action, thought, result)
              ├─ agent.update_benchmark(tokens, cost, latency)
              └─ DecisionLog.log(session, agent, action, tokens)
```

---

## Endpoints Novos (feature-diego)

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `GET /settings/ai` | GET | Retorna preset auxiliar (provider/modelo/url) da UI |
| `POST /settings/ai` | POST | Salva preset auxiliar da UI (admin) |
| `GET /models` | GET | Lista modelos do endpoint OmniRoute dinamicamente |
| `GET /profiles` | GET | Lista os 7 perfis builtin |

---

## Perfis dos 4 NPCs Padrão (feature-diego)

```python
_default_profiles = ["claude-kiro", "kimi-thinking", "kimi-groq", "claude-haiku"]
# João → claude-kiro  | Maria → kimi-thinking
# Zeca → kimi-groq    | Elly  → claude-haiku
```

---

## Resetar Estado Local

```bash
find backend/data -type f -delete
find backend/logs -type f -delete
find backend -maxdepth 1 \( -name 'hall_of_fame.json' -o -name 'world_settings.json' \) -delete
```

---

## Rate Limiting (T18)

| Endpoint | Limite |
|----------|--------|
| `POST /agents/register` | 10 req/min |
| `POST /tournaments` | 5 req/min |
| `POST /webhooks/register` | 20 req/hora |

---

## Dependências

```
fastapi, uvicorn    # Framework web + ASGI
pydantic            # Validação de schemas
python-dotenv       # Config por env
openai              # Adapter OpenAI-compatible (OmniRoute)
google-genai        # Adapter Gemini nativo (opcional)
slowapi             # Rate limiting
httpx               # HTTP async (webhooks + /models proxy)
pytest              # Testes unitários (33 casos)
```
