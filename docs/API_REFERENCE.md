# API Reference — BBBia v0.6

> Base URL: `http://localhost:8001`
> Admin endpoints requerem header `X-Admin-Token: <ADMIN_TOKEN>`

---

## Status

### `GET /`
Retorna status do servidor e ticks atuais.

```json
{ "status": "World engine is running", "ticks": 42, "session_id": "abc...", "agents": 4 }
```

### `GET /system/info`
Informações detalhadas do sistema (versão, módulos, status).

---

## Perfis de IA

### `GET /profiles`
Lista todos os 7 perfis builtin.

```json
{
  "profiles": [
    {
      "profile_id": "claude-kiro",
      "provider": "omnirouter",
      "model": "kr/claude-sonnet-4.5",
      "cooldown_ticks": 4,
      "token_budget": 15000,
      "max_tokens": 400
    }
  ]
}
```

**Perfis disponíveis:** `claude-kiro`, `claude-haiku`, `kimi-thinking`, `qwen-coder`, `kimi-groq`, `gemini-flash`, `llama-groq`

---

## Configuração de IA (preset de catálogo da UI)

> Estes endpoints salvam apenas o preset auxiliar da UI. O runtime de decisão dos agentes usa sempre o `profile_id` atribuído a cada agente.

### `GET /settings/ai`
Retorna o preset salvo de provider/modelo/URL.

```json
{
  "scope": "catalog_default",
  "note": "Perfis por agente são a fonte de verdade.",
  "ai_provider": "omnirouter",
  "ai_model": "kr/claude-sonnet-4.5",
  "omniroute_url": "http://192.168.0.15:20128/v1"
}
```

### `POST /settings/ai` *(admin)*
Salva preset de catálogo.

```json
{
  "ai_provider": "omnirouter",
  "ai_model": "kr/claude-sonnet-4.5",
  "omniroute_url": "http://192.168.0.15:20128/v1"
}
```

### `GET /models?provider=omnirouter&url=<base_url>`
Lista modelos dinamicamente do endpoint OmniRoute (ou qualquer endpoint OpenAI-compatible).
Retorna perfis builtin + modelos curados + modelos dinâmicos do endpoint.

```json
{
  "scope": "catalog",
  "provider": "omnirouter",
  "base_url": "http://192.168.0.15:20128/v1",
  "models": [
    { "id": "kr/claude-sonnet-4.5", "name": "claude-kiro (kr/claude-sonnet-4.5)", "source": "builtin_profile" }
  ]
}
```

---

## Agentes

### `POST /agents/register`
Registra um agente customizado na ilha. Rate limit: 10/min.

```json
{
  "owner_id": "meu-id",
  "owner_name": "Meu Nome",
  "agent_name": "MeuBot",
  "persona": "Estratégico e adaptável",
  "profile_id": "claude-kiro"
}
```

Resposta:
```json
{
  "agent_id": "agent_meu-id_1710000000",
  "message": "MeuBot entrou na ilha!",
  "profile": "claude-kiro",
  "model": "kr/claude-sonnet-4.5",
  "token_budget": 15000
}
```

### `GET /agents/{agent_id}/state`
Estado atual + benchmark + memória recente do agente.

### `DELETE /agent/{agent_id}` *(admin)*
Remove agente da ilha.

---

## Sessões, Scoreboard e Replay

### `GET /sessions?limit=20`
Histórico de sessões do SQLite.

### `GET /sessions/{session_id}/replay`
Todos os frames de replay de uma sessão (snapshots a cada 5 ticks).

### `GET /sessions/{session_id}/replay/frame/{tick}`
Frame específico de replay.

### `GET /sessions/{session_id}/export?format=json|csv`
Exporta frames de replay.

### `GET /sessions/{session_id}/decisions/export?format=json|csv`
Exporta decision log NDJSON.

### `GET /world/scoreboard?limit=50`
Scoreboard global multi-sessão.

### `GET /world/scoreboard/export?format=json|csv`
Exporta scoreboard.

---

## Controle de Jogo

### `POST /reset` *(admin)*
Reset completo após salvar memórias persistentes da sessão atual.
Query: `?player_count=4`

### `POST /settings/ai_interval` *(admin)*
Altera intervalo de ticks entre decisões de IA.
Query: `?interval=5`

---

## Torneios

### `POST /tournaments` *(admin)*  Rate limit: 5/min
Cria um torneio.

```json
{
  "name": "Torneio Alpha",
  "max_agents": 8,
  "duration_ticks": 500,
  "allowed_profiles": ["claude-kiro", "llama-groq"],
  "reset_on_finish": true
}
```

### `POST /tournaments/{id}/join`
Registra agente em torneio (mesma estrutura de `/agents/register`).

### `POST /tournaments/{id}/start` *(admin)*
Inicia o torneio.

### `GET /tournaments`
Lista todos os torneios.

### `GET /tournaments/{id}/status`
Status detalhado com progresso.

### `GET /tournaments/{id}/leaderboard`
Leaderboard ao vivo ou final.

---

## Webhooks

### `POST /webhooks/register`  Rate limit: 20/hora
Registra um webhook para eventos críticos.

```json
{
  "url": "https://meu-servidor.com/webhook",
  "events": ["death", "zombie", "tournament_end", "agent_registered"],
  "secret": "minha-chave-hmac"
}
```

### `GET /webhooks/{owner_id}`  (admin)
Lista webhooks registrados para um `owner_id` específico.

### `DELETE /webhooks/{webhook_id}`  (admin)
Remove um webhook registrado. Requer o `owner_id` na query:
`DELETE /webhooks/{webhook_id}?owner_id=<OWNER_ID>`.

### `POST /webhooks/test/{owner_id}`  (admin)
Dispara um evento de teste para os webhooks associados ao `owner_id` informado.

---

## Sistema

### `GET /rate-limit/status`
Status do rate limiting (slowapi).

### `GET /memories`
Lista agentes com memória persistente.

---

## Remote Agent API (legada)

### `POST /join`
Agente remoto entra na ilha (requer `agent_id` em `AUTHORIZED_IDS`).

### `GET /agent/{agent_id}/context`
Contexto do mundo para o agente remoto.

### `POST /agent/{agent_id}/action`
Submete ação manual para o agente remoto.

---

## WebSocket

### `ws://localhost:8001/ws`

Mensagens recebidas:

| type | Descrição |
|------|-----------|
| `init` | Estado completo ao conectar |
| `update` | Estado + eventos a cada tick |
| `reset` | Estado após reset |

Payload `data` inclui: `agents`, `tiles`, `ticks`, `is_night`, `ai_provider`, `ai_model`, `omniroute_url`, `day_cycle`, `player_count`.
