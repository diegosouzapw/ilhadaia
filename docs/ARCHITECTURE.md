# Arquitetura Atual

Estado documentado desta branch:

- backend monolitico em `backend/main.py`
- frontend estatico servido pelo proprio FastAPI em `/frontend/*`
- runtime de IA centralizado em `runtime/thinker.py`
- persistencia local em SQLite + NDJSON
- operacao single-process / single-worker

## Visao geral

```text
Browser
  |\
  | +--> /frontend/index.html
  | +--> /frontend/dashboard.html
  | +--> /frontend/models.html
  |
  +----> REST + WebSocket (/ws)
            |
            v
        FastAPI app
            |
            +--> World (simulacao)
            +--> Thinker (orquestracao de IA)
            +--> TournamentRunner
            +--> SessionStore / MemoryStore / ReplayStore / DecisionLog / WebhookManager
            |
            v
      Gemini API ou providers OpenAI-compatible via OmniRoute
```

## Componentes principais

### `backend/main.py`

Responsabilidades:

- inicializar a aplicacao FastAPI
- montar `StaticFiles` em `/frontend`
- criar e encerrar sessao ativa via lifespan
- expor endpoints REST e WebSocket
- rodar o `world_loop()` e disparar snapshots, score e webhooks

Estado global mantido aqui:

- `world`
- `_current_session_id`
- `TOURNAMENTS`
- instancias de `DecisionLog`, `SessionStore`, `ReplayStore`, `MemoryStore`, `WebhookManager`

### `backend/world.py`

Responsabilidades:

- manter o `WorldState`
- executar `tick()`
- controlar ciclo dia/noite, morte, zumbis e respawn
- resetar o elenco inicial
- serializar o estado enviado ao frontend e ao replay

Detalhe importante desta branch:

- os NPCs iniciais sao resetados com perfis gratuitos: `claude-kiro`, `kimi-thinking`, `kimi-groq`, `claude-haiku`

### `backend/runtime/thinker.py`

Responsabilidades:

- resolver o perfil do agente
- instanciar o adapter correto
- montar contexto + memoria relevante
- validar structured output via `ActionDecision`
- registrar decisao em `DecisionLog`

Fallback atual:

- perfil default e fallback tecnico: `claude-kiro`

### `backend/runtime/profiles.py`

Catalogo builtin de 8 perfis.

Dois grupos existem hoje:

- `provider="omnirouter"`: todos usam o mesmo `OMNIROUTER_URL`, mudando apenas `model`
- `provider="gemini"`: usa `GEMINI_API_KEY` diretamente (`gemini-native`)

### `backend/storage/*`

- `session_store.py`: sessoes e scoreboard historico em SQLite
- `memory_store.py`: memoria persistente para agentes com `owner_id`
- `replay_store.py`: snapshots NDJSON por sessao
- `decision_log.py`: NDJSON de decisoes por sessao
- `webhook_manager.py`: cadastro e disparo de webhooks

## Frontend

### `frontend/index.html`

- observer da ilha
- usa WebSocket para estado ao vivo
- HUD de benchmark agora pode ser arrastado e recolhido
- ganhou navegacao global para `dashboard.html` e `models.html`

### `frontend/dashboard.html`

- analise de sessoes
- consultas de scoreboard e exportacoes
- navegacao consistente com as demais paginas

### `frontend/models.html`

- lista perfis retornados por `/profiles`
- testa modelos individualmente
- registra novos agentes via `POST /agents/register`
- exibe agentes ativos com dados de benchmark

## Fluxo de uma sessao

```text
startup
  -> criar SessionStore/DecisionLog/ReplayStore
  -> create_session()
  -> world.reset_agents()
  -> iniciar world_loop()

world_loop()
  -> world.tick()
  -> upsert scores periodicamente
  -> maybe_snapshot()
  -> broadcast websocket
  -> disparar webhooks assincronos
```

## Artefatos de runtime

Com o comando recomendado (`cd backend && uvicorn main:app ...`), o runtime gera:

- `backend/data/ilhadaia.db`
- `backend/data/replays/*.replay.ndjson`
- `backend/logs/*.ndjson`
- `backend/hall_of_fame.json`
- `backend/world_settings.json`

Esses arquivos nao fazem mais parte do versionamento.

## Limitacoes conhecidas

- `ConnectionManager` em memoria: continua single-worker
- `main.py` segue concentrando muita responsabilidade
- paths de storage dependem do backend ser iniciado a partir de `backend/`
- `webhook_manager` e `session_store` compartilham o mesmo SQLite local

## Direcao recomendada

A proxima modularizacao continua sendo:

- separar API de simulacao
- tirar estado global de `main.py`
- preparar um manager de broadcast desacoplado do processo local

Esses passos estao detalhados em `docs/TARGET_ARCHITECTURE.md`.
