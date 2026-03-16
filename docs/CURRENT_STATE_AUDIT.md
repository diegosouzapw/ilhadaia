# Estado Atual do Projeto

Data desta revisao: marco de 2026.

## Resumo executivo

O projeto esta funcional como um simulador local de agentes com benchmark de modelos e tres interfaces web servidas pelo backend. O maior ganho desta branch nao foi adicionar uma feature de gameplay, e sim fechar o ciclo operacional:

- defaults de perfil alinhados para uso gratuito
- docs reconciliadas com o codigo real
- artefatos de runtime removidos do versionamento
- app pronta para recriar estado do zero em um boot limpo

## Estado validado

### Backend

- FastAPI sobe a API principal em `backend/main.py`
- `StaticFiles` serve `frontend/` em `/frontend`
- `Thinker` coordena chamadas de IA
- `SessionStore`, `ReplayStore`, `DecisionLog`, `MemoryStore` e `WebhookManager` continuam ativos
- fallback de perfil foi migrado para `claude-kiro`

### Perfis

Total atual: `8` perfis builtin.

Default operacional:

- registro de agente: `claude-kiro`
- fallback tecnico: `claude-kiro`
- squad inicial da ilha: `claude-kiro`, `kimi-thinking`, `kimi-groq`, `claude-haiku`

### Frontend

Interfaces oficiais:

- `index.html`
- `dashboard.html`
- `models.html`

Observacoes:

- `models.html` esta integrada a `GET /profiles`
- a navegacao entre as tres paginas esta consistente
- o HUD de benchmark na ilha pode ser movido e recolhido

## Persistencia e runtime

Artefatos gerados em execucao:

- `backend/data/ilhadaia.db`
- `backend/data/replays/*.replay.ndjson`
- `backend/logs/*.ndjson`
- `backend/hall_of_fame.json`
- `backend/world_settings.json`

Estado apos esta limpeza:

- esses arquivos nao estao mais versionados
- o workspace foi resetado para que o backend recrie tudo a partir de zero

## Validacao tecnica feita nesta continuacao

Suite executada:

```bash
pytest backend/tests/test_engine.py -q
```

Resultado observado:

- `33 passed in 3.91s`

## Riscos remanescentes

- `backend/main.py` continua centralizando muita responsabilidade
- o manager de WebSocket ainda nao suporta escala horizontal
- paths relativos de storage dependem do backend ser iniciado a partir de `backend/`

## Conclusao

A branch agora esta em um estado coerente para abrir PR:

- diff funcional organizado
- docs alinhadas com o codigo
- repositorio sem banco, WAL, replay e settings indevidamente versionados
- setup padrao documentado com foco em perfis gratuitos
