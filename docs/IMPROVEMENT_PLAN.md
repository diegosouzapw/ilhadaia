# Plano de Implementacao

Este documento resume o que ja foi consolidado no projeto e o que foi ajustado especificamente nesta branch para fechar o ciclo de operacao, documentacao e setup local.

## Base consolidada antes desta branch

Ja existiam no repositorio:

- simulacao em tempo real com `World`
- persistencia de sessoes, scoreboard, memoria e replay
- adapters Gemini + OpenAI-compatible
- `Thinker` para orquestracao das decisoes
- dashboard analitico
- endpoints de torneio, exportacao, memoria e webhook

## Ajustes consolidados nesta branch

### 1. Frontend servido pelo backend

Mudanca:

- `backend/main.py` monta `StaticFiles` em `/frontend`

Impacto:

- `index.html`, `dashboard.html` e `models.html` agora fazem parte do fluxo oficial de uso
- a documentacao deixa de orientar `file://`

### 2. Catalogo de perfis free-first

Mudanca:

- `backend/runtime/profiles.py` foi atualizado para um conjunto focado em OmniRoute + perfis gratuitos
- fallback tecnico passou para `claude-kiro`

Perfis atuais:

- `claude-kiro`
- `claude-haiku`
- `kimi-thinking`
- `qwen-coder`
- `kimi-groq`
- `gemini-flash`
- `llama-groq`

### 3. Defaults operacionais alinhados

Mudanca:

- `POST /agents/register` agora defaulta para `claude-kiro`
- o estado serializado do mundo usa `claude-kiro` como fallback de `profile_id`
- os NPCs iniciais usam uma rotacao gratuita predefinida

### 4. Console de modelos

Mudanca:

- `frontend/models.html` passou a ser uma interface oficial do sistema

Capacidades:

- listar perfis
- testar chamadas por modelo
- registrar agentes
- inspecionar agentes ativos

Ajuste feito nesta continuacao:

- o select de cadastro agora sincroniza com `GET /profiles`, evitando divergencia entre backend e UI

### 5. Operacao limpa do repositorio

Mudanca:

- `.gitignore` cobre banco, WAL, replays, logs e JSONs de runtime
- `backend/data/ilhadaia.db`, `backend/data/ilhadaia.db-shm`, `backend/data/ilhadaia.db-wal` e `backend/world_settings.json` sairam do versionamento
- o workspace foi limpo para o backend voltar a gerar estado do zero

### 6. Documentacao reconciliada

Arquivos atualizados:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/API_REFERENCE.md`
- `docs/DEVELOPMENT_GUIDE.md`
- `docs/BACKLOG.md`
- `docs/CURRENT_STATE_AUDIT.md`
- `docs/TARGET_ARCHITECTURE.md`

## Validacao executada

Comando rodado nesta atualizacao:

```bash
pytest backend/tests/test_engine.py -q
```

Resultado:

- `33 passed`

## Proximo passo tecnico recomendavel

Se houver nova rodada de trabalho estrutural, o melhor ROI agora e:

1. quebrar `backend/main.py` em modulos de rota e servico
2. desacoplar broadcast WebSocket do processo unico
3. resolver paths de storage independentemente do diretorio de boot
