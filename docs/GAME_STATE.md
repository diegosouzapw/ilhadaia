# 🎮 Game State & Simulation Logic — BBBia: A Ilha da IA

> Documento técnico sobre a lógica de simulação, ciclo de jogo e estado do mundo.

---

## O Mundo (Grid)

A ilha é um grid **20×20 tiles**. O sistema de coordenadas é `(x, y)` onde:
- `(0, 0)` é o canto superior esquerdo
- `(19, 19)` é o canto inferior direito

### Pontos Fixos de Interesse

| Local | Coordenada | Descrição |
|-------|-----------|-----------|
| Lago (centro) | ~`(10, 10)` | Radius 2.5 tiles de água |
| Casa do João | `(2, 2)` | Abrigo azul |
| Casa da Maria | `(17, 17)` | Abrigo vermelho |
| Casa do Zeca | `(17, 2)` | Abrigo verde |
| Casa da Elly | `(2, 17)` | Abrigo roxo |
| Cemitério | `(15, 5)` | Enterro de corpos |

### Geração de Recursos

| Tipo | Probabilidade | Condição |
|------|--------------|----------|
| Pedra (stone) | 2% por tile | Qualquer tile não-lago |
| Árvore (tree) | 1% por tile | Tiles a >20 dist² do lago |

---

## Ciclo Dia/Noite

**Duração total:** 120 ticks por ciclo completo.

| Fase | Ticks (mod 120) | Evento |
|------|-----------------|--------|
| ☀️ Dia | 0–79 | Normal. Zumbis ao sol são destruídos se fora de casa |
| 🌅 Entardecer | 70–79 | Transição visual |
| 🌙 Noite | 80–109 | Frio fora de casa (-2 HP/tick), mortos podem virar zumbi |
| 🌄 Amanhecer | 110–119 | Transição visual |

**Relógio fictício:** 1 tick = 12 minutos. Começa às 04:00.

---

## Vitais dos Agentes

| Vital | Faixa | Decay/tick | Efeito em 0 |
|-------|-------|-----------|-------------|
| `hunger` | 0–100 | -1 a -2 (random) | Perde HP |
| `thirst` | 0–100 | -1 a -3 (random) | Perde HP |
| `hp` | 0–100 | Varia | Morte ao chegar a 0 |
| `friendship` | 0–100 | -1 a -2 (random) | Penalidade emocional |

**Recuperação:** Se `hunger > 70` AND `thirst > 70`: `+1 a +2 HP/tick`

**Bônus de carregar corpo:** Enquanto carrega um corpo, o agente tem vitals travados em 100, HP em 100 e amizade restaurada para 100 (altruísmo recompensado).

---

## Sistema de Itens

| Item | Origem | Efeito |
|------|--------|--------|
| `fruit` | Árvore com `fruit_stage == 3` | `eat` → +80 hunger |
| `water_bottle` | Lago (adjacente) | `drink` → thirst = 100 |
| `dead_body` | Agente morto não enterrado | Carregado para cemitério |

**Inventário:** Máximo 3 itens. Coleta automática ao passar pelo item.

**Reaparecimento de frutas:** A cada 80 ticks, `fruit_stage` sobe 1 (até máximo 3).

---

## Sistema de Zumbis

```
Agente morre
    │
    └─► Corpo fica no chão (is_alive=false, is_buried=false)
              │
              ├─ Noite começa (tick%120 >= 80)
              │       └─► Corpo não carregado → is_zombie = true
              │               • Nome vira "Nome Zumbi"
              │               • HP = 200, hunger/thirst = 100
              │               • Comportamento controlado por IA (Gemini)
              │               • Pode atacar: -20 HP por ataque
              │
              └─ Dia começa (tick%120 < 80)
                      └─► Zumbi fora de casa → DESTRUÍDO (vira pó)
                          Zumbi dentro de casa → sobrevive
                              └─► Após 120 ticks como zumbi → CURADO
                                  (volta humano com HP=100, hunger/thirst=50)
```

**Miasma:** Se há algum corpo não enterrado, **todos os vivos** perdem 1-2 HP/tick.

**Observação adicional:** o prompt atual dos agentes já instrui sobreviventes a buscarem abrigo e zumbis a tentarem sobreviver escondidos para se curar, o que reforça a "novela emergente" da ilha.

---

## Sistema de Score

### Scoreboard atual (simplificado)
Hall of Fame salva top 3 por `score = apples_eaten + water_drunk + chats_sent`.

### Pontuação por ação
| Ação | Pontos |
|------|--------|
| Comer fruta | +1 `apples_eaten` |
| Beber água | +1 `water_drunk` |
| Falar/Chat | +1 `chats_sent` |

### Vitórias por sessão
Guardado em `scores` dict: `scores[name] = count_of_wins`.

### Limitações do score atual
- Não registra qual modelo foi usado pelo agente
- Não separa sobrevivência, utilidade social e eficiência
- Não persiste histórico completo por sessão

---

## Pathfinding (BFS)

O mundo usa **BFS (Breadth-First Search)** para pathfinding:
- Suporta **8 direções** (incluindo diagonais)
- Obstáculos: `tree`, `stone`, `water`, `agent` vivo
- Destinos inalcançáveis (ex: lago): chega **adjacente** (dist ≤ 1)
- Sem heurística (A*): O(n²) por busca, adequado para grid 20x20

---

## Sistema de Decisão da IA

O motor suporta dois modos:

1. **Turn-based** (`ai_interval > 0`)  
   Um agente elegível pensa a cada `N` ticks.

2. **Paralelo** (`ai_interval = 0`)  
   Todos os agentes elegíveis podem pensar a cada tick.

Um agente **não é consultado pela IA** quando:
- Está morto
- É remoto (`is_remote=True`)
- Já está caminhando automaticamente para um destino
- Acabou de chegar ao destino no tick atual
- Já está aguardando resposta da IA (`thinking_agents`)

Esse detalhe é importante porque o custo real da simulação depende mais da elegibilidade do agente do que apenas do valor bruto do tick loop.

---

## Percepção do Agente

O contexto usado pela IA inclui:
- `visible_entities` — entidades visíveis na vizinhança
- `reachable_now` — recursos/ações imediatamente alcançáveis
- `inventory`
- `is_night`
- `is_carrying_body`
- `carrying_name`
- destino automático atual (`is_moving_automatically_to`)

**Alcance visual atual:** até distância Manhattan ~12 para entidades relevantes.

Isso ajuda a explicar por que a IA às vezes "sabe" sobre corpos, lago, cemitério ou outros agentes sem enxergar o mapa inteiro.

---

## Auto-Interações por Proximidade

A cada tick, agentes vivos automaticamente:

1. **Coleta fruta** — Se inventário < 3 e árvore madura adjacente
2. **Enche garrafa** — Se inventário < 3 e sem garrafa e lago adjacente  
3. **Pega corpo** — Se inventário < 3 e não carrega corpo e corpo morto adjacente
4. **Enterra corpo** — Se está carregando corpo e está no cemitério

---

## Reset Automático

Após `game_over`, o mundo aguarda **120 ticks (2 minutos)** e então reinicia automaticamente, mantendo scores e hall of fame.

---

## Spawn de Novos Agentes

Quando um agente é enterrado ou um zumbi é destruído:
- Um novo agente da lista `extra_names` (Beto, Carla, Dudu, Eva, Fabio, Gabi) é spawned após **10 ticks**.
- Mantém a ilha sempre com agentes ativos.

**Observação:** esse comportamento já é uma boa base para futuros papéis/skills por persona, porque o pipeline de entrada de novos agentes já existe.
