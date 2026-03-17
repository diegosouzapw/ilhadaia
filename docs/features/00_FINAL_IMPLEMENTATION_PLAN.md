# Plano Final de Implementacao - BBBia

## Escopo deste documento

Este documento consolida o planejamento final de implementacao para os modos `survival`, `gincana`, `warfare` e `economy`, com foco em execucao orientada a fases, criterios de aceite verificaveis e governanca tecnica para reduzir retrabalho.

Objetivos principais:

- organizar a execucao em fases com dependencias explicitas
- tornar o desenvolvimento rastreavel por task documental
- garantir que expansao de mapa e objetos por modo seja parte da base, nao um ajuste tardio
- preservar compatibilidade com o runtime atual baseado em `profile_id` + `Thinker`

## Decisoes estruturais obrigatorias

1. Toda sessao deve declarar `game_mode` explicitamente.
2. O mundo deve suportar mapa maior que `20x20` como baseline de desenvolvimento.
3. Cada modo precisa ter matriz propria de objetos e regras de spawn.
4. Toda feature deve ter task tecnica dedicada em `docs/features/Fxx_*.md`.
5. O progresso deve ser atualizado no checklist central antes de cada merge para `main`.

## Fase 0 - Fundacao tecnica do mundo ampliado

### Objetivo da fase

Estabelecer uma base de mundo escalavel para suportar os proximos modos sem fragilizar o render no navegador e sem hardcode de coordenadas fixas do mapa `20x20`.

### Entregas obrigatorias

- map size padrao aumentado para `32x32`
- leitura de tamanho por configuracao (`WORLD_SIZE`)
- landmarks dinamicos (casas, lago, cemiterio) derivados do tamanho atual
- frontend preparado para renderizar mapa maior com camera/fog/shadow proporcionais
- documentacao de requisitos de performance para navegadores desktop

### Criterios de aceite da fase

- backend inicia sem erro com `WORLD_SIZE=32`
- frontend renderiza sessao completa sem clipping visual grosseiro
- casas, lago, recursos e cemiterio aparecem em posicoes coerentes em `32x32`
- pathfinding continua funcional com o mesmo algoritmo BFS atual

## Matriz de tamanho de mapa por modo

- `survival`: `32x32` baseline
- `gincana`: `28x28` a `36x36` conforme template
- `warfare`: `40x40` recomendado para suportar faccoes e zonas
- `economy`: `36x36` recomendado para rotas de coleta/mercado
- `hybrid` (guerra de gangues): `44x44` recomendado para conflito + logistica

Regra operacional:

- `32x32` vira configuracao padrao para desenvolvimento local
- tamanhos maiores entram por feature flag de modo, com validacao de FPS no navegador

## Matriz de objetos por modo

### Survival

- `tree`, `stone`, `water`, `house`, `cemetery`, `dropped_fruit`
- foco em sobrevivencia, memoria e social

### Gincana

- todos de `survival`
- objetos de objetivo: `checkpoint`, `artifact`, `delivery_marker`
- foco em tempo, eficiencia e cumprimento de objetivo

### Warfare

- todos de `survival`
- objetos de combate: `throwable_stone`, `throwable_bottle`, `ammo_cache`, `cover`
- objetos de territorio: `control_zone`, `team_base`, `supply_crate`

### Economy

- todos de `survival`
- objetos economicos: `market_post`, `trade_order`, `contract_item`, `storage_box`
- suporte a precificacao dinamica por item

### Hybrid (guerra de gangues)

- composicao de `warfare` + `economy`
- adiciona `black_market`, `sabotage_target`, `team_inventory_depot`

## Fases finais de implementacao

### Fase 1 - Observabilidade e controle do agente

Features:

- F01, F03, F05

Saidas:

- modo comandante
- inspector de decisao
- console de intervencao admin

### Fase 2 - Benchmark formal

Features:

- F02, F06, F09

Saidas:

- comparador A/B automatizado
- temporadas e ranking
- versionamento de perfis e prompts

### Fase 3 - Gameplay vivo no modo base

Features:

- F04, F08, F07

Saidas:

- eventos dinamicos
- missoes individuais
- reputacao social e aliancas

### Fase 4 - Modo Gincana

Features:

- F12

Saidas:

- templates de desafio
- scoreboard especializado
- metricas por objetivo

### Fase 5 - Modo Warfare

Features:

- F13, F14, F15, F16

Saidas:

- guerra de faccoes
- combate a distancia por objetos
- papeis taticos
- controle de territorio

### Fase 6 - Modo Economy

Features:

- F17, F10, F18, F19

Saidas:

- economia local
- camada de crafting e construcao integrada ao ciclo economico
- oferta e demanda dinamica
- contratos e reputacao comercial

### Fase 7 - Modo Hybrid premium

Features:

- F20

Saidas:

- guerra de gangues (conflito + logistica)

### Fase 8 - Integracao externa e automacao

Features:

- F11

Saidas:

- webhooks ampliados
- integração com observabilidade externa

## Padrao operacional por task

Toda task de feature em `docs/features/Fxx_*.md` deve ser seguida com o mesmo rito:

1. ler o documento da feature antes de codar
2. executar checklist tecnico do arquivo
3. registrar alteracoes de schema/API quando houver
4. validar criterios de aceite da feature
5. atualizar `docs/features/CHECKLIST.md`

## Mapa ampliado ja aplicado na base

Este planejamento assume mundo maior como fundacao ativa:

- backend com tamanho de mapa padrao em `32`
- landmarks calculados de forma dinamica
- frontend com camera/fog/sombra escaladas para mapa maior

## Riscos principais e mitigacoes

- risco: degradacao de FPS com mapas grandes
- mitigacao: aplicar limites por modo e validar FPS minimo por ambiente

- risco: regras de objetos crescerem sem governanca
- mitigacao: manter matriz de objetos por modo e factory de spawn dedicada

- risco: colisao entre logica antiga e nova
- mitigacao: migrar hardcodes para coordenadas derivadas do tamanho do mundo

## Definicao de pronto global

O plano final sera considerado implementado quando:

- todas as features F01..F20 tiverem task documentada e checklist rastreavel
- cada modo tiver requisitos de mapa e objetos claramente implementados
- `survival` e `gincana` estiverem estaveis em mapa maior no navegador
- `warfare` e `economy` tiverem versao MVP operacional
- dashboard consolidar comparacao entre modos e perfis
