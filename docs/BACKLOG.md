# Backlog

Este backlog foi reduzido para o que realmente continua em aberto depois desta branch. Nao inclui mais artefatos de runtime nem divergencias entre docs e codigo, porque esses pontos foram saneados aqui.

## Prioridade alta

### 1. Broadcast multi-worker

Problema atual:

- o `ConnectionManager` ainda vive em memoria dentro de um unico processo
- com mais de um worker, cada processo teria sua propria lista de conexoes

Caminho sugerido:

- introduzir um barramento de eventos entre processos
- Redis pub/sub continua sendo a opcao mais simples
- separar transporte WebSocket de geracao de eventos do mundo

## Prioridade media

### 2. Modularizar `backend/main.py`

Problema atual:

- `main.py` concentra lifespan, rotas, loop do mundo, exportacoes e webhooks

Caminho sugerido:

- mover rotas para modulos dedicados
- extrair `world_loop()` e orchestration para modulos independentes
- reduzir estado global compartilhado

### 3. Tornar storage independente do diretorio de execucao

Problema atual:

- os paths de `data/` e `logs/` funcionam como esperado quando o backend sobe a partir de `backend/`

Caminho sugerido:

- resolver paths a partir de `__file__` ou configuracao explicita
- permitir boot a partir da raiz sem ambiguidade de arquivos gerados

## Prioridade baixa

### 4. Melhorar a estrategia de smoke test

O projeto ja tem uma suite util de backend, mas ainda falta uma verificacao integrada leve para:

- boot do FastAPI
- carga das tres paginas em `/frontend`
- conexao WebSocket
- criacao de sessao limpa em ambiente zerado

### 5. Evoluir a observabilidade

Possiveis ganhos:

- metricas Prometheus
- tracing de chamadas a providers
- painel de saude para rate limiting e webhooks

## Itens explicitamente resolvidos nesta branch

- frontend servido pelo backend em `/frontend/*`
- runtime state fora do versionamento
- tela `models.html` integrada ao catalogo de perfis do backend
- default tecnico e operacional migrado para `claude-kiro`
