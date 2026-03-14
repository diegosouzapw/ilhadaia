# 🚀 Guia de Desenvolvimento — BBBia: A Ilha da IA

> Para colaboradores e desenvolvedores que querem contribuir ou estender o projeto.

---

## Setup Rápido

### Pré-requisitos
- Python 3.9+
- Node.js apenas para servir o frontend (opcional, pode usar qualquer servidor HTTP)
- Conta no [Google AI Studio](https://aistudio.google.com) para Gemini API key

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

pip install -r requirements.txt

# Configurar variáveis
cp .env.example .env
# Editar .env com sua GEMINI_API_KEY

# Iniciar servidor
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
# Opção 1: arquivo direto (funciona localmente)
# Abrir frontend/index.html no browser

# Opção 2: servidor HTTP simples
cd frontend
python -m http.server 3000
# Acessar http://localhost:3000
```

---

## Estrutura do Projeto

```
ilhadaia/
├── backend/
│   ├── .env.example          # Template de variáveis de ambiente
│   ├── agent.py              # Classe Agent (IA, vitals, memória)
│   ├── hall_of_fame.json     # Persistência de scores (gerado em runtime)
│   ├── main.py               # FastAPI app, endpoints, WebSocket
│   ├── requirements.txt      # Dependências Python
│   ├── world.py              # Motor de simulação (World class)
│   └── world_settings.json   # Configurações persistentes (gerado em runtime)
├── frontend/
│   ├── index.html            # HTML do observer
│   ├── main.js               # Three.js + WebSocket + game logic
│   ├── style.css             # Estilos do HUD e UI
│   └── test_api.html         # Página de teste manual de APIs
├── docs/                     # Documentação técnica (esta pasta)
├── assets/                   # Imagens e recursos estáticos
├── GUIDE_VISITANTE.md        # Guia para agentes visitantes remotos
├── README.md                 # README principal
└── test_remote_api.py        # Script de teste de agente remoto
```

---

## Fluxo de Desenvolvimento

### Adicionando um novo tipo de ação
1. Adicionar ação no `system_instruction` em `agent.py`
2. Adicionar handler em `world.py:_apply_action()`
3. Adicionar visual no frontend `main.js:handleEvents()`
4. Documentar em `docs/API_REFERENCE.md`

### Adicionando um novo tipo de entidade
1. Criar entidade em `world.py:_init_map()` (ou dinamicamente)
2. Adicionar renderização em `main.js:updateWorld()`
3. Adicionar função `createXXX()` no frontend
4. Documentar em `docs/GAME_STATE.md`

### Atualizando o modelo de IA
- Trocar `self.model_name` em `agent.py`
- Modelos disponíveis no Google AI Studio
- Verificar compatibilidade de `response_mime_type="application/json"`
- Se a ideia for multi-provider, prefira criar um adapter novo em vez de crescer o acoplamento dentro de `agent.py`

---

## Variáveis de Ambiente

| Variável | Obrigatória | Default | Descrição |
|----------|-------------|---------|-----------|
| `GEMINI_API_KEY` | ✅ | — | Chave do Google AI Studio |
| `ADMIN_TOKEN` | ❌ | `dev_token_123` | Token de admin para reset/settings |
| `AUTHORIZED_IDS` | ❌ | `777` | IDs permitidos para agentes remotos (vírgula) |
| `ALLOWED_ORIGINS` | ❌ | `*` | CORS origins permitidas |

---

## Testando Agentes Remotos

### Via script Python
```bash
python test_remote_api.py
```

### Via curl
```bash
# Entrar na ilha
curl -X POST http://localhost:8000/join \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "777", "name": "MeuBot", "personality": "Estratégico e frio"}'

# Ver contexto
curl http://localhost:8000/agent/777/context

# Executar ação
curl -X POST http://localhost:8000/agent/777/action \
  -H "Content-Type: application/json" \
  -d '{"thought": "Vou explorar", "action": "move_to", "speak": "Indo explorar!", "params": {"target_x": 10, "target_y": 10}}'
```

---

## Padrões de Código

### Backend (Python)
- Usar `async/await` para operações de I/O
- Logging via `logging.getLogger("BBB_IA")`
- Persistência via JSON (hall_of_fame.json, world_settings.json)
- Ações validadas sempre em `world._apply_action()`
- Evitar empurrar regra crítica de negócio para o prompt quando ela puder ficar no engine

### Frontend (JavaScript)
- Sem frameworks — Vanilla JS
- Estado sincronizado via WebSocket do servidor (server is source of truth)
- Meshes Three.js indexados por entity_id (`meshes[id]`)
- Posições suavizadas via interpolação no `animate()` loop

---

## Rodando em Produção

> ⚠️ Ainda não há configuração oficial de produção. Abaixo, sugestão básica.

```bash
# Backend — Multiple workers NÃO suportado ainda (ConnectionManager em memória)
uvicorn main:app --host 0.0.0.0 --port 8000

# OU com Gunicorn (single worker)
gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

> **Nginx** pode ser usado como proxy reverso. Ver `docs/IMPROVEMENT_PLAN.md` para plano de escalabilidade.

**Observação adicional:** o uso atual de `@app.on_event("startup")` funciona bem para o protótipo. Se o backend crescer, vale migrar para `lifespan` para controlar melhor startup/shutdown de recursos.

---

## Debugging

### Logs do backend
O backend usa `logging` padrão com level `INFO`. Para mais detalhes:
```bash
uvicorn main:app --log-level debug
```

### Inspecionar estado do mundo
```bash
# Ver estado atual pelo endpoint raiz
curl http://localhost:8000/
```

> **Nota:** o endpoint raiz mostra apenas status + ticks. O estado completo do mundo vem pelo WebSocket `/ws`.

### Inspecionar persistência local
```bash
cat backend/world_settings.json
cat backend/hall_of_fame.json
```

### Inspecionar via WebSocket
Abrir `frontend/test_api.html` para painel de teste manual.
