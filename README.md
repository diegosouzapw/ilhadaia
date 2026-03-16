# 👁️ BBBia: A Ilha da iA

Bem-vindo ao **BBBia**, uma simulação de sobrevivência 3D onde agentes controlados por Inteligência Artificial (Gemini) competem e socializam em uma ilha deserta.

![Preview do Jogo](./assets/hero.png)

### 📸 Gameplay em Tempo Real
![Simulação da Ilha](./assets/ilhadaia.png)

## 🚀 Como Funciona?

Os personagens no jogo não seguem scripts fixos. Cada um possui uma personalidade e objetivos, tomando decisões em tempo real usando o modelo Gemini. Eles precisam:

- **Sobreviver**: Coletar frutas e água para não morrer de fome ou sede.
- **Socializar**: Conversar para manter o nível de amizade alto.
- **Ciclo Dia/Noite**: 
  - **Frio Mortal**: Durante a noite, quem estiver fora de casa perde 1 HP/segundo. Os NPCs precisam correr para seus lares!
  - **Maldição Zumbi**: Se um NPC morrer e não for enterrado, ele pode se levantar à noite como um **Zumbi**.
  - **Desintegração Solar**: Zumbis que ficarem expostos ao sol durante o dia viram pó.
  - **Cura Milagrosa**: Se um zumbi sobreviver escondido dentro de uma casa por 24h, ele volta a ser humano!

## 🛠️ Tecnologias Utilizadas

- **Frontend**: [Three.js](https://threejs.org/) (Motor 3D), Vanilla JavaScript, CSS3.
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python), WebSockets para comunicação em tempo real.
- **Cérebro (IA)**: Google Gemini API via Google GenAI SDK ou qualquer provedor compatível com OpenAI (via OMNIROUTE).
- **Configurações Dinâmicas**: Menu de configurações (engrenagem) para trocar provedor, modelo e URL em tempo real.

## 📦 Como Instalar e Rodar

### Pré-requisitos
- Python 3.9+
- Uma chave de API do [Google AI Studio](https://aistudio.google.com/)

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/inteligenciamilgrau/ilhadaia.git
   cd ilhadaia
   ```

2. **Configure o Backend:**
   - Entre na pasta `backend`.
   - Crie um ambiente virtual: `python -m venv venv`.
   - Ative o ambiente (`venv\Scripts\activate` no Windows).
   - Instale as dependências: `pip install -r requirements.txt`.
   - Configure sua chave de API no arquivo `.env`.

3. **Inicie o Servidor:**
   ```bash
   uvicorn main:app --reload
   ```

4. **Abra o Jogo:**
   - Abra o arquivo `frontend/index.html` no seu navegador.

## ⚖️ Licença

Este projeto é para fins educacionais e de demonstração de capacidades de IA.
