# BBBia: A Ilha da IA

BBBia e um simulador de sobrevivencia social com benchmark de modelos de IA. O backend FastAPI executa o mundo, expõe REST + WebSocket e serve tres interfaces web:

- `frontend/index.html`: observer 3D da ilha em tempo real
- `frontend/dashboard.html`: dashboard analitico de sessoes, score e exportacoes
- `frontend/models.html`: console para testar perfis, cadastrar agentes e inspecionar o runtime

## O que esta branch consolida

- frontend servido pelo proprio backend em `/frontend/*`
- catalogo de perfis migrado para um setup free-first via OmniRoute
- nova tela `models.html` para testes de modelos e registro de agentes
- HUD de benchmark arrastavel e recolhivel na ilha
- menu auxiliar na ilha para consultar catalogo dinamico de modelos e salvar preset de provider/modelo
- artefatos de runtime removidos do git: banco SQLite, WAL, replays, logs e JSONs de estado

## Stack atual

- Backend: FastAPI + asyncio + WebSocket
- Runtime de IA: `runtime/thinker.py` + adapters Gemini/OpenAI-compatible
- Persistencia: SQLite + NDJSON de decisoes e replay
- Frontend: paginas estaticas em HTML/CSS/JS servidas por `StaticFiles`
- Ambiente recomendado: Python 3.12+

Importante: a fonte de verdade do runtime continua sendo o sistema de `profiles`. O menu de settings herdado da `main` foi mantido como camada auxiliar para:

- listar modelos dinamicamente por provider
- salvar um preset/catalogo default da UI
- inspecionar URL do provider OpenAI-compatible

Ele nao substitui `profile_id`, nem o fluxo de decisao baseado em `runtime/thinker.py`.

## Setup rapido

```bash
# 1. clone
 git clone https://github.com/inteligenciamilgrau/ilhadaia.git
 cd ilhadaia

# 2. instale as dependencias do backend
 cd backend
 pip install -r requirements.txt

# 3. configure o ambiente local
 cp ../.env.example .env
 # edite os valores necessarios

# 4. suba o backend
 uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

O comando acima deve ser executado a partir de `backend/`. Com isso, os paths relativos de `data/` e `logs/` ficam dentro de `backend/`, como esperado pelo projeto.

## Configuracao default gratuita

O setup padrao adotado nesta branch usa `claude-kiro` como perfil default gratuito.

```env
ADMIN_TOKEN=troque-este-token
OMNIROUTER_URL=http://192.168.0.15:20128/v1
OMNIROUTER_API_KEY=omniroute-local
ALLOWED_ORIGINS=*

# Exemplo opcional de credencial externa. Nao faz parte do fluxo default.
GEMINI_API_KEY=sua_chave_gemini_aqui
```

Observacoes importantes:

- `POST /agents/register` agora usa `claude-kiro` como default quando `profile_id` nao e enviado.
- `get_profile()` tambem faz fallback para `claude-kiro`.
- Os quatro NPCs iniciais da ilha usam esta rotacao gratuita: `claude-kiro`, `kimi-thinking`, `kimi-groq`, `claude-haiku`.
- por compatibilidade com a `main`, o backend tambem aceita `OMNIROUTE_API_KEY` como alias legado de `OMNIROUTER_API_KEY`.
- por compatibilidade com outros endpoints OpenAI-compatible, o backend tambem aceita `OPENAI_BASE_URL` e `OPENAI_API_KEY` como aliases opcionais.

## Interfaces web

Com o backend rodando:

| Interface | URL |
| --- | --- |
| Ilha ao vivo | `http://localhost:8001/frontend/index.html` |
| Dashboard | `http://localhost:8001/frontend/dashboard.html` |
| Modelos | `http://localhost:8001/frontend/models.html` |

Nao abra os arquivos `.html` por `file://`. O fluxo correto desta branch e servir tudo via `/frontend/` para manter WebSocket e fetches no mesmo host.

## Perfis disponiveis

Hoje o projeto tem 7 perfis builtin.

| Perfil | Provider | Modelo | Uso principal |
| --- | --- | --- | --- |
| `claude-kiro` | OmniRoute | `kr/claude-sonnet-4.5` | default gratuito e mais equilibrado |
| `claude-haiku` | OmniRoute | `kr/claude-haiku-4.5` | rapido e barato |
| `kimi-thinking` | OmniRoute | `if/kimi-k2` | respostas mais longas / reasoning |
| `qwen-coder` | OmniRoute | `if/qwen3-coder-plus` | tarefas de codigo |
| `kimi-groq` | OmniRoute | `groq/moonshotai/kimi-k2-instruct` | alternativa via Groq |
| `gemini-flash` | OmniRoute | `gc/gemini-2.5-flash` | Gemini via gateway |
| `llama-groq` | OmniRoute | `groq/llama-3.3-70b-versatile` | inferencia rapida |

A tela `models.html` consome `GET /profiles` e sincroniza automaticamente a lista de perfis com o backend, inclusive no formulario de registro.

Na `index.html`, o botao de engrenagem agora consome:

- `GET /settings/ai`
- `POST /settings/ai`
- `GET /models`

Esses endpoints existem como apoio de catalogo/default da UI. O runtime ativo da ilha continua vindo dos perfis atribuidos a cada agente.

## Resetar estado local

Os artefatos de runtime nao sao mais versionados. Para voltar o projeto a um estado limpo de execucao:

```bash
find backend/data -type f -delete
find backend/logs -type f -delete
find backend -maxdepth 1 \( -name 'hall_of_fame.json' -o -name 'world_settings.json' \) -delete
```

Na proxima subida do backend, `data/`, `logs/`, o banco SQLite e os snapshots serao recriados automaticamente.

## Estrutura resumida

```text
ilhadaia/
├── README.md
├── .env.example
├── docs/
├── frontend/
│   ├── index.html
│   ├── dashboard.html
│   ├── models.html
│   ├── benchmark.js
│   ├── main.js
│   └── style.css
└── backend/
    ├── main.py
    ├── agent.py
    ├── world.py
    ├── runtime/
    ├── storage/
    └── tests/
```

## Documentacao tecnica

- `docs/ARCHITECTURE.md`: arquitetura atual e responsabilidades dos modulos
- `docs/API_REFERENCE.md`: endpoints e exemplos de uso
- `docs/DEVELOPMENT_GUIDE.md`: setup local, testes e extensoes
- `docs/GAME_STATE.md`: detalhes de simulacao, score e world state
- `docs/IMPROVEMENT_PLAN.md`: historico de implementacao e ajustes da branch
- `docs/BACKLOG.md`: pendencias tecnicas reais
- `docs/CURRENT_STATE_AUDIT.md`: fotografia atual do projeto apos validacao
- `docs/TARGET_ARCHITECTURE.md`: direcao de modularizacao futura

## Validacao local desta atualizacao

- `pytest backend/tests/test_engine.py -q`
- resultado: `33 passed`

## Licenca

Projeto de estudo e experimentacao de agentes de IA.
