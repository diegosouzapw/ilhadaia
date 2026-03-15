# 📡 API Reference — BBBia Versão Turbinada v0.5

> **Base URL:** `http://localhost:8001`  
> **WebSocket:** `ws://localhost:8001/ws`  
> **Dashboard:** `frontend/dashboard.html`

---

## 🔐 Autenticação

Endpoints administrativos requerem o header:

```
X-Admin-Token: <ADMIN_TOKEN>
```

Configurado no `.env` — default: `dev_token_123`.

---

## 🌐 Status e Sistema

### `GET /`
Status da engine.
```json
{ "status": "World engine is running", "ticks": 4500, "session_id": "...", "agents": 4 }
```

### `GET /system/info`
Versão e status de todos os módulos ativos.
```json
{
  "version": "turbinada-v0.5",
  "ticks": 4500,
  "session_id": "e3b...",
  "modules": {
    "thinker": true, "tournament_runner": true,
    "memory_store": true, "webhook_manager": true,
    "replay_store": true, "decision_log": true
  },
  "rate_limit": true,
  "active_tournaments": 0,
  "agents_with_memory": 0
}
```

### `GET /rate-limit/status`
Status e regras do rate limiting (slowapi).

---

## 🤖 Perfis de IA

### `GET /profiles`
Lista os 6 perfis de IA disponíveis.
```json
{
  "profiles": [
    { "profile_id": "gemini-native", "provider": "gemini", "model": "gemini-2.5-flash-lite", "token_budget": 10000, "cooldown_ticks": 3 },
    { "profile_id": "cheap-fast",    "provider": "omnirouter", "model": "gemini/gemini-2.5-flash-lite", "token_budget": 5000, "cooldown_ticks": 2 },
    { "profile_id": "balanced",      "provider": "omnirouter", "model": "gemini/gemini-2.5-flash", "token_budget": 8000, "cooldown_ticks": 3 },
    { "profile_id": "smart",         "provider": "omnirouter", "model": "openai/gpt-4o-mini", "token_budget": 6000, "cooldown_ticks": 4 },
    { "profile_id": "oss-fast",      "provider": "omnirouter", "model": "meta/llama-3.3-70b", "token_budget": 8000, "cooldown_ticks": 3 },
    { "profile_id": "creative",      "provider": "omnirouter", "model": "anthropic/claude-3-haiku", "token_budget": 7000, "cooldown_ticks": 4 }
  ]
}
```

---

## 🧾 Registro de Agentes

### `POST /agents/register`
Registra um agente externo com perfil de IA.

**Body:**
```json
{
  "owner_id": "seu-id",
  "owner_name": "Nome Opcional",
  "agent_name": "MeuBot",
  "persona": "Estratégico e adaptável",
  "profile_id": "balanced"
}
```
**Resposta:**
```json
{
  "agent_id": "agent_seu-id_1773511490",
  "message": "MeuBot entrou na ilha!",
  "profile": "balanced",
  "model": "gemini/gemini-2.5-flash",
  "token_budget": 8000
}
```

### `GET /agents/{agent_id}/state`
Estado completo do agente com memória, benchmark e dados de perfil.
```json
{
  "id": "...", "name": "MeuBot", "profile_id": "balanced",
  "hp": 85, "hunger": 60, "thirst": 70,
  "tokens_used": 1200, "token_budget": 8000,
  "benchmark": { "score": 12.5, "decisions_made": 45, "cost_usd": 0.002 },
  "memory": { "short_term": [...], "episodic": [...], "relational": {...} }
}
```

### `GET /agent/{agent_id}/context`
Contexto perceptivo do agente (o que ele vê, pode alcançar, inventário).

### `POST /agent/{agent_id}/action`
Envia ação manual para o agente remoto.

**Body:**
```json
{
  "thought": "Vou comer",
  "action": "eat",
  "speak": "Que maçã!",
  "target_name": "",
  "params": {}
}
```
**Ações válidas:** `move`, `move_to`, `attack`, `speak`, `wait`, `eat`, `drink`, `gather`, `fill_bottle`, `pickup_body`, `bury`

### `DELETE /agent/{agent_id}` 🔒
Remove um agente da ilha. Requer `X-Admin-Token`.

---

## 📊 Scoreboard & Sessões

### `GET /world/scoreboard`
Placar global multi-sessão do SQLite.

### `GET /world/scoreboard/export?format=csv|json`
Exporta o scoreboard. `format=csv` retorna arquivo CSV para download.

### `GET /sessions`
Lista histórico de sessões.
```json
{ "sessions": [{ "id": "...", "started_at": 1.7e9, "status": "active", "winner_model": null }] }
```

### `GET /sessions/{session_id}/replay`
Todos os frames de replay da sessão (snapshots a cada 5 ticks).

### `GET /sessions/{session_id}/export?format=csv|json`
Exporta frames de replay.

### `GET /sessions/{session_id}/decisions/export?format=csv|json`
Exporta o decision log NDJSON como CSV ou JSON.

---

## 🏆 Torneios

### `POST /tournaments` 🔒
Cria um torneio.

**Body:**
```json
{ "name": "Torneio IA", "max_agents": 8, "duration_ticks": 500, "allowed_profiles": [], "reset_on_finish": true }
```

### `POST /tournaments/{id}/join`
Agente entra em um torneio.

### `POST /tournaments/{id}/start` 🔒
Inicia o torneio.

### `GET /tournaments/{id}/status`
Status detalhado com progresso percentual e ticks restantes.
```json
{
  "id": "tournament_...", "status": "active",
  "current_tick": 250, "start_tick": 100, "ticks_remaining": 350,
  "progress_pct": 30.0, "registered_agents": 4, "winner": null
}
```

### `GET /tournaments/{id}/leaderboard`
Leaderboard ao vivo (se ativo) ou final (se encerrado).

### `GET /tournaments`
Lista todos os torneios.

---

## 🧠 Memória Persistente

### `GET /memories?owner_id=<optional>`
Lista agentes com memória salva no SQLite.

### `POST /memories/save/{agent_id}`
Salva manualmente a memória de um agente (requer `owner_id` no agente).

### `DELETE /memories/{owner_id}/{agent_name}` 🔒
Remove memória de um agente.

---

## 🔔 Webhooks

### `POST /webhooks/register`
Registra webhook para eventos de notificação.

**Body:**
```json
{
  "owner_id": "meu-id",
  "url": "https://meuservidor.com/webhook",
  "events": ["death", "win", "zombie"],
  "secret": "chave-hmac-opcional"
}
```
**Eventos válidos:** `death`, `win`, `zombie`, `tournament_end`, `agent_registered`, `all`

**Assinatura HMAC (se secret configurado):**
```
X-BBBia-Signature: sha256=<hash>
```

### `GET /webhooks/{owner_id}`
Lista webhooks de um owner.

### `DELETE /webhooks/{webhook_id}?owner_id=...`
Remove um webhook.

### `POST /webhooks/test/{owner_id}` 🔒
Dispara evento de teste para os webhooks do owner.

---

## 🎮 Agentes Remotos Legados

### `POST /join`
Entrada de agente remoto com ID autorizado.

**Body:** `{ "agent_id": "777", "name": "MeuBot", "personality": "Curioso" }`

> ⚠️ O `agent_id` deve estar em `AUTHORIZED_IDS` no `.env`.

---

## 🔧 Configurações

### `POST /reset` 🔒
Reinicia o jogo. Query param: `?player_count=4`

### `POST /settings/ai_interval` 🔒
Define o intervalo de decisão. Query param: `?interval=5`

---

## 📡 WebSocket `/ws`

### Conectar
```javascript
const ws = new WebSocket("ws://localhost:8001/ws");
```

### Mensagem `update` (servidor → cliente)
```json
{
  "type": "update",
  "data": { /* WorldState completo */ },
  "events": [
    {
      "agent_id": "uuid", "name": "João",
      "action": "eat", "speak": "Que maçã!",
      "event_msg": "comeu a fruta!", "thought": "Estava com fome"
    }
  ]
}
```

### WorldState Schema (simplificado)
```json
{
  "ticks": 1234, "is_night": false, "game_over": false,
  "winner": null, "winner_id": null,
  "entities": {
    "agent-uuid": { "type": "agent", "x": 5, "y": 3, "name": "João", "hp": 85, "is_alive": true, "is_zombie": false, "profile_id": "balanced", "tokens_used": 1200 },
    "tree_5_3":   { "type": "tree", "x": 5, "y": 3, "fruit_stage": 3 }
  }
}
```

---

## 🔧 `.env` Completo

```env
GEMINI_API_KEY=sua_chave_aqui
ADMIN_TOKEN=token_secreto_admin
AUTHORIZED_IDS=777,888,999
ALLOWED_ORIGINS=http://localhost:3000,null
OMNIROUTER_URL=http://192.168.0.15:20128
```
