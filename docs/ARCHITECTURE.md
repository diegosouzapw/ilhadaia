# Arquitetura — BBBia v0.8 (feature-diego)

> Estado: **Produção** | Backend: FastAPI 0.111 | Python 3.12 | Março 2026 | 174 testes

---

## Visão Geral

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Browser)                              │
│  index.html          dashboard.html        models.html                   │
│  ├── Three.js 3D     ├── Chart.js          ├── Testar modelos            │
│  ├── main.js         ├── KPIs ao vivo      ├── Registrar agentes         │
│  ├── benchmark.js    ├── Scoreboard        └── Inspecionar perfis        │
│  └── WebSocket /ws   └── Export CSV/JSON                                 │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │ HTTP REST + WebSocket /ws
┌────────────────────────────▼─────────────────────────────────────────────┐
│                       BACKEND (FastAPI + asyncio)                        │
│                         Porta 8001 | Single Worker                       │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    World (Motor Central)                         │    │
│  │  grid dinâmico (32×32 → 44×44 por game_mode)                    │    │
│  │  tick loop → thinker → engines → broadcast WebSocket            │    │
│  │                                                                  │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │
│  │  │GincanaEngine │  │WarfareEngine │  │   EconomyEngine      │  │    │
│  │  │ F12          │  │  F13-F16     │  │  F10/F17/F18/F19     │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │
│  │  ┌──────────────┐                                               │    │
│  │  │GangWarEngine │                                               │    │
│  │  │     F20      │                                               │    │
│  │  └──────────────┘                                               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌──────────────┐  ┌────────────────────┐  ┌──────────────────────┐    │
│  │   Thinker    │  │  TournamentRunner  │  │  WebhookManager F11  │    │
│  │ (decisão IA) │  │  (torneios auto)   │  │  (16 tipos + retry)  │    │
│  └──────────────┘  └────────────────────┘  └──────────────────────┘    │
└─────────────────────────────────────┬────────────────────────────────────┘
                                      │ HTTPS
┌─────────────────────────────────────▼────────────────────────────────────┐
│                      PROVIDERS DE IA (via OmniRoute)                     │
│  kr/ Kiro │ if/ iFlow │ gc/ Gemini CLI │ groq/ Groq                      │
└──────────────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────────────┐
│                        STORAGE (SQLite WAL)                              │
│  sessions + agent_scores + world_settings_history                        │
│  agent_memories + webhooks + webhook_deliveries                          │
│  backend/logs/*.ndjson  (decision log por sessão)                        │
│  backend/data/replays/*.ndjson  (snapshots a cada 5 ticks)               │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Modos de Jogo

| Modo | Grid | Engine | Features |
|------|------|--------|---------|
| `survival` | 32×32 | — (World nativo) | Recursos, zumbis, ciclo dia/noite |
| `gincana` | 32×32 | `GincanaEngine` | F12: checkpoints, artefato, placar, timer |
| `warfare` | 40×40 | `WarfareEngine` | F13-F16: facções, throw_stone AOE, papéis, território |
| `economy` | 36×36 | `EconomyEngine` | F10/F17-F19: crafting, trade, mercado, contratos |
| `gangwar` | 40×40 | `GangWarEngine` | F20: gangues, depósito, sabotagem, black market |
| `hybrid` | 44×44 | — | Expansão futura |

---

## Engines de Runtime

### `runtime/gincana_engine.py` — F12

- **Checkpoints:** 5 espalhados pelo mapa, 5 pts por captura
- **Artefato:** pickup + deliver = 20 pts
- **Timer global:** `max_ticks` configurável (default 400)
- **Endpoints:** `POST /gincana/start|stop`, `GET /gincana/state|templates`

### `runtime/warfare_engine.py` — F13-F16

- **F13 Facções:** 2 equipes (alpha/beta), `base_hp=100`, `agent.faction`
- **F14 Arremesso:** `throw_stone()`: dano 15 HP, AOE raio 1, alcance 5 tiles; Warriors auto-disparam
- **F15 Papéis táticos:** scout (+visão), medic (cura +5 HP aliados/5 ticks), warrior (×1.5 dano)
- **F16 Território:** zona central → 3 ticks consecutivos → captura → +2 pts/tick
- **Endpoints:** `POST /warfare/start|stop|throw`, `GET /warfare/state|roles|territory`

### `runtime/economy_engine.py` — F10/F17/F18/F19

- **F10 Crafting:** 5 receitas (`axe`, `raft`, `wall`, `torch`, `bandage`); `craft()` consome ingredientes
- **F17 Trade P2P:** `trade(seller, buyer, item, price)`; agentes recebem 10 moedas ao `start()`
- **F18 Mercado:** `market_buy/sell`; `_recalc_prices()`: preços 0.5×–3× base por escassez/excesso
- **F19 Contratos:** `post_contract` reserva recompensa; `fulfill_contract` paga + `trade_reputation`
- **Endpoints:** `/economy/*`, `/market/*`

### `runtime/gangwar_engine.py` — F20

- **Gangues:** Alpha/Beta com atribuição automática, `agent.faction`
- **Depósito compartilhado:** `deposit/withdraw`, capacidade 50 itens por gangue
- **Sabotagem:** trava depósito inimigo 15 ticks + -1/3 recursos
- **Supply posts:** captura por presença (raio 2), renda passiva a cada 10 ticks
- **Black market:** 5 itens exclusivos, preços voláteis ±40% a cada 15 ticks (usa `economy.coins`)
- **Endpoints:** `POST /gangwar/start|stop|sabotage|depot/deposit|depot/withdraw|bm/buy`, `GET /gangwar/state|depot/{gang}|bm/prices`

---

## Backend — Módulos Core

### `world.py` — Motor de Simulação

- Grid dinâmico via `MODE_SIZES` (32 a 44 por `game_mode`)
- BFS pathfinding, ciclo dia/noite, zumbis, desintegração solar
- Integra todos os 4 engines: `self.gincana`, `self.warfare`, `self.economy`, `self.gangwar`
- Engines ficam ativos o tempo todo; `tick()` os ativa condicionalmente por `game_mode`
- `get_state()` inclui estado do engine ativo no campo correspondente

### `agent.py` — Agente IA

- Vitals: `hp`, `hunger`, `thirst`, `friendship`, `faction`, `role`
- Budget: `token_budget`, `tokens_used`, `cooldown_ticks`, `can_think()`
- Memória: `AgentMemory` (4 camadas: short_term, episodic, relational, benchmark)
- `profile_id` — vincula ao perfil de IA

### `runtime/profiles.py` — Catálogo

| Perfil | Modelo | Provider |
|--------|--------|----------|
| `claude-kiro` ⭐ | `kr/claude-sonnet-4.5` | Kiro |
| `claude-haiku` | `kr/claude-haiku-4.5` | Kiro |
| `kimi-thinking` | `if/kimi-k2` | iFlow |
| `qwen-coder` | `if/qwen3-coder-plus` | iFlow |
| `kimi-groq` | `groq/moonshotai/kimi-k2-instruct` | Groq |
| `gemini-flash` | `gc/gemini-2.5-flash` | Gemini CLI |
| `llama-groq` | `groq/llama-3.3-70b-versatile` | Groq |

### `storage/webhook_manager.py` — F11 Webhooks (Expandido)

- **16 tipos de evento:** `agent_dead`, `winner_declared`, `checkpoint_captured`, `artifact_delivered`, `sabotage`, `gangwar_end`, `gincana_end`, `warfare_end`, `contract_fulfilled`, `trade`, `market_buy`, `market_sell` + originais
- **Retry configurável** por webhook (padrão 3, máx 5) com backoff exponencial (2s→4s→8s)
- **Tabela `webhook_deliveries`:** persiste status, tentativa, http_code e erro
- **Endpoints:** `GET /webhooks/admin/history|stats|event-types`
- **Schema migration:** `_migrate()` para DBs legados

---

## Endpoints por Domínio

| Domínio | Endpoints |
|---------|-----------|
| **World/Agents** | `GET /state`, `POST /reset`, `POST /agents/register`, `GET /agents` |
| **Gincana F12** | `POST /gincana/start|stop`, `GET /gincana/state|templates` |
| **Warfare F13-F16** | `POST /warfare/start|stop|throw`, `GET /warfare/state|roles|territory` |
| **Economy F10/F17-F19** | `GET /economy/state|recipes|coins|contracts|reputation`, `POST /economy/craft|trade|contracts|contracts/fulfill` |
| **Market F18** | `GET /market/prices`, `POST /market/buy|sell` |
| **GangWar F20** | `POST /gangwar/start|stop|sabotage|depot/deposit|depot/withdraw|bm/buy`, `GET /gangwar/state|depot/{gang}|bm/prices` |
| **Webhooks F11** | `POST /webhooks/register|test/{id}`, `GET /webhooks/{owner_id}`, `DELETE /webhooks/{id}`, `GET /webhooks/admin/history|stats|event-types` |
| **AI Features** | `GET /profiles|models`, `POST /settings/ai`, `GET /settings/ai` |
| **Torneios** | `POST /tournaments`, `GET /tournaments/{id}` |

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

## Rate Limiting

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
slowapi             # Rate limiting
httpx               # HTTP async (webhooks + /models proxy)
pytest              # 174 testes automatizados
```
