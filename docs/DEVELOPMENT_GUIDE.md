# 🛠️ Guia de Desenvolvimento — BBBia Versão Turbinada v0.5

---

## Setup Local

```bash
# 1. Clone e entre no backend
cd ilhadaia/backend

# 2. Instalar dependências (Python 3.12+)
pip install -r requirements.txt

# 3. Configurar .env
cp ../.env.example .env
# Edite: GEMINI_API_KEY, ADMIN_TOKEN, OMNIROUTER_URL

# 4. Iniciar backend
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 5. Abrir frontend
# Navegue para frontend/index.html no browser (file:// ou http server)
# Navegue para frontend/dashboard.html para o dashboard analítico
```

---

## Variáveis de Ambiente (`.env`)

```env
# Obrigatórias
GEMINI_API_KEY=sua_chave_aqui

# Segurança
ADMIN_TOKEN=dev_token_123          # Token para endpoints admin
AUTHORIZED_IDS=777,888,999         # IDs autorizados para /join

# OmniRouter (provider OpenAI-compat)
OMNIROUTER_URL=http://192.168.0.15:20128

# CORS (inclua "null" para file://)
ALLOWED_ORIGINS=http://localhost:3000,null
```

---

## Via Docker

```bash
docker-compose up --build
# Backend em http://localhost:8001
# Frontend servido pelo nginx em http://localhost:80
```

---

## Estrutura de Módulos

### `runtime/` — Motor de IA
Todos os novos providers e adaptadores vão aqui:

```python
# Novo adapter em runtime/adapters/meu_provider.py
from runtime.adapters.base import AIAdapter, AIResponse

class MeuAdapter(AIAdapter):
    async def complete(self, messages: list[dict], max_tokens: int) -> AIResponse:
        # Sua lógica aqui
        return AIResponse(text="...", tokens_in=0, tokens_out=0, latency_ms=0)
```

Após criar o adapter, registre no `runtime/profiles.py`:

```python
BUILTIN_PROFILES["meu-perfil"] = AgentProfile(
    profile_id="meu-perfil",
    provider="meu-provider",
    model="meu-modelo",
    token_budget=5000,
    cooldown_ticks=3,
    max_tokens=512,
)
```

### `storage/` — Persistência
Todos os módulos de storage seguem a mesma interface:

```python
class MeuStorage:
    def __init__(self, db_path: str = "data/ilhadaia.db"): ...
    def close(self) -> None: self.conn.close()
```

Registre a nova instância no `lifespan` do `main.py`.

---

## Adicionando um Endpoint

```python
# Em main.py, adicione após os endpoints existentes

class MeuRequest(BaseModel):
    meu_campo: str

@app.get("/meu-endpoint")
async def meu_endpoint(request: Request):
    # Se quiser rate limit: @limiter.limit("10/minute") antes do @app.get
    return {"resultado": "exemplo"}

@app.post("/meu-endpoint", dependencies=[Depends(verify_admin_token)])
async def criar_algo(req: MeuRequest):
    return {"criado": req.meu_campo}
```

---

## Rodando os Testes

```bash
cd backend
pytest tests/ -v
# Expected: 31 passed in < 1s
```

Para adicionar testes novos, edite `backend/tests/test_engine.py`.

---

## Ciclo de Contribuição

1. Crie a tasks em `docs/tasks/TXX-nome.md` (ver arquivos existentes como modelo)
2. Implemente o módulo em `backend/runtime/` ou `backend/storage/`
3. Integre no `main.py` (imports + lifespan + endpoints)
4. Adicione testes em `backend/tests/test_engine.py`
5. Atualize `docs/IMPROVEMENT_PLAN.md` e `docs/API_REFERENCE.md`

---

## Observações de Arquitetura

- **Estado global:** `world`, `TOURNAMENTS`, `_current_session_id` são globais em `main.py`. Mudanças devem ser thread-safe (asyncio.Lock se necessário)
- **SQLite WAL:** Todos os módulos de storage conectam ao mesmo arquivo `data/ilhadaia.db` com WAL mode — suporta múltiplos readers + 1 writer simultâneos
- **CORS file://** O header `null` no CORS é necessário para o frontend funcionar diretamente via `file://` em desenvolvimento. Em produção, filtrar por origin real
- **WebSocket single-worker:** O `ConnectionManager` atual só funciona com 1 worker uvicorn. Para múltiplos workers, implementar T17 (Redis pub/sub)
- **Rate limiting:** O decorator `@limiter.limit("...")` usa a variável `request: Request` — sempre inclua como parâmetro do endpoint
