# Guia de Desenvolvimento

## Ambiente local

Fluxo recomendado:

```bash
cd ilhadaia/backend
pip install -r requirements.txt
cp ../.env.example .env
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

O `.env.example` canonico esta na raiz do repositorio.

## Variaveis de ambiente

### Obrigatorias para o setup free-first

```env
ADMIN_TOKEN=troque-este-token
OMNIROUTER_URL=http://192.168.0.15:20128/v1
OMNIROUTER_API_KEY=omniroute-local
ALLOWED_ORIGINS=*
```

### Opcional

```env
GEMINI_API_KEY=sua_chave_gemini_aqui
```

Mantenha `GEMINI_API_KEY` apenas como exemplo de credencial externa. O fluxo default desta branch usa somente `OMNIROUTER_URL` + `OMNIROUTER_API_KEY`.

## Como validar localmente

### Testes

```bash
pytest backend/tests/test_engine.py -q
```

Estado validado nesta atualizacao: `33 passed`.

### Smoke manual

1. subir o backend a partir de `backend/`
2. abrir `http://localhost:8001/frontend/index.html`
3. abrir `http://localhost:8001/frontend/models.html`
4. validar `GET /profiles` e cadastro de um agente

## Limpeza de runtime

Para resetar o estado local sem mexer no codigo:

```bash
find backend/data -type f -delete
find backend/logs -type f -delete
find backend -maxdepth 1 \( -name 'hall_of_fame.json' -o -name 'world_settings.json' \) -delete
```

O backend recria esses artefatos na proxima execucao.

## Adicionando ou alterando perfis

O catalogo vive em `backend/runtime/profiles.py`.

Checklist minimo:

1. adicionar ou editar a entrada em `BUILTIN_PROFILES`
2. manter `provider`, `model`, `token_budget`, `cooldown_ticks` e `max_tokens` coerentes
3. reiniciar o backend
4. validar `GET /profiles`
5. abrir `frontend/models.html` e confirmar que a lista e o formulario de registro refletiram o novo perfil
6. atualizar README e docs se o perfil alterar o setup recomendado

## Adicionando endpoints

Pontos de atencao em `backend/main.py`:

- endpoints admin devem usar `Depends(verify_admin_token)`
- rate limiting usa `Request` como parametro do handler quando o decorator `_rate_limit(...)` for aplicado
- se o endpoint mudar o mundo, pense no impacto em replay, websocket e scoreboard

## Persistencia

Persistencia atual:

- `SessionStore`: SQLite de sessoes e scoreboard
- `MemoryStore`: memoria persistente por owner
- `ReplayStore`: snapshots NDJSON
- `DecisionLog`: NDJSON de decisoes
- `WebhookManager`: webhooks e disparos

Todos sao instanciados no startup do FastAPI.

## Frontend

As paginas HTML sao servidas em `/frontend` por `StaticFiles`.

Nao trate `frontend/` como artefato isolado de `file://`; as paginas assumem backend HTTP no mesmo host.

## Consistencia entre backend e UI

Ao alterar perfis ou dados exibidos para agentes:

- confira `GET /profiles`
- confira `frontend/models.html`
- confira `frontend/index.html` / `frontend/benchmark.js`
- confira qualquer texto do README que mencione defaults ou setup gratuito
