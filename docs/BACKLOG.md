# 📋 BACKLOG — BBBia Versão Turbinada

> Versão: v0.5 | Data: Março 2026
> Tasks T01–T16 + T18–T24 implementadas. Apenas T17 permanece como backlog.

---

## ⏳ T17 — Redis WebSocket (Backlog)

**Versão planejada:** v0.6  
**Prioridade:** Média-Alta  
**Esforço estimado:** 4–6 horas  
**Pré-requisito:** Redis instalado e acessível (serviço externo)

### Contexto
O backend atual usa um `ConnectionManager` em memória para broadcast dos WebSocket. Isso funciona bem para **single worker**, mas impede escala horizontal (múltiplas réplicas uvicorn).

### Proposta de Implementação

**Dependências:**
```
redis>=5.0
aioredis>=2.0
```

**Arquivo novo:** `backend/messaging/redis_pubsub.py`

```python
import redis.asyncio as aioredis
import asyncio, json

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHANNEL = "bbbia:world_events"

class RedisPubSubManager:
    async def connect(self): ...
    async def publish(self, message: dict): ...
    async def subscribe(self, ws): ...
```

**Mudanças em `main.py`:**
- Substituir `ConnectionManager.broadcast()` por `RedisPubSubManager.publish()`
- `world_loop()` publica no canal Redis
- Cada worker consome do canal e envia aos seus WebSockets locais

**`docker-compose.yml`:**
```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

### Critério de Aceite
- [ ] Dois workers uvicorn simultâneos recebem o mesmo evento pelo Redis
- [ ] Falha do Redis retorna ao broadcast em memória graciosamente
- [ ] Métricas de latência não degradam (< +5ms no P95)

---

## 💡 Ideias Futuras (Não Priorizadas)

| Ideia | Complexidade | Impacto |
|-------|-------------|---------|
| Vector store para episódic memory (ChromaDB) | Alta | Médio |
| Web scraping de context externo por agente | Alta | Médio |
| Streaming de respostas da IA (SSE) | Média | Alto |
| Modo Espectador com câmera seguindo agente | Média | Alto |
| Multi-ilha (múltiplos worlds paralelos) | Muito Alta | Alto |
| Ranking ELO entre modelos | Baixa | Alto |
| Interface admin para gerenciar torneios ao vivo | Média | Médio |
| Mobile-first no dashboard | Baixa | Médio |

---

## Estrutura Atual (v0.5)

```
backend/
├── main.py               ← 700+ linhas, 30+ endpoints
├── agent.py              ← AgentMemory integrada
├── runtime/
│   ├── thinker.py        ← Orquestrador AI
│   ├── profiles.py       ← 6 perfis
│   ├── memory.py         ← 4 camadas
│   ├── schemas.py        ← ActionDecision
│   ├── relevance.py      ← TF-IDF episódico
│   └── tournament_runner.py
├── storage/
│   ├── session_store.py  ← SQLite WAL
│   ├── decision_log.py   ← NDJSON
│   ├── replay_store.py   ← Snapshots
│   ├── memory_store.py   ← Memória persistente
│   └── webhook_manager.py ← Notificações HMAC
└── tests/
    └── test_engine.py    ← 31/31 ✅

frontend/
├── index.html            ← 3D + HUD + Replay + Timeline
├── dashboard.html        ← Dashboard analítico
├── benchmark.js
└── style.css
```
