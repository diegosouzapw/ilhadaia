# Current State Audit — BBBia v0.6 (feature-diego)

> Auditoria: Março 2026 | Branch: feature-diego

---

## Status Geral: ✅ Operacional

---

## Backend

| Módulo | Status | Observação |
|--------|--------|-----------|
| `main.py` | ✅ | 30+ endpoints REST + WebSocket + StaticFiles |
| `world.py` | ✅ | Motor 20×20, ciclo dia/noite, torneios, campos de catálogo de IA |
| `agent.py` | ✅ | Vitals, budget, 4 camadas de memória, profile_id |
| `runtime/thinker.py` | ✅ | OpenAICompatibleAdapter, can_think(), logging |
| `runtime/profiles.py` | ✅ | 7 perfis free-first via OmniRoute |
| `runtime/adapters/openai_compat.py` | ✅ | Adapter único para qualquer endpoint OpenAI-compat |
| `runtime/memory.py` | ✅ | AgentMemory 4 camadas |
| `runtime/relevance.py` | ✅ | TF-IDF + decaimento temporal |
| `runtime/tournament_runner.py` | ✅ | Auto-finalização, leaderboard, webhook |
| `storage/session_store.py` | ✅ | SQLite WAL — sessões e scoreboard |
| `storage/decision_log.py` | ✅ | NDJSON por sessão |
| `storage/replay_store.py` | ✅ | Snapshots a cada 5 ticks |
| `storage/memory_store.py` | ✅ | Memória persistente entre sessões |
| `storage/webhook_manager.py` | ✅ | HMAC + fire_count |

---

## Frontend

| Arquivo | Status | Observação |
|---------|--------|-----------|
| `index.html` | ✅ | Observer 3D + sidebar + nav global + modal de catálogo IA |
| `dashboard.html` | ✅ | KPIs + gráficos + scoreboard + export + nav |
| `models.html` | ✅ | Perfis dinâmicos + testes + agentes + registro + nav |
| `main.js` | ✅ | Three.js, WebSocket, HUD, modal de agente, catálogo IA |
| `benchmark.js` | ✅ | Benchmark HUD (arrastável, colapsável), replay, timeline |
| `style.css` | ✅ | CSS da ilha + nav global + sidebar + modal de catálogo |

---

## Configuração de Modelos

| Perfil | Modelo | Testado | Observação |
|--------|--------|---------|-----------|
| `claude-kiro` | `kr/claude-sonnet-4.5` | ✅ | Padrão — grátis, ilimitado |
| `claude-haiku` | `kr/claude-haiku-4.5` | ✅ | Rápido — grátis, ilimitado |
| `kimi-thinking` | `if/kimi-k2` | ✅ | Grátis, ilimitado |
| `qwen-coder` | `if/qwen3-coder-plus` | ⚠️ | Grátis, a testar |
| `kimi-groq` | `groq/moonshotai/kimi-k2-instruct` | ✅ | Grátis, 30 RPM |
| `gemini-flash` | `gc/gemini-2.5-flash` | ⚠️ | Sujeito a rate limit de conta |
| `llama-groq` | `groq/llama-3.3-70b-versatile` | ✅ | Grátis, 30 RPM |

---

## 4 NPCs da Ilha

| NPC | Perfil | Modelo |
|-----|--------|--------|
| João | `claude-kiro` | `kr/claude-sonnet-4.5` |
| Maria | `kimi-thinking` | `if/kimi-k2` |
| Zeca | `kimi-groq` | `groq/moonshotai/kimi-k2-instruct` |
| Elly | `claude-haiku` | `kr/claude-haiku-4.5` |

---

## Endpoints Novos (feature-diego)

| Endpoint | Status |
|----------|--------|
| `GET /settings/ai` | ✅ |
| `POST /settings/ai` | ✅ |
| `GET /models` | ✅ |
| `GET /profiles` | ✅ (já era, agora com 7 perfis) |

---

## Testes

- `pytest backend/tests/ -q` → **33 passed**
- Cobertura: engine, memória, benchmark, adapters, schemas

---

## Gitignore

Arquivos corretamente excluídos do versionamento:
- `*.db`, `*.db-shm`, `*.db-wal`
- `backend/logs/`, `logs/`
- `backend/data/replays/`, `data/replays/`
- `backend/hall_of_fame.json`, `backend/world_settings.json`
- `.env`

---

## Limitações Conhecidas

| Limitação | Status |
|-----------|--------|
| Single worker (não escala horizontalmente) | Ativo — T17 no backlog |
| `gc/` (Gemini CLI) sujeito a rate limit de conta | Monitorado |
| Posição do benchmark HUD pode sair do viewport em mobile | Backlog |
