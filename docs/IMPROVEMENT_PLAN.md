# 🚀 Plano de Melhorias — BBBia: A Ilha da IA (Versão Turbinada)

> **Documento:** Análise completa de viabilidade + roadmap de implementação  
> **Baseado em:** Conversa ChatGPT "Desenvolvimento de Mundo Roblox" (46 páginas)  
> **Data:** Março 2026  
> **Arquitetura alvo:** Manter Python/FastAPI/Three.js. **SEM migração para Roblox.**

---

## 📋 Resumo Executivo

O protótipo atual prova que a ideia funciona: agentes de IA com personalidade, simulação de sobrevivência, zumbis, ciclo dia/noite. A conversa do ChatGPT revelou um roadmap ambicioso. 

Após análise técnica completa do código atual e pesquisa de viabilidade, **15 das 16 ideias principais são implementáveis** na arquitetura atual sem mudança de tecnologia. Apenas a integração nativa com Roblox exige adaptação (mas o backend pode ser usado como endpoint para Roblox também).

---

## ✅ O que PODE ser feito (na arquitetura atual)

### 🔴 Alta Prioridade — Quick Wins

#### M01 — Adapter de IA Multi-Provider (OmniRouter)
**Status:** ✅ Viável | **Impacto:** 🔥🔥🔥 | **Esforço:** Médio

**Problema atual:** `agent.py` usa `google-genai` hardcoded. Impossível trocar de modelo.

**Solução:**
- Criar `backend/ai_adapter.py` com interface abstrata `AIAdapter`
- Implementar `GeminiAdapter`, `OmniRouterAdapter` (via HTTP)
- Cada agente recebe um `model_profile` (YAML/dict)
- Fallback automático por custo/erro

**Perfis por agente (como a conversa sugere):**
```yaml
profiles:
  cheap-fast:
    provider: openrouter
    model: qwen/qwen-2.5-coder
    max_tokens: 300
  social-drama:
    provider: omnirouter   # Seu OmniRoute!
    model: claude-sonnet
    max_tokens: 500
  survivor-balanced:
    provider: google
    model: gemini-flash
    max_tokens: 350
```

**Impacto:** Transforma a ilha em **benchmark de agentes** de verdade.

---

#### M02 — Budget de Tokens e Rate Limiting por Agente
**Status:** ✅ Viável | **Impacto:** 🔥🔥🔥 | **Esforço:** Baixo

**Problema atual:** Nenhum controle de custo. Um agente pode chamar a API a cada tick.

**Solução:**
- Adicionar `token_budget: int` e `tokens_used: int` ao Agent
- Limitar via configuração `max_tokens_per_tick`
- Cooldown mínimo configurável por agente
- Alertas quando budget > 80%
- Telemetria: latência, custo estimado, tokens por decisão

---

#### M03 — Logging Estruturado de Decisões (Decision Log)
**Status:** ✅ Viável | **Impacto:** 🔥🔥🔥 | **Esforço:** Baixo

**Problema atual:** Logs só no console/uvicorn. Sem análise pós-jogo.

**Solução:**
- Criar `backend/decision_log.py` que salva NDJSON line-by-line
- Logar por decisão: agent_id, tick, model, latency_ms, tokens, thought, action, result
- Endpoint `GET /logs/decisions?session_id=X` para download
- Base para replay e benchmark

**Formato:**
```json
{"tick": 450, "agent": "João", "model": "gemini-flash", "latency_ms": 342, "tokens": 287, "thought": "...", "action": "eat", "result": "success"}
```

---

#### M04 — Sistema de Replay (Gravação + Reprodução)
**Status:** ✅ Viável | **Impacto:** 🔥🔥🔥 | **Esforço:** Médio

**Problema atual:** Cada sessão se perde. Impossível rever o que aconteceu.

**Solução:**
- Salvar `world_state` snapshot a cada N ticks em arquivo NDJSON
- Novo endpoint `GET /sessions` lista sessões gravadas
- Novo endpoint `GET /sessions/{id}/replay` serve estado tick-a-tick
- Frontend: botão "Assistir gravação" carrega replay
- Sessão ativa: `session_id = timestamp_início`

**Impacto:** Permite compartilhar partidas, estudar comportamentos, criar "hall da fama" visual.

---

#### M05 — Scoreboard Detalhado por Modelo/Agente
**Status:** ✅ Viável | **Impacto:** 🔥🔥 | **Esforço:** Baixo

**Problema atual:** Score simplificado (apples + water + chats). Scoreboard volátil.

**Solução:**
- Score multidimensional: sobrevivência (ticks), eficiência, social, enterros, recursos
- Guardar `model_used` junto com o score
- Endpoint `GET /worlds/{worldId}/scoreboard` retorna ranking por dimensão
- Comparativo histórico por modelo de IA
- SQLite (via `sqlite3` stdlib) — sem dependência extra

**Schema SQLite proposto:**
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    started_at INTEGER,
    ended_at INTEGER,
    player_count INTEGER
);

CREATE TABLE agent_scores (
    session_id TEXT,
    agent_name TEXT,
    model_used TEXT,
    ticks_survived INTEGER,
    apples_eaten INTEGER,
    water_drunk INTEGER,
    chats_sent INTEGER,
    burials_done INTEGER,
    kills_as_zombie INTEGER,
    final_hp INTEGER,
    total_tokens INTEGER,
    total_cost_usd REAL
);
```

---

### 🟡 Média Prioridade — Expansões Arquiteturais

#### M06 — Memória em 4 Camadas (Como o ChatGPT propôs)
**Status:** ✅ Viável | **Impacto:** 🔥🔥🔥 | **Esforço:** Alto

**Problema atual:** `self.memory = []` com max 10 thoughts. Perde tudo ao reiniciar.

**Proposta da conversa (implementável em Python puro):**

| Camada | Tipo | Implementação |
|--------|------|---------------|
| `short_term` | Últimos eventos da sessão | Lista em memória (atual) |
| `episodic` | Histórias compactadas por dia | dict comprimido no Agent |
| `relational` | Relações (confiança, medo, amizade) | dict `{nome: score}` |
| `benchmark_memory` | Telemetria de decisões | Decision Log (M03) |

**Não precisamos de Vector DB para isso.** Um dict JSON é suficiente para o escopo atual.

```python
self.memory = {
    "short_term": [],        # últimos 20 eventos
    "episodic": {},          # {"dia_3": "Carla me salvou do zumbi"}
    "relational": {          # {"Beto": {"trust": 0.8, "fear": 0.1}}
        "João": {"trust": 0.5, "fear": 0.0, "debt": 0}
    },
    "benchmark": []          # telemetria bruta
}
```

---

#### M07 — Separação simulation-core como Módulo
**Status:** ✅ Viável | **Impacto:** 🔥🔥 | **Esforço:** Médio

**Proposta da conversa:** Extrair `World` e estado dos agentes para módulo reutilizável.

**Estrutura proposta:**
```
backend/
├── simulation/
│   ├── __init__.py
│   ├── world.py          # Motor puro, sem FastAPI
│   ├── agent.py          # Agente puro, sem Google GenAI hardcoded
│   ├── rules.py          # Regras determinísticas isoladas
│   └── serializer.py     # Serialização do estado
├── ai/
│   ├── __init__.py
│   ├── base_adapter.py   # Interface abstrata
│   ├── gemini_adapter.py
│   └── omnirouter_adapter.py
├── api/
│   ├── __init__.py
│   ├── main.py           # FastAPI app
│   └── ws_manager.py     # WebSocket manager
└── storage/
    ├── __init__.py
    ├── session_store.py  # SQLite session storage
    └── replay_store.py   # Replay file storage
```

**Benefício:** Facilita testes unitários, benchmark isolado, e futura integração com Roblox (mesmo backend).

---

#### M08 — Regras Determinísticas vs IA (Separação Clara)
**Status:** ✅ Viável | **Impacto:** 🔥🔥 | **Esforço:** Baixo/Médio

**Problema atual:** Algumas validações de ação estão na IA (prompt), não no engine.

**O que FICA determinístico (engine):**
- Dano por frio (já é)
- Morte por HP zero (já é)
- Consumo de item (já é)
- Inventário (já é)
- Validação de movimento (já é parcialmente)
- Zumbificação (já é)
- Cálculo de score
- **Cooldown de ação por agente** ← novo
- **Limite de orçamento** ← novo (M02)

**O que FICA com IA:**
- Fala/chat
- Justificativa do pensamento
- Escolha entre ações permitidas
- Estratégia social
- "Novela"

**Criar `allowed_actions` context** mais rico, evitando que a IA tente ações inválidas.

---

#### M09 — Frontend Observer Turbinado
**Status:** ✅ Viável | **Impacto:** 🔥🔥 | **Esforço:** Alto

**O que adicionar:**

1. **Painel por agente** — Clicar no agente abre modal com:
   - Timeline de decisões desta sessão
   - Grafo de relações (com quem falou, atacou, enterrou)
   - Custo acumulado (tokens × preço do modelo)
   - Memória atual (short_term + relational)

2. **Timeline de eventos** — Linha do tempo lateral com todos os eventos filtráveis por tipo

3. **HUD de benchmark** — Tabela comparativa de modelos ao vivo:
   | Modelo | Agente | Ticks | Tokens | Custo | Score |
   |--------|--------|-------|--------|-------|-------|

4. **Controle de replay** — Slider de progresso, play/pause, velocidade

---

#### M10 — Sistema de Agentes com Owner/Token
**Status:** ✅ Viável | **Impacto:** 🔥🔥🔥 | **Esforço:** Médio

**Inspiração da conversa:** "cada pessoa aqui pode controlar um!"

**Implementação atual vs proposta:**
| Atual | Proposta |
|-------|---------|
| `AUTHORIZED_IDS` hardcoded no .env | Registro via endpoint |
| Sem owner | `owner_id`, `owner_name` no agente |
| Sem budget real | `token_budget` configurável por owner |
| Sem múltiplos tokens | Geração de `agent_token` UUID |

**Novo endpoint de registro:**
```
POST /agents/register
{
    "owner_name": "Diego",
    "agent_name": "AlphaBot",
    "personality": "Estratégico e frio",
    "model_profile": "cheap-fast",
    "token_budget": 10000
}
→ { "agent_token": "uuid", "agent_id": "uuid" }
```

---

#### M11 — API de Torneio/Campeonato
**Status:** ✅ Viável | **Impacto:** 🔥🔥🔥 | **Esforço:** Alto

**Conceito:** Torneio entre modelos de IA. Ranking global por modelo.

```
POST /tournaments → cria torneio
POST /tournaments/{id}/agents → registra agente com modelo
POST /tournaments/{id}/start → inicia
GET  /tournaments/{id}/leaderboard → ranking ao vivo
GET  /tournaments/{id}/results → resultado final
```

**Modos de torneio:**
- `survival`: Quem sobrevive mais ticks
- `social`: Quem tem mais chats + enterros + amizade
- `efficiency`: Relação custo/performance (custo em USD por ponto de score)

---

### 🟢 Baixa Prioridade — Melhorias de Qualidade

#### M12 — Testes Unitários do Motor
**Status:** ✅ Viável | **Impacto:** 🔥 | **Esforço:** Médio

**Proposta da conversa:** "testes de regressão do mundo"

- `pytest` para regras determinísticas
- Testar: tick de morte, enterro, zumbi, BFS pathfinding, vitals
- CI básico via GitHub Actions

---

#### M13 — Dockerfile e Docker Compose
**Status:** ✅ Viável | **Impacto:** 🔥🔥 | **Esforço:** Baixo

**Setup simples:**
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
  frontend:
    image: nginx:alpine
    volumes: ["./frontend:/usr/share/nginx/html"]
    ports: ["3000:80"]
```

---

#### M14 — WebSocket Escalável (Redis Pub/Sub)
**Status:** ✅ Viável (com Redis) | **Impacto:** 🔥 | **Esforço:** Alto

**Problema atual:** `ConnectionManager` em memória → single-worker only.

**Solução com Redis:**
- Add `redis` e `broadcaster` ao requirements
- Substituir `ConnectionManager` por pub/sub via Redis channel
- Permite múltiplos workers Uvicorn (horizontal scale)
- **Necessário apenas se quiser múltiplos workers** (baixa prioridade para demo)

---

#### M15 — README e Docs Completos
**Status:** ✅ Viável | **Impacto:** 🔥🔥 | **Esforço:** Baixo

- README atualizado com arquitetura, screenshots, badges
- Documentação em `/docs` (já iniciada neste sprint)
- ADR (Architecture Decision Records) para decisões importantes
- `CONTRIBUTING.md` para colaboradores

---

## ❌ O que NÃO será feito (nesta versão)

### Integração Roblox (Sem migração)
**Status:** ❌ Fora de escopo | **Motivo:** Mudança de plataforma completa

A integração Roblox **não será feita**, mas o backend está preparado para ela:
- O endpoint `/agents/think` já pode ser chamado por Luau via `HttpService:RequestAsync()`
- Seria necessário: Roblox Studio, Luau scripting, PathfindingService
- Se quiser no futuro: o backend atual funciona sem mudanças como gateway para Roblox

### Vector DB para Memória
**Status:** ❌ Overkill | **Motivo:** Overhead desnecessário

O ChatGPT sugeriu "vector DB depois" para memória. Para o escopo atual, **dict JSON é suficiente** (M06). Qdrant/Chroma seriam necessários apenas com centenas de agentes e histórico multi-sessão por agente.

### GenerationService / Procedural World
**Status:** ❌ Fora de escopo | **Motivo:** Feature Roblox específica

O `GenerationService` mencionado é nativo do Roblox. Não aplicável aqui.

---

## 📊 Matriz de Viabilidade

| ID | Melhoria | Viável? | Impacto | Esforço | Prioridade |
|----|----------|---------|---------|---------|-----------|
| M01 | Multi-Provider / OmniRouter | ✅ Sim | 🔥🔥🔥 | Médio | 🔴 Alta |
| M02 | Budget de tokens | ✅ Sim | 🔥🔥🔥 | Baixo | 🔴 Alta |
| M03 | Decision Log NDJSON | ✅ Sim | 🔥🔥🔥 | Baixo | 🔴 Alta |
| M04 | Replay de sessão | ✅ Sim | 🔥🔥🔥 | Médio | 🔴 Alta |
| M05 | Scoreboard SQLite | ✅ Sim | 🔥🔥 | Baixo | 🔴 Alta |
| M06 | Memória 4 camadas | ✅ Sim | 🔥🔥🔥 | Alto | 🟡 Média |
| M07 | simulation-core módulo | ✅ Sim | 🔥🔥 | Médio | 🟡 Média |
| M08 | Regras determinísticas | ✅ Sim | 🔥🔥 | Médio | 🟡 Média |
| M09 | Frontend observer turbinado | ✅ Sim | 🔥🔥 | Alto | 🟡 Média |
| M10 | Owner/Token por agente | ✅ Sim | 🔥🔥🔥 | Médio | 🟡 Média |
| M11 | API de torneio | ✅ Sim | 🔥🔥🔥 | Alto | 🟡 Média |
| M12 | Testes unitários | ✅ Sim | 🔥 | Médio | 🟢 Baixa |
| M13 | Dockerfile | ✅ Sim | 🔥🔥 | Baixo | 🟢 Baixa |
| M14 | Redis WebSocket | ✅ Sim | 🔥 | Alto | 🟢 Baixa |
| M15 | Docs completos | ✅ Sim | 🔥🔥 | Baixo | 🔴 Alta |
| R01 | Integração Roblox | ❌ Não | — | Muito alto | ❌ |
| R02 | Vector DB memória | ❌ Overkill | — | Alto | ❌ |

---

## 🗓️ Roadmap de Implementação

### v0.2 — Engine Confiável (Quick Wins)
> **Objetivo:** Base sólida para benchmark. Sem mudar gameplay.

- [x] Documentação técnica `/docs` ← **esta sprint**
- [ ] M02 — Budget de tokens e cooldown
- [ ] M03 — Decision Log NDJSON estruturado
- [ ] M05 — Scoreboard SQLite detalhado
- [ ] M15 — README atualizado
- [ ] M13 — Dockerfile

**Entrega:** Backend mais confiável, com logging e custo controlado.

---

### v0.3 — Multi-Provider Benchmark
> **Objetivo:** Transformar a ilha em benchmark real de modelos de IA.

- [ ] M01 — AI Adapter multi-provider (OmniRouter + Gemini + OpenAI)
- [ ] M07 — Refatoração simulation-core modular
- [ ] M08 — Separação regras determinísticas
- [ ] M06 — Memória em 4 camadas
- [ ] M12 — Testes unitários do motor

**Entrega:** Cada NPC usa um modelo diferente. Ranking por modelo ao vivo.

---

### v0.4 — Plataforma de Competição
> **Objetivo:** Usuários registram agentes e competem.

- [ ] M04 — Replay de sessão (gravação + player)
- [ ] M09 — Frontend observer turbinado (painel por agente, timeline)
- [ ] M10 — Owner/Token por agente (registro público)
- [ ] M11 — API de torneio/campeonato

**Entrega:** Campeonato aberto. Cada pessoa configura seu agente com seu modelo preferido.

---

### v0.5 — Escala (Opcional)
> **Objetivo:** Suportar muitos usuários simultâneos.

- [ ] M14 — Redis Pub/Sub para WebSocket multi-worker
- [ ] Deploy em VPS com Nginx + Docker Compose

---

## ⚠️ Guardrails Obrigatórios (da conversa ChatGPT)

> Estes pontos foram explicitados como riscos críticos e devem ser implementados primeiro.

1. **Cooldown de pensamento por NPC** — Nunca chamar IA mais de 1x por N ticks
2. **Orçamento por agente** — Limite de tokens/custo configurável
3. **Ação sempre validada pela engine** — IA sugere, engine valida e aplica
4. **Logging por decisão** — Rastreabilidade de cada chamada de IA
5. **Fallback por provider/modelo** — Se Gemini falha, não trava o jogo

---

## 💡 Próximos Passos Imediatos

1. Implementar **M02 (Budget)** + **M03 (Decision Log)** — Levam < 1 dia
2. Criar **SQLite scoreboard (M05)** — Substitui o JSON frágil atual
3. Criar **AI Adapter (M01)** com OmniRouter — O cenário mais empolgante
4. Começar com 2-3 modelos diferentes por NPC e gravar estatísticas
