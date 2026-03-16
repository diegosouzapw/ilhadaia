# Backlog — BBBia

---

## Pendências Técnicas Reais

### T17 — Multi-worker com Redis pub/sub
- **Status:** Backlog
- **Por quê:** A arquitetura atual usa um único worker FastAPI + asyncio com WebSocket broadcast local. Para escalar horizontalmente (múltiplos workers ou pods), o broadcast precisa de um pub/sub externo (Redis).
- **Impacto:** Sem isso, apenas 1 worker pode ser executado por vez.

### T25 — Persistência de Memória em Sessões Longas
- **Status:** Backlog
- **Por quê:** `MemoryStore` serializa `AgentMemory` por `owner_id`. Em sessões muito longas, episódios antigos nunca são purgados do SQLite.
- **Sugestão:** Implementar TTL ou limite de episódios no `memory_store`.

### Autenticação de Providers no OmniRoute
- **Status:** Monitoramento
- **Problema:** Providers que exigem OAuth (como `gc/` via Gemini CLI) podem retornar 403 por rate limit de conta. O runtime não faz retry inteligente por provider.
- **Sugestão:** Implementar fallback de provider no `Thinker` quando o adapter retornar 4xx.

### Drag do Benchmark HUD — Persistência em Mobile
- **Status:** Backlog
- **Problema:** A posição do HUD é salva no `localStorage` por desktop. Em dispositivos touch, o HUD pode sair da área visível.
- **Sugestão:** Limitar `left`/`top` ao viewport ao restaurar posição.

---

## Ideias Futuras

- **Leaderboard público** — endpoint open para observadores externos votarem/acompanharem
- **Multi-ilha** — múltiplas instâncias `World` em sessões paralelas
- **Agente treinável** — fine-tuning local com decisões bem-sucedidas
- **Plugin de provider** — suporte a providers adicionais via config sem alterar código
- **Dashboard mobile** — layout responsivo para `dashboard.html` e `models.html`

---

## Itens Implementados (removidos do backlog)

| Task | Implementação |
|------|--------------|
| T01-T09 | Motor base (grid, vitals, inventário, ciclo dia/noite, chat) |
| T10 | AgentMemory 4 camadas |
| T11 | ActionDecision Pydantic |
| T12 | OmniRoute via OpenAICompatibleAdapter |
| T13 | Replay store NDJSON |
| T14 | `/agents/register` com perfis |
| T15 | Sistema de torneios (join/start/leaderboard) |
| T16 | Benchmark HUD ao vivo + drag-and-drop + colapso |
| T17 | Backlog — Redis pub/sub |
| T18 | Rate limiting via slowapi |
| T19 | Export CSV/JSON de sessões/scoreboard |
| T20 | TournamentRunner automático |
| T21 | Busca episódica por relevância (TF-IDF) |
| T22 | MemoryStore SQLite |
| T23 | Frontend `models.html` (gerenciador de perfis) |
| T24 | WebhookManager com HMAC |
| T25 | Nav global nas 3 telas |
| T26 | Sidebar da ilha (atalhos, replay, timeline integrados) |
| T27 | `/settings/ai` + `/models` — catálogo dinâmico de IA |
| T28 | Dropdown de perfis dinâmico no `models.html` |
| T29 | `.gitignore` corrigido — exclui .db, logs, replays, .env |
