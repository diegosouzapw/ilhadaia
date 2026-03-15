# 🗒️ Plano de Implementação — BBBia Versão Turbinada

> Atualizado: Março 2026 | Versão: v0.5 | Status: **T17 no backlog, T01–T16 + T18–T24 implementadas**

---

## Resumo do Roadmap

| Versão | Foco | Tasks | Status |
|--------|------|-------|--------|
| v0.2 — Engine Confiável | Segurança, budget, storage | T01–T06 | ✅ 100% |
| v0.3 — Multi-Provider Benchmark | Adapters, perfis, thinker, memória, schema, testes | T07–T12 | ✅ 100% |
| v0.4 — Plataforma de Competição | Replay, registro, torneios, frontend | T13–T16 | ✅ 100% |
| v0.5 — Escala & Intelligence | Rate limit, export, tournament runner, relevância, memória, dashboard, webhooks | T18–T24 | ✅ 100% |
| Backlog | Redis pub/sub multi-worker | T17 | ⏳ Backlog |

---

## v0.2 — Engine Confiável ✅

### T01 — Admin Token
**Arquivo:** `backend/main.py`  
Endpoint `DELETE /agent/{id}` protegido com `X-Admin-Token` via `Depends(verify_admin_token)`. Retorna 401 sem token.

### T02 — Budget & Cooldown
**Arquivo:** `backend/agent.py`  
Adicionados: `token_budget`, `tokens_used`, `cooldown_ticks`, `last_thought_tick`, `benchmark`, `can_think()`, `update_benchmark()`.

### T03 — Decision Log
**Arquivo:** `backend/storage/decision_log.py`  
Log NDJSON por sessão. Cada linha: `{session_id, tick, agent_id, action, thought, tokens_used, cost_usd, latency_ms}`.

### T04 — SQLite Scoreboard
**Arquivo:** `backend/storage/session_store.py`  
SQLite WAL com tabelas: `sessions`, `agent_scores`, `world_settings_history`. Métodos: `create_session`, `end_session`, `upsert_agent_score`, `get_scoreboard`.

### T05 — Lifespan Migration
**Arquivo:** `backend/main.py`  
`@app.on_event` substituído por `@asynccontextmanager async def lifespan(app)`. Inclui startup e shutdown limpos.

### T06 — Docker
**Arquivos:** `backend/Dockerfile`, `docker-compose.yml`, `.env.example`  
Serviços: `backend` (FastAPI) + `nginx` (proxy reverso). Build multi-stage.

---

## v0.3 — Multi-Provider Benchmark ✅

### T07 — AI Adapters
**Arquivos:** `backend/runtime/adapters/base.py`, `gemini.py`, `openai_compatible.py`  
`AIAdapter` (abstract), `AIResponse` (dataclass), `GeminiAdapter` (google-genai SDK), `OpenAICompatibleAdapter` (openai SDK → OmniRouter).

### T08 — Agent Profiles
**Arquivo:** `backend/runtime/profiles.py`  
6 perfis: `gemini-native`, `cheap-fast`, `balanced`, `smart`, `oss-fast`, `creative`. Configurados com `provider`, `model`, `token_budget`, `cooldown_ticks`, `max_tokens`.

### T09 — Thinker
**Arquivo:** `backend/runtime/thinker.py`  
Orquestrador central: `can_think()` → montar contexto → chamar adapter → validar com ActionDecision → atualizar memória → logar decisão.

### T10 — Memória 4 Camadas
**Arquivo:** `backend/runtime/memory.py`  
`AgentMemory` com `ShortTermEntry` (deque max 10), `EpisodicEntry` (max 50), `RelationalEntry` (opiniões -1..+1), benchmark herdado do Agent.

### T11 — Structured Output
**Arquivo:** `backend/runtime/schemas.py`  
`ActionDecision` Pydantic: validação de `action` (enum), `intent` (max 100 chars), alias `speech→speak`, `to_world_action()`, `from_dict()` seguro, `get_json_schema_prompt()`.

### T12 — Testes Unitários
**Arquivo:** `backend/tests/test_engine.py`  
31 testes pytest: `TestActionDecision`, `TestAgentMemory`, `TestProfiles`, `TestAIResponse`, `TestDecisionLog`, `TestSessionStore`. **31/31 passing ✅**

---

## v0.4 — Plataforma de Competição ✅

### T13 — Replay System
**Arquivo:** `backend/storage/replay_store.py`  
Snapshots NDJSON a cada 5 ticks por sessão. Métodos: `start_session`, `save_snapshot`, `load_session`, `get_frame`.

### T14 — Agent Registration
**Endpoint:** `POST /agents/register`  
Registro de agentes externos com `owner_id`, `agent_name`, `persona`, `profile_id`. Agente ativo na ilha automaticamente.

### T15 — Tournament API
**Endpoints:** `POST /tournaments`, `POST /tournaments/{id}/join`, `POST /tournaments/{id}/start`, `GET /tournaments/{id}/leaderboard`  
Torneios em memória com registro de agentes e leaderboard ao vivo.

### T16 — Frontend Turbinado
**Arquivos:** `frontend/index.html`, `frontend/benchmark.js`, `frontend/style.css`  
HUD Benchmark (🏆), Painel de Replay (▶), Timeline de Eventos (📜), Modal de Agente Detalhado.

---

## v0.5 — Escala & Intelligence ✅

### T18 — Rate Limiting
**Arquivo:** `backend/main.py` (slowapi)  
Rate limit por IP em endpoints públicos. `/agents/register`: 10/min, `/tournaments`: 5/min, `/webhooks/register`: 20/hora.

### T19 — Exportação CSV/JSON
**Endpoints:**
- `GET /sessions/{id}/export?format=csv|json`
- `GET /world/scoreboard/export?format=csv|json`
- `GET /sessions/{id}/decisions/export?format=csv|json`

`StreamingResponse` com `Content-Disposition` para download direto.

### T20 — Tournament Runner
**Arquivo:** `backend/runtime/tournament_runner.py`  
`TournamentRunner` com loop assíncrono de monitoramento. Finalização automática por `duration_ticks`. Leaderboard ao vivo e final. `GET /tournaments/{id}/status` com `progress_pct` e `ticks_remaining`.

### T21 — Relevância Episódica
**Arquivo:** `backend/runtime/relevance.py`  
`EpisodicRelevanceEngine`: TF-IDF simplificado + pesos por tipo de evento (`death=3.0`, `attack=2.5`, `move=0.5`) + decaimento temporal exponencial. Sem ChromaDB.

### T22 — Memória Persistente
**Arquivo:** `backend/storage/memory_store.py`  
`MemoryStore` salva/restaura `AgentMemory` (4 camadas) no SQLite entre sessões para agentes com `owner_id`. Endpoints: `GET /memories`, `POST /memories/save/{id}`.

### T23 — Dashboard de Análise
**Arquivo:** `frontend/dashboard.html`  
Dashboard completo: KPIs ao vivo, Chart.js (tokens/scores), comparação de modelos por score médio, scoreboard global, histórico de sessões, seletor de sessão + export CSV.

### T24 — Notificações Push
**Arquivo:** `backend/storage/webhook_manager.py`  
`WebhookManager` com registro de URLs por owner, filtragem por tipo de evento, disparo assíncrono com `httpx` e assinatura HMAC-SHA256. Endpoints: register, list, delete, test.

---

## Backlog

### T17 — Redis WebSocket (pub/sub) — ⏳ Backlog
**Arquivo planejado:** `backend/messaging/redis_pubsub.py`  
Substituir broadcast em memória por Redis Pub/Sub para suportar múltiplos workers uvicorn. Requer instalação e configuração de Redis como serviço externo.

**Dependências:** `redis`, `aioredis` | **Estimativa:** 2–3h | **Impacto:** Alto (necessário para escala horizontal)

Ver [`BACKLOG.md`](./BACKLOG.md) para detalhes completos.

---

## Critérios de Aceite Globais

- ✅ Backend sem erro em startup
- ✅ 31/31 testes unitários passando
- ✅ Frontend conecta e exibe estado em tempo real
- ✅ Dashboard carrega KPIs e scoreboard
- ✅ Webhook registrado e listado com sucesso
- ✅ Export CSV de scoreboard com 175+ entradas
- ✅ Torneio com status detalhado e leaderboard
