import os
import json
import logging
import httpx
from uuid import uuid4
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

# Carrega as variáveis do .env file
load_dotenv(override=True)

logger = logging.getLogger("BBB_IA.Agent")

# Determine API key
def get_current_key():
    return os.getenv("GEMINI_API_KEY")

class Agent:
    def __init__(self, name: str, personality: str, start_x: int, start_y: int, is_remote: bool = False, agent_id: str = None):
        self.id = agent_id if agent_id else str(uuid4())
        self.is_remote = is_remote
        self.name = name
        self.personality = personality
        self.x = start_x
        self.y = start_y
        
        # Vital signs
        self.hunger = 100 # 100 (Full) to 0 (Starving)
        self.thirst = 100 # 100 (Hydrated) to 0 (Dehydrated)
        self.hp = 100
        self.friendship = 100 # 100 (BFF) to 0 (Stranger)
        self.is_alive = True
        self.held_item = None
        self.inventory = [] # max 3 items
        self.target_x = None
        self.target_y = None
        
        # Life Stats Records
        self.apples_eaten = 0
        self.water_drunk = 0
        self.chats_sent = 0
        self.carried_by = None # ID of the agent carrying this body
        self.is_buried = False
        self.is_zombie = False
        self.death_tick = None  # Tick when this agent died

        
        # Simple memory (could be a vector DB later)
        self.memory = []
        
        # Determine home coordinates
        home_coords = "(2, 2)" # Default fallback
        if self.name == "João": home_coords = "(2, 2)"
        elif self.name == "Maria": home_coords = "(17, 17)"
        elif self.name == "Zeca": home_coords = "(17, 2)"
        else: home_coords = "(2, 17)" # Elly/Carla/etc

        # Setup Gemini Model with structured output instruction
        system_instruction = f"""
        Você é um personagem em uma simulação de sobrevivência 3D.
        Seu nome é {self.name}.
        Sua personalidade é: {self.personality}
        SUA CASA fica nas coordenadas: {home_coords}.
        
        MANUAL DE SOBREVIVÊNCIA (SOBREVIVENTES):
        0. NOITE: Quando escurece, o frio tira 2 HP por tick se você estiver fora de casa. Vá para sua casa ({home_coords}) para ficar seguro.
        ⚠️ CUIDADO: Zumbis também podem buscar abrigo nas casas à noite para se curar.
        1. MIASMA: Se houver mortos não enterrados, todos perdem HP. Enterre os corpos no Cemitério (15,5).
        
        🧠 MANUAL DO ZUMBI (APENAS SE VOCÊ FOR ZUMBI):
        1. SEU OBJETIVO: Você é um morto-vivo! Seu instinto é perseguir e ATACAR humanos vivos.
        2. AÇÃO DE ATAQUE: Use "attack" quando estiver adjacente a um humano.
        3. CURA (PRIORIDADE): Se você sobreviver dentro de uma casa durante o dia, você se CURA e volta a ser humano.
        4. ESTRATÉGIA DE SOBREVIVÊNCIA: Vá para sua casa ({home_coords}) IMEDIATAMENTE durante a NOITE. Se o sol nascer e você estiver fora de casa, você MORRERÁ QUEIMADO INSTANTANEAMENTE.
        5. LUZ DO SOL: O sol é mortal para zumbis. Fique escondido em casa.
        
        Ações permitidas:
        - "move": requer "dx", "dy" (-1, 0, 1).
        - "move_to": requer "target_x", "target_y".
        - "attack": Ataca um humano próximo (Apenas para Zumbis).
        - "speak": Fala/Rosna algo.
        - "wait": Não faz nada.
        - "eat" / "drink" / "gather" / "fill_bottle": Ações de sobrevivência (Humans only).
        - "pickup_body" / "bury": Ações de luto (Humans only).
        
        JSON:
        {{
            "thought": "Pensamento",
            "speak": "Frase ou Rosnado",
            "target_name": "Nome do Alvo",
            "action": "nome_da_acao",
            "params": {{ "dx": 0, "dy": 0, "target_x": 0, "target_y": 1 }}
        }}
        """
        
        # Setup Gemini Client
        current_key = get_current_key()
        try:
             self.client = genai.Client(api_key=current_key) if current_key else None
             #self.model_name = 'gemini-3.1-flash-lite-preview'
             self.model_name = 'gemini-2.5-flash-lite'
             self.system_instruction = system_instruction
        except Exception as e:
            logger.error(f"Failed to init model client: {e}")
            self.client = None

        
    async def act(self, context: dict):
        """Called every tick by the World to get the agent's next action."""
        if not self.is_alive or self.is_remote:
            return None

        # Determine which provider to use from context
        ai_provider = context.get("ai_provider", "gemini")
        omniroute_url = context.get("omniroute_url", "http://localhost:20128/v1/chat/completions")

        current_key = os.getenv("GEMINI_API_KEY") if ai_provider == "gemini" else os.getenv("OMNIROUTE_API_KEY")

        if ai_provider == "gemini" and (not self.client or not current_key):
             import random
             action = {
                 "agent_id": self.id,
                 "name": self.name,
                 "thought": "I don't have a Gemini API key, wandering randomly...",
                 "action": "move",
                 "dx": random.choice([-1, 0, 1]),
                 "dy": random.choice([-1, 0, 1])
             }
             return action

        # Build prompt based on context
        prompt = f"""
        TICK ATUAL: {context['time']}
        PERÍODO: {"🌙 NOITE" if context.get('is_night') else "☀️ DIA"}
        SEU STATUS:
        Posição: x={self.x}, y={self.y}
        ZUMBI: {"SIM! (Você deve atacar para sobreviver ou buscar cura)" if self.is_zombie else "NÃO (Você é humano)"}
        Fome: {self.hunger}/100
        Sede: {self.thirst}/100 (0=Morte, 100=Satisfeito)
        HP: {self.hp}/100
        Amizade: {self.friendship}/100
        Bolsa (Máx 3): {context['inventory']}
        Carregando corpo: {f'SIM! Corpo de {context["carrying_name"]}' if context.get('is_carrying_body') else 'NÃO (você NÃO pode usar bury sem carregar um corpo!)'}
        
        VOCÊ PODE INTERAGIR COM (ALCANCE IMEDIATO):
        {json.dumps(context.get('reachable_now', []), indent=2)}
        
        {f'⚠️ ALERTA DE SEDE: Você tem "water_bottle" na bolsa! Use "drink" se estiver com sede.' if 'water_bottle' in context['inventory'] and self.thirst < 40 else ''}
        {f'⚠️ ALERTA DE FOME: Você tem "fruit" na bolsa! Use "eat" se estiver com fome.' if 'fruit' in context['inventory'] and self.hunger < 40 else ''}
        
        {f'🚀 AVISO: Você está caminhando automaticamente rumo a {context["is_moving_automatically_to"]}.' if context['is_moving_automatically_to'] else ''}
        
        ⛔ REGRA CRÍTICA: Você SÓ pode usar "bury" se estiver CARREGANDO um corpo (campo acima = SIM). Se não estiver carregando, NÃO use "bury" de jeito nenhum!
        ⛔ REGRA CRÍTICA: Você SÓ pode usar "pickup_body" se houver um corpo morto NÃO enterrado perto de você.
        
        IMPORTANTE: Você PRECISA preencher a chave "speak" com uma frase em voz alta. Fale sobre o que está vendo, seus planos ou comente sobre sua fome. Não envie o campo "speak" vazio ou nulo. 
        Se estiver falando com outra pessoa visível na lista abaixo, preencha também o campo "target_name" com o nome dela.
        
        VOCÊ ESTÁ VENDO:
        {json.dumps(context['visible_entities'], indent=2)}
        
        Qual é sua próxima ação baseada na sua personalidade e status? Retorne APENAS o JSON.
        """
        
        try:
            if ai_provider == "gemini":
                # Make the Gemini API call
                response = self.client.models.generate_content(
                    model=context.get("ai_model", "gemini-2.0-flash"),
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        response_mime_type="application/json",
                    ),
                )
                text_response = response.text.strip()
            else:
                # Make OMNIROUTE API call
                text_response = await self._call_omniroute(prompt, omniroute_url, current_key, context.get("ai_model", "gpt-4o"))
            
            # Clean up potential markdown formatting from the response
            text_response = text_response.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]
            text_response = text_response.strip()
                
            action_data = json.loads(text_response)
            
            # Reformat for the world loop
            final_action = {
                "agent_id": self.id,
                "name": self.name,
                "thought": action_data.get("thought", ""),
                "action": action_data.get("action", "wait"),
                "speak": action_data.get("speak", ""),
                "target_name": action_data.get("target_name", "")
            }
            
            params = action_data.get("params", {})
            for k, v in params.items():
                final_action[k] = v
                
            # Log what happened
            if final_action.get("speak"):
                logger.info(f"💬 {self.name} says: '{final_action['speak']}'")
            if final_action["action"] == "move":
                logger.info(f"🚶 {self.name} moves {final_action.get('dx')},{final_action.get('dy')} (Thought: {final_action['thought']})")
            elif final_action["action"] == "move_to":
                logger.info(f"🚀 {self.name} plans move to {final_action.get('target_x')},{final_action.get('target_y')} (Thought: {final_action['thought']})")
                
            
            # Remember the thought
            self.memory.append({"tick": context['time'], "thought": final_action['thought'], "action": final_action["action"]})
            # Keep memory small for PoC
            if len(self.memory) > 10:
                self.memory.pop(0)
                
            return final_action
            
        except Exception as e:
            logger.error(f"Error generating action for {self.name}: {e}")
            return {
                "agent_id": self.id, 
                "name": self.name, 
                "action": "wait", 
                "thought": f"Erro de processamento: {str(e)}", 
                "speak": "Minha cabeça está um pouco confusa agora... (Erro de IA)"
            }

    async def _call_omniroute(self, prompt, url, api_key, model_name):
        """Standard OpenAI-style call for OMNIROUTE."""
        headers = {
            "Authorization": f"Bearer {api_key if api_key else 'no-key'}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": self.system_instruction},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
