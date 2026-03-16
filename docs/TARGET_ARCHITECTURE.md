# Arquitetura Alvo

Este documento descreve a direcao de modularizacao recomendada sem reescrever a stack atual.

## Objetivo

Levar o projeto de um backend monolitico funcional para um arranjo mais claro entre:

- API HTTP/WebSocket
- simulacao do mundo
- runtime de IA
- persistencia

## Principios

1. manter FastAPI e o frontend web atual
2. modularizar sem reescrita total
3. preservar o fluxo de benchmark entre perfis
4. evitar nova infraestrutura antes da necessidade real
5. manter o setup local simples

## Topologia desejada

```text
web-observer
    |
    v
world-api
    |
    +--------------------+
    |                    |
    v                    v
simulation-core     agent-runtime
    |                    |
    +---------+----------+
              |
              v
            storage
```

## Recorte de modulos desejado

```text
backend/
├── api/
│   ├── app.py
│   ├── deps.py
│   ├── routes_agents.py
│   ├── routes_admin.py
│   ├── routes_sessions.py
│   └── ws_manager.py
├── simulation/
│   ├── world.py
│   ├── actions.py
│   ├── entities.py
│   └── serializer.py
├── runtime/
│   ├── thinker.py
│   ├── profiles.py
│   ├── memory.py
│   └── adapters/
└── storage/
    ├── session_store.py
    ├── replay_store.py
    ├── decision_log.py
    ├── memory_store.py
    └── webhook_manager.py
```

## Contratos que valem a pena preservar

### `AgentProfile`

Exemplo alinhado com o catalogo atual:

```json
{
  "profile_id": "claude-kiro",
  "provider": "omnirouter",
  "model": "kr/claude-sonnet-4.5",
  "temperature": 0.7,
  "max_tokens": 400,
  "token_budget": 15000,
  "cooldown_ticks": 4
}
```

### `AgentRegistration`

```json
{
  "owner_id": "diego",
  "owner_name": "Diego",
  "agent_name": "AlphaBot",
  "persona": "Curioso e competitivo",
  "profile_id": "claude-kiro"
}
```

### `ActionDecision`

```json
{
  "thought": "Preciso sair do frio e continuar vivo",
  "speak": "Vou voltar para casa antes da noite apertar",
  "intent": "survive_and_coordinate",
  "action": "move_to",
  "params": {
    "target_x": 2,
    "target_y": 17
  }
}
```

## Problemas que esta arquitetura alvo resolve

- reduz o acoplamento atual de `main.py`
- permite testar simulacao sem subir a API inteira
- prepara o sistema para trocar o broadcast local por um barramento entre processos
- torna os componentes de runtime e storage mais reutilizaveis

## Passos incrementais sugeridos

1. extrair rotas de `main.py` para `backend/api/`
2. mover `world_loop()` e coordenacao de estado para um servico dedicado
3. isolar serializacao de estado e regras de replay
4. introduzir um transport layer para broadcast
5. revisar paths de storage para nao depender do diretorio de boot
