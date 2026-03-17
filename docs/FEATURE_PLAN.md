# Plano de Features e Melhorias — BBBia

> Estado: **✅ IMPLEMENTADO** | Base: `main` | Março 2026 | 174 testes passando

## Status de Implementação

| Fase | Features | Status | Engine |
|------|---------|--------|--------|
| Fase 1 | F01 Comandante, F03 Inspector, F05 Console | ✅ Completo | World nativo |
| Fase 2 | F02 A/B, F06 ELO, F09 Perfis | ✅ Completo | World nativo |
| Fase 3 | F04 Eventos, F07 Reputação, F08 Missões | ✅ Completo | World nativo |
| Fase 4 | F12 Gincana | ✅ Completo | `GincanaEngine` |
| Fase 5 | F13-F16 Warfare | ✅ Completo | `WarfareEngine` |
| Fase 6 | F10, F17-F19 Economy | ✅ Completo | `EconomyEngine` |
| Fase 7 | F20 Guerra de Gangues | ✅ Completo | `GangWarEngine` |
| Fase 8 | F11 Webhooks Expandidos | ✅ Completo | `WebhookManager` |

---

## Objetivo

## Navegacao de execucao detalhada

Para implementacao operacional por fases e por task tecnica, usar a pasta `docs/features/`:

- `docs/features/00_FINAL_IMPLEMENTATION_PLAN.md`
- `docs/features/CHECKLIST.md`
- `docs/features/INDEX.md`
- `docs/features/F01_*.md` ate `docs/features/F20_*.md`

Este documento organiza as proximas features do BBBia com foco em:

- aumentar o valor do simulador como laboratorio de IA
- aprofundar o gameplay e a observabilidade da ilha
- reaproveitar a arquitetura que ja existe hoje
- priorizar entregas que cabem bem no stack atual

Este plano complementa:

- `docs/BACKLOG.md` — pendencias tecnicas e debt real
- `docs/IMPROVEMENT_PLAN.md` — historico do que ja foi consolidado
- `docs/ARCHITECTURE.md` — desenho tecnico atual

Aqui o foco e produto, experiencia, experimentacao e evolucao do sistema.

---

## Premissas do Plano

Antes de adicionar features novas, estas regras continuam valendo:

1. `profile_id` continua sendo a fonte de verdade do runtime.
2. O `Thinker` continua sendo o ponto central de decisao.
3. O backend permanece single-worker ate uma futura evolucao com Redis/pub-sub.
4. Toda feature nova deve, quando possivel, aproveitar os modulos existentes:
   - `runtime/thinker.py`
   - `runtime/profiles.py`
   - `storage/session_store.py`
   - `storage/decision_log.py`
   - `storage/replay_store.py`
   - `storage/memory_store.py`
   - `storage/webhook_manager.py`
5. O frontend oficial continua sendo:
   - `frontend/index.html`
   - `frontend/dashboard.html`
   - `frontend/models.html`

---

## Estrutura Recomendada por Game Mode

Para manter o projeto coerente, as proximas expansoes devem ser encaixadas como `game_mode` da sessao, em vez de misturar todas as regras no modo padrao.

### `survival`

Modo base atual da ilha.

Foco:

- sobrevivencia
- relacoes sociais
- coleta e exploracao
- benchmark geral dos perfis

Features mais conectadas:

- F01, F03, F04, F05, F06, F07, F08, F09, F10, F11

### `gincana`

Modo orientado a objetivo e eficiencia.

Foco:

- desafios curtos
- coleta dirigida
- checkpoints
- score por execucao

Features mais conectadas:

- F02, F04, F08, F12

### `warfare`

Modo competitivo por faccoes e confronto direto.

Foco:

- times
- recursos de combate
- arremesso de objetos
- territorio e eliminacoes

Features mais conectadas:

- F04, F13, F14, F15, F16, F20

### `economy`

Modo sistêmico de mercado, estoque e negociacao.

Foco:

- compra e venda
- contratos
- profissao
- reputacao comercial

Features mais conectadas:

- F08, F10, F17, F18, F19, F20

---

## Resumo Executivo

| ID | Feature | Valor | Esforco | Prioridade |
|----|---------|-------|---------|------------|
| F01 | Modo Comandante por linguagem natural | Muito alto | Medio | P1 |
| F02 | Comparador A/B de perfis e torneios | Muito alto | Medio | P1 |
| F03 | Inspector de decisao por agente | Muito alto | Medio | P1 |
| F04 | Eventos dinamicos da ilha | Alto | Medio | P1 |
| F05 | Console de intervencao ao vivo | Alto | Medio | P1 |
| F06 | Temporadas e ranking ELO | Alto | Medio | P2 |
| F07 | Aliancas, traicao e reputacao social | Alto | Alto | P2 |
| F08 | Missoes e objetivos individuais | Alto | Medio | P2 |
| F09 | Editor versionado de perfis e prompts | Medio/alto | Medio | P2 |
| F10 | Economia, crafting e construcao | Alto | Alto | P3 |
| F11 | Webhooks e integracoes externas expandidas | Medio | Baixo/medio | P3 |
| F12 | Modo Gincana | Muito alto | Medio/alto | P1 |
| F13 | Modo Guerra de Faccoes | Muito alto | Medio | P1 |
| F14 | Sistema de Arremesso e Combate a Distancia | Alto | Medio | P1 |
| F15 | Papeis Taticos de Equipe | Alto | Medio | P2 |
| F16 | Controle de Territorio e Recursos de Guerra | Alto | Medio/alto | P2 |
| F17 | Modo Economia Local | Muito alto | Medio | P1 |
| F18 | Mercado Dinamico com Oferta e Demanda | Alto | Medio | P2 |
| F19 | Contratos, Entregas e Reputacao Comercial | Alto | Medio | P2 |
| F20 | Guerra de Gangues: conflito + logistica | Muito alto | Alto | P2 |

---

## Ordem Recomendada de Implementacao

### Fase 1 — ROI imediato

- F01 — Modo Comandante
- F03 — Inspector de decisao
- F02 — Comparador A/B
- F04 — Eventos dinamicos
- F12 — Modo Gincana
- F13 — Modo Guerra de Faccoes
- F17 — Modo Economia Local

### Fase 2 — Profundidade de simulacao

- F05 — Console de intervencao ao vivo
- F08 — Missoes e objetivos individuais
- F07 — Aliancas, traicao e reputacao
- F06 — Temporadas e ranking ELO
- F09 — Editor versionado de perfis e prompts
- F14 — Sistema de arremesso e combate a distancia
- F18 — Mercado dinamico
- F19 — Contratos e reputacao comercial

### Fase 3 — Expansao de plataforma

- F10 — Economia, crafting e construcao
- F11 — Webhooks e integracoes externas expandidas
- F15 — Papeis taticos de equipe
- F16 — Controle de territorio e recursos de guerra
- F20 — Guerra de Gangues

---

## F01 — Modo Comandante por Linguagem Natural

### Visao

Permitir que um usuario controle um agente por texto livre, como se estivesse "pilotando" o personagem por linguagem natural.

Exemplos:

- "Va ate o lago, beba agua e depois procure frutas."
- "Fuja do zumbi mais proximo e volte para casa."
- "Converse com a Maria e tente formar uma alianca."

### Problema que resolve

- Hoje o usuario observa, mas interage pouco com o comportamento da IA.
- Falta um modo de demonstracao mais forte para testar obediencia, planejamento e interpretacao.

### Experiencia esperada

- O usuario clica em um agente na ilha.
- Abre um modal "Modo Comandante".
- Digita uma instrucao.
- O agente tenta converter essa instrucao em uma acao valida dentro do schema atual.
- A UI mostra o status: `pendente`, `executado`, `falhou`, `expirado`, `cancelado`.

### Impacto tecnico

Backend:

- `backend/main.py`
- `backend/agent.py`
- `backend/world.py`
- `backend/runtime/thinker.py`
- `backend/storage/decision_log.py`

Frontend:

- `frontend/index.html`
- `frontend/main.js`
- `frontend/style.css`

### MVP

- 1 comando ativo por agente
- comando com expirar em N ticks
- modo `command`
- logar se a decisao veio de humano ou de autonomia
- botao "Liberar agente" para voltar ao comportamento normal

### Fase 2

- fila de comandos
- modo `suggestion` em vez de `command`
- comandos coletivos
- comparacao de obediencia por perfil/modelo

### Riscos

- comandos vagos demais
- conflitos com a autonomia do agente
- usuarios tentando acao impossivel

### Criterio de sucesso

- o agente recebe e processa comando sem quebrar o fluxo atual do `Thinker`
- o replay e o log indicam claramente quando houve intervencao humana

---

## F02 — Comparador A/B de Perfis e Torneios Automatizados

### Visao

Executar lotes de partidas entre combinacoes de perfis e gerar um relatorio comparativo real.

### Problema que resolve

- Hoje existe benchmark ao vivo, mas falta experimento sistematico.
- O projeto ainda nao entrega um fluxo forte de comparacao entre perfis em volume.

### Experiencia esperada

- Na `models.html` ou `dashboard.html`, o usuario seleciona perfis.
- Define quantidade de partidas, seeds e configuracao do mundo.
- O sistema roda os torneios em lote.
- Ao final, mostra tabela comparativa com:
  - win rate
  - score medio
  - sobrevida media
  - tokens medios
  - latencia
  - custo

### Impacto tecnico

Backend:

- `backend/runtime/tournament_runner.py`
- `backend/storage/session_store.py`
- `backend/storage/decision_log.py`

Frontend:

- `frontend/models.html`
- `frontend/dashboard.html`

### MVP

- comparar 2 a 4 perfis
- rodar N sessoes
- armazenar resultados agregados
- exportar CSV/JSON

### Fase 2

- seeds controladas
- relatorio por mapa/evento
- comparacao por tipo de objetivo

### Riscos

- execucoes longas em single-worker
- necessidade de serializar melhor os experimentos

### Criterio de sucesso

- gerar um relatorio comparativo reprodutivel sem precisar interpretar logs manualmente

---

## F03 — Inspector de Decisao por Agente

### Visao

Abrir um painel de inspecao que explique por que o agente fez o que fez.

### Problema que resolve

- Hoje da para ver a acao final, mas nao ha transparencia suficiente do processo.
- Falta observabilidade detalhada para debugging e tuning de perfis.

### Experiencia esperada

Ao clicar em um agente, ver:

- estado atual
- ultimas decisoes
- memoria relevante recuperada
- comando humano ativo, se existir
- prompt/contexto resumido
- resposta estruturada do modelo
- custo, latencia e uso de tokens

### Impacto tecnico

Backend:

- `backend/storage/decision_log.py`
- `backend/storage/memory_store.py`
- endpoints de leitura por agente/sessao

Frontend:

- `frontend/index.html`
- `frontend/main.js`

### MVP

- mostrar ultimas 5 decisoes
- mostrar memoria relevante usada no ultimo turno
- mostrar tokens e latencia

### Fase 2

- diff entre perfis
- playback da cadeia de pensamento estruturada
- heatmap de fatores decisorios

### Riscos

- payloads grandes no frontend
- vazar contexto demais e poluir a UI

### Criterio de sucesso

- o usuario consegue responder "por que esse agente fez isso?" sem abrir logs manuais

---

## F04 — Eventos Dinamicos da Ilha

### Visao

Adicionar eventos sistemicos que alteram o estado do mundo e forcam adaptacao dos agentes.

### Exemplos

- tempestade
- seca
- queda de suprimentos
- radio misterioso
- eclipse
- area contaminada
- bonus temporario de recursos

### Problema que resolve

- Hoje a ilha tem boa base sistemica, mas ainda pode ficar previsivel demais.
- Faltam gatilhos que gerem partidas mais variadas.

### Impacto tecnico

Backend:

- `backend/world.py`
- `backend/runtime/thinker.py`
- `backend/storage/replay_store.py`

Frontend:

- `frontend/index.html`
- `frontend/benchmark.js`

### MVP

- 3 a 5 eventos globais
- broadcast via WebSocket
- timeline destacando causa e efeito

### Fase 2

- eventos por regiao do mapa
- eventos em cadeia
- eventos disparados por performance dos agentes

### Riscos

- excesso de aleatoriedade
- dificuldade de balancear

### Criterio de sucesso

- as partidas passam a gerar estrategias mais diversas e replays mais interessantes

---

## F05 — Console de Intervencao ao Vivo

### Visao

Criar um painel admin para alterar o estado do mundo sem reiniciar a sessao.

### Casos de uso

- spawnar item
- spawnar zumbi
- mudar clima
- trocar perfil de um agente
- pausar/reiniciar torneio
- aplicar buff/debuff

### Problema que resolve

- Falta uma forma de manipular a simulacao para testes, demos e QA.

### Impacto tecnico

Backend:

- `backend/main.py`
- `backend/world.py`
- controle por `ADMIN_TOKEN`

Frontend:

- `frontend/index.html`
- talvez uma tela admin dedicada no futuro

### MVP

- painel simples com 5 a 8 acoes administrativas
- confirmacao visual e log do evento

### Fase 2

- presets de caos/teste
- macros admin
- console de script seguro

### Riscos

- abuso de endpoint admin
- UI poluida na tela principal

### Criterio de sucesso

- o operador consegue preparar cenarios de teste sem reiniciar o backend

---

## F06 — Temporadas e Ranking ELO por Perfil

### Visao

Transformar a competicao em ciclos persistentes com ranking formal.

### Problema que resolve

- O benchmark atual e forte no tempo real, mas falta camada de progressao historica.

### Experiencia esperada

- ranking por `profile_id`
- leaderboard por temporada
- medalhas, win streak, score medio, sobrevivencia media
- reset de temporada com historico preservado

### Impacto tecnico

Backend:

- `backend/storage/session_store.py`
- possivel tabela nova para temporadas

Frontend:

- `frontend/dashboard.html`

### MVP

- temporadas com data de inicio/fim
- ELO basico por partida
- pagina de ranking consolidado

### Fase 2

- ranking por mapa, evento ou modo
- selo de campeao por temporada

### Riscos

- formula de ELO injusta para partidas multiagente
- necessidade de calibrar peso por modo de jogo

### Criterio de sucesso

- o projeto ganha memoria competitiva real, nao apenas scoreboard de sessao

---

## F07 — Aliancas, Traicao e Reputacao Social

### Visao

Expandir a camada social para alem de `friendship`, com pactos explicitos e consequencias.

### Problema que resolve

- A simulacao social ainda pode ficar rasa perto do potencial do sistema.

### Componentes

- alianca formal
- promessa
- quebra de promessa
- inimigo declarado
- reputacao por comportamento

### Impacto tecnico

Backend:

- `backend/agent.py`
- `backend/runtime/memory.py`
- `backend/storage/memory_store.py`
- `backend/world.py`

Frontend:

- overlays e cards relacionais no modal do agente

### MVP

- alianças 1:1
- memoria de traicao
- bonus e penalidade social

### Fase 2

- faccoes
- diplomacia multiagente
- acordo de troca de recursos

### Riscos

- explodir a complexidade do estado
- tornar a explicacao dos vinculos confusa

### Criterio de sucesso

- o comportamento social fica observavelmente mais rico e menos aleatorio

---

## F08 — Missoes e Objetivos Individuais

### Visao

Dar objetivos secundarios a cada agente para diversificar comportamento e avaliacao.

### Exemplos

- construir abrigo
- manter 2 aliados vivos
- coletar 10 frutas
- dominar uma regiao
- vencer sem atacar

### Problema que resolve

- Hoje quase toda avaliacao gira em torno de sobrevivencia/score.
- Faltam metas que produzam estilos diferentes.

### Impacto tecnico

Backend:

- `backend/world.py`
- `backend/agent.py`
- `backend/runtime/thinker.py`

Frontend:

- HUD do agente
- dashboard com taxa de conclusao de missoes

### MVP

- catalogo de 5 a 8 missoes
- atribuicao na criacao do agente ou no inicio da sessao
- score bonus por conclusao

### Fase 2

- missoes encadeadas
- missoes secretas
- missoes por evento

### Riscos

- missoes mal balanceadas virarem "meta dominante"

### Criterio de sucesso

- agentes do mesmo perfil passam a agir de forma diferente em funcao do objetivo

---

## F09 — Editor Versionado de Perfis e Prompts

### Visao

Transformar `models.html` em um laboratorio de perfis versionados.

### Problema que resolve

- Hoje o catalogo existe, mas nao ha historia nem comparacao de variacoes de prompt/config.

### Capacidades desejadas

- versoes por perfil
- notas de alteracao
- clone de perfil
- rollback
- testes A/B entre versoes

### Impacto tecnico

Backend:

- `backend/runtime/profiles.py`
- possivel storage persistente de perfis custom

Frontend:

- `frontend/models.html`

### MVP

- criar versao de perfil
- salvar prompt/config associada
- marcar versao ativa

### Fase 2

- diffs entre versoes
- publicacao de preset validado
- import/export de perfis

### Riscos

- mistura entre perfis builtin e customizados
- necessidade de governanca de configuracao

### Criterio de sucesso

- tuning de perfil deixa de ser manual e passa a ser auditavel

---

## F10 — Economia, Crafting e Construcao

### Visao

Criar loops mais profundos de sobrevivencia e estrategia material.

### Problema que resolve

- O mundo atual ja tem recursos e inventario, mas ainda nao explora bem producao e progresso.

### Componentes

- receitas
- ferramentas
- abrigo
- fogueira
- garrafa/filtro
- armadilhas
- melhoria de casa

### Impacto tecnico

Backend:

- `backend/world.py`
- `backend/agent.py`
- validacao de acoes

Frontend:

- inventario
- estado de base/construcao

### MVP

- 3 receitas
- 2 estruturas construiveis
- efeitos concretos no score/vitals

### Fase 2

- arvore de crafting
- bases persistentes por sessao
- sabotagem e defesa

### Riscos

- alta complexidade de balanceamento
- aumento forte de regras no `world.py`

### Criterio de sucesso

- a economia cria estrategias novas sem tornar o sistema opaco demais

---

## F11 — Webhooks e Integracoes Externas Expandidas

### Visao

Evoluir o `WebhookManager` para uma camada real de integracao externa.

### Casos de uso

- avisar vitoria no Discord
- mandar fim de sessao para n8n
- exportar leaderboard
- acionar pipeline de analise

### Problema que resolve

- O sistema ja possui base de webhook, mas pouco explorada como plataforma.

### Impacto tecnico

Backend:

- `backend/storage/webhook_manager.py`
- novos eventos em `world.py` e `tournament_runner.py`

Frontend:

- configuracao no dashboard ou tela admin

### MVP

- ampliar eventos suportados:
  - `session_start`
  - `session_end`
  - `agent_dead`
  - `winner_declared`
  - `tournament_end`

### Fase 2

- retry configuravel
- historico de entregas
- webhook test button

### Riscos

- ruido excessivo
- seguranca de destino externo

### Criterio de sucesso

- terceiros conseguem reagir a eventos do BBBia sem acoplamento manual

---

## F12 — Modo Gincana

### Visao

Criar um modo de jogo orientado a desafios, em que os agentes precisam pegar objetos, cumprir tarefas e disputar quem executa melhor o objetivo proposto.

Em termos simples: "coloca alguns agentes, espalha objetos e define uma meta; a gente assiste quem faz melhor".

### Por que essa feature e forte

- transforma a ilha em uma arena de desafios objetivos
- aproxima o sistema de benchmark pratico
- cria partidas mais curtas, comparaveis e divertidas
- funciona muito bem para stream, demo e experimento

### Exemplos de gincanas

- coletar 5 frutas e voltar para casa
- encontrar 3 objetos especificos no mapa
- montar um kit: madeira + pedra + agua
- resgatar um item raro no centro e retornar vivo
- cumprir uma rota com checkpoints
- colaborar em dupla para concluir uma tarefa

### Como funcionaria

- o operador escolhe um template de gincana
- o mundo spawn objetos e condicoes especiais
- os agentes recebem o objetivo na inicializacao
- o scoreboard mede:
  - tempo para concluir
  - quantidade de passos
  - uso de tokens
  - erros
  - sobrevivencia
  - bonus por eficiencia

### Impacto tecnico

Backend:

- `backend/world.py`
- `backend/runtime/thinker.py`
- `backend/storage/session_store.py`
- `backend/runtime/tournament_runner.py`

Frontend:

- `frontend/index.html`
- `frontend/dashboard.html`
- possivel pagina dedicada no futuro

### MVP

- 2 a 3 tipos de gincana
- regras objetivas de vitoria
- scoreboard especifico do modo
- tela principal exibindo objetivo atual

### Fase 2

- gincanas cooperativas
- gincanas em equipes
- gincanas com fases
- editor de gincanas customizadas

### Riscos

- misturar demais o modo livre com o modo desafio
- regras mal definidas gerarem resultados ambiguos

### Criterio de sucesso

- o sistema consegue rodar partidas orientadas por objetivo com vencedor claro e replay interessante

---

## F13 — Modo Guerra de Faccoes

### Visao

Criar um modo competitivo em que dois times de agentes se enfrentam em uma arena da ilha, disputando eliminacoes, objetivos e supremacia do round.

Exemplo base:

- time A com 4 agentes de um perfil/modelo
- time B com 4 agentes de outro perfil/modelo
- cada lado tenta coletar recursos, se equipar e derrotar o outro

### Problema que resolve

- Falta um modo competitivo direto entre grupos de modelos.
- O benchmark atual compara agentes em um ecossistema aberto, mas ainda nao entrega bem o conceito de "time contra time".

### Experiencia esperada

- selecionar dois times
- escolher perfil dominante de cada faccao
- configurar tamanho da equipe, mapa e condicoes do round
- assistir ao conflito em tempo real
- ver placar por time e por individuo

### Impacto tecnico

Backend:

- `backend/world.py`
- `backend/runtime/tournament_runner.py`
- `backend/storage/session_store.py`

Frontend:

- `frontend/index.html`
- `frontend/dashboard.html`

### MVP

- 2 faccoes
- placar por equipe
- base inicial por lado
- condicao de vitoria por eliminacao ou score do round

### Fase 2

- series melhor de 3 / melhor de 5
- composicao mista de perfis por time
- mapas especificos para guerra

### Riscos

- combate ficar caotico demais sem objetivos secundarios
- rounds longos se nao houver criterio de encerramento claro

### Criterio de sucesso

- o sistema passa a comparar modelos em confrontos de equipe que sejam legiveis e reprodutiveis

---

## F14 — Sistema de Arremesso e Combate a Distancia

### Visao

Adicionar uma camada de combate baseada em projeteis improvisados e uso tatico de itens.

### Problema que resolve

- O modo guerra perde identidade se todo confronto for apenas aproximacao fisica.
- O projeto ainda nao explora bem itens como ferramentas ofensivas.

### Exemplos

- jogar pedra
- lancar garrafa
- usar item craftado como projetil
- arremessar objeto para interromper ou afastar inimigo

### Impacto tecnico

Backend:

- `backend/world.py`
- schema de acoes no runtime
- validacao de alcance, dano e consumo de item

Frontend:

- feedback visual de trajetoria/impacto
- timeline de combate

### MVP

- nova acao `throw_item`
- 2 ou 3 itens arremessaveis
- alcance, dano e precisao simples

### Fase 2

- cobertura e obstaculos
- status de stun/lentidao
- diferenca entre projeteis leves e pesados

### Riscos

- balanceamento ruim pode transformar o modo em spam de projetil
- exige visualizacao minimamente clara no frontend

### Criterio de sucesso

- o combate a distancia vira uma escolha estrategica real, nao apenas efeito cosmetico

---

## F15 — Papeis Taticos de Equipe

### Visao

Permitir que agentes dentro da mesma faccao assumam papeis distintos, mesmo usando o mesmo modelo base.

### Exemplos de papeis

- atacante
- defensor
- coletor
- suporte
- scout

### Problema que resolve

- Sem papeis, times com o mesmo perfil tendem a agir de modo parecido demais.
- Falta especializacao funcional dentro da guerra.

### Impacto tecnico

Backend:

- `backend/agent.py`
- `backend/runtime/thinker.py`
- configuracao de perfil/prompt por role

Frontend:

- exibir papel do agente no HUD e no dashboard

### MVP

- 3 papeis iniciais
- pequenos modificadores de comportamento e prioridade
- score por papel

### Fase 2

- sinergias entre papeis
- formacao automatica de equipe
- presets taticos completos

### Riscos

- papel virar override excessivo do modelo
- tuning demorado para diferenciar sem engessar

### Criterio de sucesso

- equipes do mesmo modelo deixam de ser clones comportamentais

---

## F16 — Controle de Territorio e Recursos de Guerra

### Visao

Adicionar zonas do mapa com valor estrategico, incentivando disputa por posicao e abastecimento.

### Problema que resolve

- Guerra sem territorio tende a virar confronto erratico.
- Falta objetivo intermediario entre spawn e eliminacao.

### Componentes

- areas de controle
- pontos de coleta de municao improvisada
- agua/curacao em regioes disputadas
- bonus de score por dominacao

### Impacto tecnico

Backend:

- `backend/world.py`
- `backend/storage/replay_store.py`

Frontend:

- overlays de territorio
- mini-indicadores de controle

### MVP

- 2 ou 3 zonas estrategicas
- pontos por ocupacao
- recursos especiais vinculados a area

### Fase 2

- captura progressiva
- estruturas defensivas
- zonas mutaveis por evento

### Riscos

- excesso de regras espaciais pode sobrecarregar o mundo base

### Criterio de sucesso

- o modo guerra passa a ter dinamica de mapa, nao apenas perseguicao

---

## F17 — Modo Economia Local

### Visao

Criar um modo de simulacao economica em que os agentes precisam sobreviver e prosperar praticando compra, venda, troca e abastecimento.

### Problema que resolve

- O projeto ainda explora pouco o potencial de agentes negociando recursos de sobrevivencia.
- Falta um modo em que a performance venha de estrategia comercial, nao apenas combate ou sobrevivencia direta.

### Experiencia esperada

- sessao com foco em mercado local
- agentes precisam coletar, precificar, vender e recomprar itens
- o vencedor pode ser quem acumula mais valor, cumpre mais contratos ou sustenta melhor seu estoque

### Impacto tecnico

Backend:

- `backend/world.py`
- `backend/agent.py`
- `backend/storage/session_store.py`

Frontend:

- `frontend/index.html`
- `frontend/dashboard.html`

### MVP

- moeda simples
- compra e venda de itens basicos
- score economico separado
- ranking por patrimonio e giro

### Fase 2

- bancos/caixas de mercado
- diferenca entre preco de compra e venda
- estrategias comerciais por agente

### Riscos

- se a economia for rasa demais, vira apenas coleta com outro nome

### Criterio de sucesso

- os agentes passam a competir tambem por eficiencia economica, nao so por sobrevivencia

---

## F18 — Mercado Dinamico com Oferta e Demanda

### Visao

Criar um sistema de precos variaveis com base em escassez, clima, consumo e eventos do mundo.

### Problema que resolve

- Sem variacao de preco, o modo economia fica estatico e pouco interessante.

### Exemplos

- agua sobe de preco na seca
- madeira sobe apos tempestade
- comida dispara quando muitos agentes estao com fome

### Impacto tecnico

Backend:

- `backend/world.py`
- modulo de mercado/precos
- persistencia historica opcional no `session_store`

Frontend:

- ticker de precos
- graficos de variacao no dashboard

### MVP

- 4 a 6 itens com preco dinamico
- recalculo periodico por tick ou janela
- historico basico de preco

### Fase 2

- choque de oferta
- arbitragem entre postos
- previsao e tendencia de mercado

### Riscos

- calibragem ruim gerar inflacao ou colapso permanente

### Criterio de sucesso

- o mercado passa a forcar agentes a decidir quando comprar, estocar e vender

---

## F19 — Contratos, Entregas e Reputacao Comercial

### Visao

Adicionar objetivos economicos formalizados por ordens de entrega e reputacao de confiabilidade comercial.

### Problema que resolve

- O modo economia precisa de metas objetivas alem do lucro puro.
- Falta mecanismo para medir consistencia de comportamento comercial.

### Exemplos

- entregar 3 aguas ate o tick X
- vender 5 frutas no posto central
- montar e entregar um kit de sobrevivencia

### Impacto tecnico

Backend:

- `backend/world.py`
- `backend/agent.py`
- `backend/storage/session_store.py`
- eventual extensao da memoria relacional

Frontend:

- painel de contratos ativos
- reputacao visivel por agente

### MVP

- contratos simples gerados pelo sistema
- expiracao por tempo
- reputacao sobe e desce por cumprimento ou falha

### Fase 2

- contratos entre agentes
- fraude, roubo e quebra de acordo
- reputacao comercial afetando precos e acesso

### Riscos

- sobreposicao excessiva com sistema de missoes se os conceitos nao forem separados

### Criterio de sucesso

- o modo economia ganha uma camada clara de compromisso, risco e confianca

---

## F20 — Guerra de Gangues: Conflito + Logistica

### Visao

Criar um modo hibrido em que faccoes competem ao mesmo tempo por combate, territorio, recursos e sustentabilidade logistica.

### Problema que resolve

- Guerra pura pode ficar superficial.
- Economia pura pode ficar passiva demais.
- O modo hibrido junta as duas dimensoes em um jogo mais completo e dramatico.

### Como funcionaria

- cada gangue possui base
- precisa coletar recursos, abastecer estoque e armar o time
- pode atacar, defender e sabotar
- vence por eliminacao, score total ou dominio sustentado

### Impacto tecnico

Backend:

- composicao de F13, F14, F16, F17 e F19

Frontend:

- scoreboard hibrido
- indicadores de time, estoque e territorio

### MVP

- 2 faccoes
- recursos compartilhados por equipe
- score por combate + logistica

### Fase 2

- mercado negro
- sabotagem de entrega
- alianças temporarias entre gangues

### Riscos

- e o modo mais complexo deste plano
- exige boa separacao entre regras de guerra e economia

### Criterio de sucesso

- o BBBia ganha um modo "premium" de alta rejogabilidade, util tanto para demo quanto para benchmark avancado

---

## Dependencias e Sinergias

Algumas features se fortalecem mutuamente:

- F01 + F03
  - comandos humanos ficam explicaveis pelo inspector
- F02 + F06
  - comparador A/B alimenta ranking e temporada
- F04 + F12
  - eventos dinamicos enriquecem as gincanas
- F04 + F13 + F16
  - eventos dinamicos deixam a guerra menos previsivel e mais dramatica
- F07 + F08
  - missoes e relacoes sociais se reforcam
- F09 + F02
  - perfis versionados podem ser comparados formalmente
- F10 + F17 + F18
  - crafting e economia se fortalecem quando o mercado reage ao mundo
- F12 + F19
  - gincanas de entrega e coleta podem virar contratos objetivos
- F13 + F14 + F15 + F16
  - guerra de faccoes so fica realmente rica quando ha projeteis, roles e territorio
- F17 + F18 + F19
  - modo economia local depende de mercado dinamico e reputacao comercial
- F13 + F17 + F20
  - guerra de gangues nasce da combinacao entre conflito e logistica
- F11 + todas
  - webhooks permitem automacao e observabilidade externa

---

## Roadmap Recomendado

### Ciclo A — Ferramentas de observacao e controle

1. F01 — Modo Comandante
2. F03 — Inspector de decisao
3. F05 — Console de intervencao

### Ciclo B — Benchmark competitivo

1. F02 — Comparador A/B
2. F06 — Temporadas e ELO
3. F09 — Perfis versionados

### Ciclo C — Gameplay mais rico

1. F04 — Eventos dinamicos
2. F08 — Missoes individuais
3. F07 — Aliancas e traicao
4. F10 — Economia e construcao

### Ciclo D — Modos especiais e novos game modes

1. F12 — Modo Gincana
2. F13 — Modo Guerra de Faccoes
3. F17 — Modo Economia Local

### Ciclo E — Profundidade de warfare e economy

1. F14 — Sistema de arremesso
2. F15 — Papeis taticos
3. F16 — Territorio e recursos de guerra
4. F18 — Mercado dinamico
5. F19 — Contratos e reputacao comercial
6. F20 — Guerra de Gangues

### Ciclo F — Integracao de plataforma

1. F11 — Integracoes externas para cobertura e automacao

---

## Roadmap por Game Mode

### `survival`

Modo base da plataforma.

Sequencia recomendada:

1. F01 — Modo Comandante
2. F03 — Inspector de decisao
3. F04 — Eventos dinamicos
4. F08 — Missoes individuais
5. F07 — Aliancas e reputacao
6. F10 — Economia/crafting

### `gincana`

Modo de desafio curto e comparavel.

Sequencia recomendada:

1. F12 — Modo Gincana
2. F02 — Comparador A/B
3. F04 — Eventos dinamicos
4. F19 — Contratos e entregas

### `warfare`

Modo de combate entre faccoes.

Sequencia recomendada:

1. F13 — Guerra de Faccoes
2. F14 — Arremesso e combate a distancia
3. F15 — Papeis taticos
4. F16 — Territorio e recursos de guerra

### `economy`

Modo de comercio e sobrevivencia economica.

Sequencia recomendada:

1. F17 — Economia Local
2. F18 — Mercado dinamico
3. F19 — Contratos e reputacao comercial
4. F10 — Crafting e construcao como aprofundamento material

### `hybrid`

Modo premium que combina conflito e logistica.

Sequencia recomendada:

1. F20 — Guerra de Gangues
2. F11 — Webhooks e integracoes para acompanhamento e automacao

---

## Recomendacao Final

Se a ideia for maximizar valor rapido sem perder coerencia tecnica, a melhor sequencia pratica e:

1. F01 — Modo Comandante
2. F03 — Inspector de decisao
3. F02 — Comparador A/B
4. F12 — Modo Gincana
5. F13 — Modo Guerra de Faccoes
6. F17 — Modo Economia Local
7. F04 — Eventos dinamicos

Essa ordem funciona bem porque:

- aproveita fortemente a arquitetura atual
- aumenta demonstracao, teste e benchmark logo no curto prazo
- cria tres frentes fortes de produto: observabilidade, desafio e modos competitivos
- prepara o terreno para warfare/economy sem baguncar o modo base

---

## Definicao de Sucesso do Plano

Este plano tera valido a pena se o BBBia evoluir de:

- simulador interessante com benchmark ao vivo

para:

- laboratorio competitivo de agentes
- ambiente de desafios e torneios comparaveis
- plataforma de observacao, controle e explicacao de comportamento
