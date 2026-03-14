# 📡 API Reference — BBBia: A Ilha da IA

> **Base URL (local):** `http://localhost:8000`  
> **WebSocket:** `ws://localhost:8000/ws`

---

## Autenticação

Endpoints administrativos requerem o header `X-Admin-Token`.

```
X-Admin-Token: <ADMIN_TOKEN>
```

O `ADMIN_TOKEN` é configurado no `.env`. Default: `dev_token_123`.

---

## REST Endpoints

### `GET /`
Status da engine.

**Resposta:**
```json
{
    "status": "World engine is running",
    "ticks": 1234
}
```

---

### `POST /reset` 🔒 (Admin)
Reinicia o jogo. Requer `X-Admin-Token`.

**Query params:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `player_count` | `int` | `4` | Número de NPCs |

**Resposta:**
```json
{
    "status": "World reset successful",
    "player_count": 4
}
```

---

### `POST /settings/ai_interval` 🔒 (Admin)
Define o intervalo de decisão da IA (em ticks).

**Query params:**
| Param | Tipo | Descrição |
|-------|------|-----------|
| `interval` | `int` | `0` = modo paralelo (todos pensam a cada tick). `N` = turnos, um por vez a cada N ticks |

**Resposta:**
```json
{
    "status": "Interval updated",
    "new_interval": 5
}
```

---

### `POST /join`
Entrada de um agente remoto (controlado externamente) na ilha.

**Requer:** `agent_id` deve estar na lista `AUTHORIZED_IDS` do `.env`.

**Body:**
```json
{
    "agent_id": "777",
    "name": "MeuAgente",
    "personality": "Curioso e estratégico. Gosta de explorar o mapa."
}
```

**Resposta:**
```json
{
    "status": "Joined successfully",
    "agent_id": "777",
    "name": "MeuAgente",
    "personality": "Curioso e estratégico...",
    "coords": [10, 10]
}
```

**Erros:**
- `401`: `agent_id` não autorizado
- `400`: `agent_id` já está em uso por agente vivo

---

### `GET /agent/{agent_id}/context`
Retorna o contexto atual do agente remoto (o que ele vê, status de vitals, inventário).

**Resposta:**
```json
{
    "time": 450,
    "is_night": false,
    "visible_entities": [...],
    "reachable_now": ["ÁRVORE COM FRUTO em 5,3"],
    "can_gather_now": true,
    "can_drink_now": false,
    "inventory": ["fruit"],
    "is_moving_automatically_to": null,
    "is_carrying_body": false,
    "carrying_name": null,
    "status": {
        "hp": 85,
        "hunger": 60,
        "thirst": 45,
        "is_alive": true,
        "is_zombie": false,
        "inventory": ["fruit"],
        "pos": [5, 4]
    }
}
```

---

### `POST /agent/{agent_id}/action`
Agente remoto envia uma ação para execução imediata.

**Body:**
```json
{
    "thought": "Preciso comer antes de escurecer",
    "action": "eat",
    "speak": "Ótimo, finalmente uma maçã!",
    "target_name": "",
    "params": {}
}
```

**Ações disponíveis:** `move`, `move_to`, `gather`, `eat`, `fill_bottle`, `drink`, `speak`, `wait`, `pickup_body`, `bury`, `attack`

**Params por ação:**
| Ação | Params |
|------|--------|
| `move` | `{"dx": -1, "dy": 0}` (valores: -1, 0 ou 1) |
| `move_to` | `{"target_x": 15, "target_y": 5}` |
| `attack` | Body: `"target_name": "João"` |

**Resposta:**
```json
{
    "status": "Action processed",
    "action": "eat"
}
```

---

### `DELETE /agent/{agent_id}` 🔒 (Admin)
Remove um agente da ilha.

**Resposta:**
```json
{
    "status": "Agent removed",
    "agent_id": "777"
}
```

---

## WebSocket `/ws`

### Conectar
```javascript
const ws = new WebSocket("ws://localhost:8000/ws");
```

### Mensagens recebidas (servidor → cliente)

#### `init` — Estado inicial ao conectar
```json
{
    "type": "init",
    "data": { /* world state */ }
}
```

#### `update` — Atualização a cada tick (~1s)
```json
{
    "type": "update",
    "data": { /* world state */ },
    "events": [
        {
            "agent_id": "uuid",
            "name": "João",
            "action": "eat",
            "speak": "Que maçã deliciosa!",
            "target_name": "",
            "event_msg": "comeu a fruta! Fome: 95/100",
            "thought": "Estava com muita fome"
        }
    ]
}
```

#### `reset` — Jogo reiniciado
```json
{
    "type": "reset",
    "data": { /* world state */ }
}
```

### World State Schema
```json
{
    "ticks": 1234,
    "game_over": false,
    "winner": null,
    "winner_id": null,
    "day_cycle": 45,
    "is_night": false,
    "ai_interval": 5,
    "player_count": 4,
    "next_agent": "João",
    "ticks_to_next_turn": 3,
    "reset_countdown": null,
    "scores": { "João": 2, "Maria": 1 },
    "hall_of_fame": [
        {
            "name": "Maria",
            "apples": 12,
            "water": 8,
            "chats": 45,
            "tick": 320,
            "score": 65
        }
    ],
    "entities": {
        "agent_uuid": {
            "type": "agent",
            "x": 5,
            "y": 3,
            "name": "João",
            "hp": 85,
            "hunger": 70,
            "thirst": 55,
            "friendship": 60,
            "is_alive": true,
            "is_zombie": false,
            "inventory": ["fruit"],
            "held_item": null,
            "apples_eaten": 3,
            "water_drunk": 2,
            "chats_sent": 15
        },
        "tree_5_3": {
            "type": "tree",
            "x": 5,
            "y": 3,
            "fruit_stage": 3
        },
        "water_10_10": {
            "type": "water",
            "x": 10,
            "y": 10
        }
    }
}
```

### Tipos de Entidade
| Tipo | Descrição |
|------|-----------|
| `agent` | NPC ou jogador remoto |
| `tree` | Árvore com fruta (fruit_stage: 1-3) |
| `water` | Tile de lago |
| `stone` | Pedra (obstáculo) |
| `house` | Casa (abrigo do agente) |
| `cemetery` | Área do cemitério |
| `dead_agent` | Túmulo (após enterro) |
| `dropped_fruit` | Fruta no chão |

---

## Fluxo de Integração (Agente Remoto)

```
1. POST /join  →  Receber agent_id confirmado
2. Loop:
   a. GET /agent/{id}/context  →  Obter estado atual
   b. Processar com sua IA/lógica
   c. POST /agent/{id}/action  →  Enviar decisão
   d. Aguardar N segundos
3. Observar via WebSocket /ws para ver todos os eventos
```

---

## Configuração `.env`

```env
GEMINI_API_KEY=sua_chave_aqui
ADMIN_TOKEN=token_secreto_admin
AUTHORIZED_IDS=777,888,999
ALLOWED_ORIGINS=http://localhost:3000,http://meusite.com
```
