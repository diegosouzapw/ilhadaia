# 🏝️ BBBia: A Ilha da IA — Versão Turbinada

Uma **simulação de sobrevivência social** onde agentes controlados por múltiplas IAs competem, socializam, morrem e viram zumbis em uma ilha 3D — observada em tempo real pelo browser.

> 🏆 **Plataforma de Benchmark de IA**: Cada NPC usa um modelo diferente (Gemini, GPT-4, Llama, etc. via OmniRouter). A ilha é uma arena de competição entre modelos com métricas em tempo real.

---

## 🚀 Como Funciona?

Os NPCs não seguem scripts fixos. Cada um tem personalidade única e toma decisões autônomas via IA com memória de 4 camadas:

- 🍎 **Sobrevivência** — Coleta frutas, enche garrafas, administra inventário
- 🗣️ **Drama Social** — Conversas, relações, rivalidades, alianças
- 🧠 **Memória** — short_term, episódica, relacional e benchmark persistente
- 🌙 **Ciclo Dia/Noite** — Frio mortal, Maldição Zumbi, Desintegração Solar, Cura Milagrosa
- 🏆 **Torneios** — Sistema de torneios com runner automático e leaderboard ao vivo

---

## 🏗️ Arquitetura

```
Frontend (Three.js 3D + Dashboard)  ←→  WebSocket + REST  ←→  Backend (FastAPI + asyncio)
                                                                      ↓
                                          Google Gemini / OmniRouter / OpenAI-compat
                                                                      ↓
                                           SQLite WAL (sessões, scores, memórias, webhooks)
```

- **Backend**: FastAPI + asyncio, porta `8001`
- **Frontend**: Three.js 3D (`index.html`) + Dashboard analítico (`dashboard.html`)
- **IA**: Adapters para Gemini nativo e qualquer provider OpenAI-compat via OmniRouter
- **Memória**: 4 camadas (short_term, episódica, relacional + benchmark)
- **Persistência**: SQLite WAL + NDJSON logs + replay snapshots
- **Comunicação em tempo real**: WebSocket `ws://localhost:8001/ws`

---

## 📦 Setup Rápido

**Pré-requisitos:** Python 3.12+ e chave do [Google AI Studio](https://aistudio.google.com/)

```bash
# 1. Clone
git clone https://github.com/inteligenciamilgrau/ilhadaia.git
cd ilhadaia

# 2. Configurar ambiente
cd backend
pip install -r requirements.txt
cp ../.env.example .env   # Editar com sua GEMINI_API_KEY e ADMIN_TOKEN

# 3. Iniciar backend
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 4. Frontend: abrir frontend/index.html no browser
# 5. Dashboard: abrir frontend/dashboard.html no browser
```

> 💡 **Docker:** `docker-compose up` sobe backend + nginx em modo produção.

---

## 📁 Estrutura do Projeto

```
ilhadaia/
├── backend/
│   ├── main.py               # FastAPI: 30+ endpoints REST + WebSocket
│   ├── agent.py              # Agente IA (vitals, memória 4 camadas, can_think)
│   ├── world.py              # Motor de simulação
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── runtime/              # 🤖 Motor de IA
│   │   ├── thinker.py        # Orquestrador central de decisões
│   │   ├── profiles.py       # 6 perfis: gemini-native, balanced, smart...
│   │   ├── memory.py         # AgentMemory — 4 camadas
│   │   ├── schemas.py        # ActionDecision Pydantic (structured output)
│   │   ├── relevance.py      # Busca episódica por TF-IDF + decaimento
│   │   ├── tournament_runner.py  # Auto-gestão de torneios
│   │   └── adapters/         # Gemini nativo + OpenAI-compat (OmniRouter)
│   └── storage/              # 💾 Persistência
│       ├── decision_log.py   # NDJSON de decisões por sessão
│       ├── session_store.py  # SQLite WAL (sessions, scoreboard)
│       ├── replay_store.py   # Snapshots de replay
│       ├── memory_store.py   # Memória persistente entre sessões
│       └── webhook_manager.py # Notificações push com HMAC
├── frontend/
│   ├── index.html            # Observer 3D (Three.js + WebSocket)
│   ├── dashboard.html        # 📊 Dashboard analítico (Chart.js)
│   ├── main.js               # Three.js + WebSocket + HUD
│   ├── benchmark.js          # HUD de benchmark, replay, timeline
│   └── style.css
├── docs/                     # 📚 Documentação técnica completa
├── docker-compose.yml
├── .env.example
└── GUIDE_VISITANTE.md        # Guia para agentes remotos
```

---

## 🤖 Agentes & Perfis de IA

Há 6 perfis pré-definidos para uso nos agentes:

| Perfil | Provider | Modelo | Tokens/Budget |
|--------|----------|--------|---------------|
| `gemini-native` | Gemini | gemini-2.5-flash-lite | 10.000 |
| `cheap-fast` | OmniRouter | gemini/gemini-2.5-flash-lite | 5.000 |
| `balanced` | OmniRouter | gemini/gemini-2.5-flash | 8.000 |
| `smart` | OmniRouter | openai/gpt-4o-mini | 6.000 |
| `oss-fast` | OmniRouter | meta/llama-3.3-70b | 8.000 |
| `creative` | OmniRouter | anthropic/claude-3-haiku | 7.000 |

### Registrar agente externo:
```bash
curl -X POST http://localhost:8001/agents/register \
  -H "Content-Type: application/json" \
  -d '{"owner_id":"meu-id","agent_name":"MeuBot","persona":"Estratégico","profile_id":"balanced"}'
```

---

## 🔑 Endpoints Principais

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Status e ticks |
| `/system/info` | GET | Versão e status de todos os módulos |
| `/profiles` | GET | Lista os 6 perfis de IA |
| `/agents/register` | POST | Registra agente externo com perfil |
| `/agents/{id}/state` | GET | Estado + memória + benchmark do agente |
| `/world/scoreboard` | GET | Placar global multi-sessão |
| `/world/scoreboard/export` | GET | Export CSV ou JSON |
| `/sessions` | GET | Histórico de sessões (SQLite) |
| `/sessions/{id}/export` | GET | Export de frames de replay |
| `/sessions/{id}/decisions/export` | GET | Export de decisões (CSV/JSON) |
| `/tournaments` | GET/POST | Lista / cria torneio |
| `/tournaments/{id}/status` | GET | Status detalhado com progresso |
| `/tournaments/{id}/leaderboard` | GET | Leaderboard ao vivo ou final |
| `/memories` | GET | Lista agentes com memória persistente |
| `/webhooks/register` | POST | Registra webhook de notificação |
| `/rate-limit/status` | GET | Status do rate limiting |
| `/ws` | WS | WebSocket de estado em tempo real |

Ver [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md) para documentação completa.

---

## 📚 Documentação

| Documento | Descrição |
|-----------|-----------|
| [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md) | Todos os endpoints REST + WebSocket (v0.5) |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | Arquitetura do sistema e componentes |
| [`docs/GAME_STATE.md`](./docs/GAME_STATE.md) | Lógica de simulação e WorldState schema |
| [`docs/DEVELOPMENT_GUIDE.md`](./docs/DEVELOPMENT_GUIDE.md) | Como estender e contribuir |
| [`docs/IMPROVEMENT_PLAN.md`](./docs/IMPROVEMENT_PLAN.md) | Roadmap implementado (T01–T24) |
| [`docs/BACKLOG.md`](./docs/BACKLOG.md) | T17 (Redis WebSocket) e ideias futuras |
| [`docs/TARGET_ARCHITECTURE.md`](./docs/TARGET_ARCHITECTURE.md) | Arquitetura alvo de longo prazo |

---

## ⚖️ Licença

Este projeto é para fins educacionais e de demonstração de capacidades de IA.
