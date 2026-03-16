# Development Guide — BBBia v0.6

---

## Setup Local

### Pré-requisitos
- Python 3.12+
- OmniRoute rodando (ou qualquer endpoint OpenAI-compatible)

### Instalação

```bash
git clone https://github.com/inteligenciamilgrau/ilhadaia.git
cd ilhadaia/backend
pip install -r requirements.txt
cp ../.env.example .env
# Edite .env com seus valores
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

O backend cria automaticamente `data/`, `logs/` e o banco SQLite ao subir.

### Variáveis de Ambiente

```env
# Obrigatória (qualquer string)
ADMIN_TOKEN=troque-este-token

# OmniRoute — endpoint OpenAI-compatible
OMNIROUTER_URL=http://192.168.0.15:20128/v1
OMNIROUTER_API_KEY=omniroute-local

# CORS (deixe * para dev local)
ALLOWED_ORIGINS=*

# Gemini nativo — só se usar perfil gemini-native
GEMINI_API_KEY=sua_chave_gemini_aqui
```

**Aliases aceitos:** `OMNIROUTE_URL`, `OPENAI_BASE_URL` → todos resolvem para `OMNIROUTER_URL`.

---

## Fluxo de IA — Como Funciona

Cada agente tem um `profile_id` que aponta para um perfil em `runtime/profiles.py`.
O `Thinker` usa o perfil do agente para montar a chamada ao OmniRoute:

```python
profile = get_profile(agent.profile_id)
adapter = OpenAICompatibleAdapter(
    base_url=profile.base_url,  # OMNIROUTER_URL
    api_key=profile.api_key,
    model=profile.model,        # ex: "kr/claude-sonnet-4.5"
    max_tokens=profile.max_tokens,
)
```

O OmniRoute roteia pelo prefixo do modelo:
- `kr/` → Kiro (Claude) · `if/` → iFlow (Kimi, Qwen) · `gc/` → Gemini CLI · `groq/` → Groq

---

## Adicionando um Novo Perfil

Edite `backend/runtime/profiles.py` e adicione uma entrada em `BUILTIN_PROFILES`:

```python
"meu-perfil": AgentProfile(
    profile_id="meu-perfil",
    provider="omnirouter",
    model="groq/meta-llama/llama-4-scout",
    base_url=OMNIROUTER_URL,
    api_key=OMNIROUTER_API_KEY,
    max_tokens=300,
    token_budget=10_000,
    cooldown_ticks=3,
    temperature=0.7,
),
```

Reinicie o backend. O perfil aparece automaticamente em `/profiles`, na `models.html` e no formulário de registro.

---

## NPCs Default da Ilha

Definidos em `world.py` → `reset_agents()`:

```python
_default_profiles = ["claude-kiro", "kimi-thinking", "kimi-groq", "claude-haiku"]
# João → claude-kiro  | Maria → kimi-thinking
# Zeca → kimi-groq    | Elly  → claude-haiku
```

Para mudar os perfis default, edite essa lista.

---

## Registrando um Agente Externo

```bash
curl -X POST http://localhost:8001/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "owner_id": "meu-id",
    "agent_name": "MeuBot",
    "persona": "Estratégico e adaptável",
    "profile_id": "claude-kiro"
  }'
```

---

## Rodando Testes

```bash
cd backend
pytest tests/ -v
# 33 casos — engine, memória, benchmark, adapters
```

---

## Frontend

O backend serve o frontend via `StaticFiles`:
```
GET /frontend/index.html     → Ilha ao vivo
GET /frontend/dashboard.html → Dashboard analítico
GET /frontend/models.html    → Gerenciador de modelos
```

**Não** abra os `.html` diretamente por `file://` — o WebSocket não conecta.

### Adicionando uma Nova Interface

1. Crie o `.html` em `frontend/`
2. Adicione link de navegação no `<nav>` de cada página existente
3. O backend serve automaticamente via `StaticFiles`

---

## Resetar Estado Local

```bash
find backend/data -type f -delete
find backend/logs -type f -delete
find backend -maxdepth 1 \( -name 'hall_of_fame.json' -o -name 'world_settings.json' \) -delete
```

Na próxima subida, tudo é recriado automaticamente.

---

## Deploy com Docker

```bash
docker-compose up
```

Sobe backend + nginx. O nginx serve o frontend estático em `/frontend/`.

---

## Arquivos que NÃO devem ser commitados

O `.gitignore` exclui automaticamente:
- `*.db`, `*.db-shm`, `*.db-wal` — banco SQLite gerado em runtime
- `backend/logs/`, `logs/` — decision logs de sessão
- `backend/data/replays/`, `data/replays/` — snapshots de replay
- `backend/hall_of_fame.json`, `backend/world_settings.json` — estado runtime
- `.env` — credenciais locais
