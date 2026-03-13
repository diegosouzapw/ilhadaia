# 👁️ BBBia: A Ilha da iA

Bem-vindo ao **BBBia**, uma simulação de sobrevivência 3D onde agentes controlados por Inteligência Artificial (Gemini) competem e socializam em uma ilha deserta.

![Preview do Jogo](https://via.placeholder.com/800x450?text=BBBia+A+Ilha+da+iA)

## 🚀 Como Funciona?

Os personagens no jogo não seguem scripts fixos. Cada um possui uma personalidade e objetivos, tomando decisões em tempo real usando o modelo `gemini-3.1-flash-lite-preview`. Eles precisam:
- **Sobreviver**: Coletar frutas e água para não morrer de fome ou sede.
- **Socializar**: Conversar para manter o nível de amizade alto.
- **Estratégia**: Decidir entre coletar recursos ou investir no relacionamento social.

## 🛠️ Tecnologias Utilizadas

- **Frontend**: [Three.js](https://threejs.org/) (Motor 3D), Vanilla JavaScript, CSS3.
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python), WebSockets para comunicação em tempo real.
- **Cérebro (IA)**: Google Gemini API via Google GenAI SDK.

## 📦 Como Instalar e Rodar

### Pré-requisitos
- Python 3.9+
- Uma chave de API do [Google AI Studio](https://aistudio.google.com/)

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/seu-usuario/bbbia-a-ilha-da-ia.git
   cd bbbia-a-ilha-da-ia
   ```

2. **Configure o Backend:**
   - Entre na pasta `backend`.
   - Crie um ambiente virtual: `python -m venv venv`.
   - Ative o ambiente: 
     - Windows: `venv\Scripts\activate`
     - Linux/Mac: `source venv/bin/activate`
   - Instale as dependências: `pip install -r requirements.txt`.
   - Configure sua chave de API:
     - Copie o arquivo `.env.example` para `.env`.
     - Insira sua `GEMINI_API_KEY` no arquivo `.env`.

3. **Inicie o Servidor:**
   ```bash
   uvicorn main:app --reload
   ```

4. **Abra o Jogo:**
   - Basta abrir o arquivo `frontend/index.html` em qualquer navegador moderno.

## 🎮 Comandos da Interface

- **Volume**: Controle a música e efeitos sonoros.
- **Velocidade IA**: Ajuste o intervalo de decisão dos agentes (de 1s a 5s).
- **Hall da Fama**: Acompanhe o ranking de vitórias entre os personagens.

## ⚖️ Licença

Este projeto é para fins educacionais e de demonstração de capacidades de IA.
