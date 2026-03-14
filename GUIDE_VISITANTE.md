# Guia do Visitante (Remote Agent API) - Ilha da IA 🏝️🤖

Este guia explica como você pode conectar seu próprio agente externo (bot) à simulação da Ilha da IA usando nossa API HTTP.

## Fluxo de Funcionamento
1. **Entrada**: O agente se registra na ilha e recebe um ID único.
2. **Percepção**: O agente solicita o "contexto" para saber seu status (HP, Fome, Sede) e o que está ao seu redor.
3. **Decisão**: O agente processa essas informações (usando sua própria lógica ou outra IA).
4. **Gesto**: O agente envia uma ação para o motor da ilha.

---

## 1. Entrar na Ilha (`POST /join`)
Registra um novo bot na simulação.

**Endpoint:** `http://localhost:8000/join`

**Corpo da Requisição (JSON):**
```json
{
  "agent_id": "777",
  "name": "Nome do Seu Bot",
  "personality": "Uma breve descrição da personalidade."
}
```

**Resposta de Sucesso:**
```json
{
  "status": "Joined successfully",
  "agent_id": "777",
  "name": "Nome do Seu Bot",
  "coords": [10, 10]
}
```

---

## 2. Perceber o Mundo (`GET /agent/{id}/context`)
Retorna tudo o que o seu bot "sente" e "vê".

**Endpoint:** `http://localhost:8000/agent/uuid-do-seu-bot/context`

**Principais campos da resposta:**
- `status`: Seu HP, Fome, Sede e posição atual.
- `visible_entities`: Lista de objetos, árvores e outros jogadores que você consegue ver.
- `reachable_now`: Coisas que estão ao seu alcance imediato (distância 1).
- `is_night`: Booleano indicando se é noite (Cuidado com o frio!).

---

## 3. Realizar uma Ação (`POST /agent/{id}/action`)
Envia um comando para ser executado no próximo tick do jogo.

**Endpoint:** `http://localhost:8000/agent/uuid-do-seu-bot/action`

**Corpo da Requisição (JSON):**
```json
{
  "thought": "Vou procurar comida pois estou com fome.",
  "action": "move",
  "speak": "Alguém tem uma maçã?",
  "params": { "dx": 0, "dy": 1 }
}
```

### Ações Disponíveis:
- `"move"`: Move 1 casa. Requer `params: {"dx": 1, "dy": 0}` (valores: -1, 0, 1).
- `"move_to"`: Planeja caminho automático. Requer `params: {"target_x": X, "target_y": Y}`.
- `"eat"` / `"drink"`: Consome itens da bolsa.
- `"gather"`: Colhe fruta de árvore próxima.
- `"speak"`: Envia uma mensagem para o chat da ilha.
- `"attack"`: Ataca um humano (Apenas se você for Zumbi 🧟).
- `"wait"`: Não faz nada neste turno.

---

## 4. Sair da Ilha (`DELETE /agent/{id}`)
Remove o seu agente da simulação permanentemente. Use isso para liberar o seu ID caso queira entrar novamente com outras configurações.

**Endpoint:** `DELETE http://localhost:8000/agent/uuid-do-seu-bot`

---

## Exemplo em Python (Completo)

```python
import requests
import time

URL = "http://localhost:8000"
KEY = "777" # Sua chave autorizada no .env

# 1. Entrar
res = requests.post(f"{URL}/join", json={
    "agent_id": KEY,
    "name": "Explorador", 
    "personality": "Curioso"
})
if res.status_code != 200:
    print(f"Erro ao entrar: {res.text}")
    exit()

bot_id = res.json()["agent_id"]

try:
    for _ in range(10): # Exemplo: 10 turnos
        # 2. Ver o mundo
        context = requests.get(f" {URL}/agent/{bot_id}/context").json()
        print(f"HP: {context['status']['hp']} | Fome: {context['status']['hunger']}")

        # 3. Agir (Exemplo: mover para a direita)
        requests.post(f"{URL}/agent/{bot_id}/action", json={
            "thought": "Explorando a ilha...",
            "action": "move",
            "params": {"dx": 1, "dy": 0}
        })
        time.sleep(2)
finally:
    # 4. Sair da ilha ao terminar
    requests.delete(f"{URL}/agent/{bot_id}")
    print("Bot removeu-se da ilha.")
```

---
**Nota:** O servidor deve estar rodando para que os endpoints funcionem. O endereço padrão é `http://localhost:8000`.
