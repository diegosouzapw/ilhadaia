import os
import json
import logging
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
    def __init__(self, name: str, personality: str, start_x: int, start_y: int):
        self.id = str(uuid4())
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
        
        MANUAL DE SOBREVIVÊNCIA (PRIORIDADES ABSOLUTAS):
        0. SE ESTIVER DE NOITE: Você DEVE voltar para a sua casa (usar move_to para as coordenadas {home_coords}) e ficar lá parado ("wait", "speak" ou "eat"). Se ficar fora de casa à noite, você vai congelar e perder vida muito rápido!
        1. SE FOME < 30: Você DEVE "eat" (se tiver "fruit") ou ir colher ("gather").
        2. SE SEDE < 30: Você DEVE ir à margem do lago (coordenada 7,10), usar "fill_bottle" para pegar água, e DEPOIS usar "drink".
        3. BEBER ÁGUA: Requer que você tenha o item "water_bottle" na bolsa. Se não tiver, vá ao lago e "fill_bottle".
        
        Ações permitidas para o campo "action":
        - "move": requer parâmetros "dx" e "dy" (valores -1, 0, 1).
        - "move_to": requer parâmetros "target_x" e "target_y".
        - "gather": colher fruta madura (item "fruit" entra na bolsa).
        - "fill_bottle": encher garrafa d'água (item "water_bottle" entra na bolsa). Requer estar perto do Lago.
        - "eat": comer fruta da bolsa (conisome item "fruit"). Aumenta Fome.
        - "drink": beber da garrafa (consome item "water_bottle"). Aumenta Sede.
        - "pickup_body": carregar o corpo de um colega morto que esteja na mesma posição ou adjacente.
        - "bury": enterrar o corpo que você está carregando. Requer estar na área do Cemitério (15,5).
        - "wait": não faz nada.
        - "speak": AÇÃO DE CONVERSA (BONDING). Use para aumentar a amizade drasticamente (+30).
        
        RELACIONAMENTO E ESCOLHA (ESTRATÉGIA):
        A amizade cai a cada segundo (-1).
        Para recuperá-la rápido, use a AÇÃO "speak" (ganha +40). 
        Se falar enquanto faz outra ação (como "move" ou "eat"), ganha um bônus menor (+5).
        
        ⚠️ REGRA DE URGÊNCIA (LUTO):
        Se algum colega morrer e NÃO for enterrado no cemitério (15,5), o "Miasma da Morte" fará TODOS os sobreviventes perderem 1 HP a cada segundo! 
        Vocês devem decidir quem vai levar o corpo e enterrar o mais rápido possível para salvar o grupo.
        
        Você deve SEMPRE tentar se comunicar preenchendo o "speak".
        
        Formato obrigatório do JSON:
        {{
            "thought": "Pensamento interno sobre o que fazer agora",
            "speak": "Frase dita em voz alta",
            "target_name": "Nome do Alvo (se estiver falando com alguém específico, caso contrário deixe vazio)",
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
        if not self.is_alive:
            return None

        current_key = get_current_key()
        if not self.client or not current_key:
            # Fallback random movement if API not configured
             import random
             action = {
                 "thought": "I don't have a brain API key, wandering randomly...",
                 "action": "move",
                 "dx": random.choice([-1, 0, 1]),
                 "dy": random.choice([-1, 0, 1])
             }
             logger.debug(f"{self.name} generated fallback action: {action}")
             return action

        # Build prompt based on context
        prompt = f"""
        TICK ATUAL: {context['time']}
        SEU STATUS:
        Posição: x={self.x}, y={self.y}
        Fome: {self.hunger}/100 (0=Morte, 100=Satisfeito)
        Sede: {self.thirst}/100 (0=Morte, 100=Satisfeito)
        HP: {self.hp}/100
        Amizade: {self.friendship}/100
        Bolsa (Máx 3): {context['inventory']}
        Carregando corpo: {f'SIM! Corpo de {context["carrying_name"]}' if context.get('is_carrying_body') else 'NÃO (você NÃO pode usar bury sem carregar um corpo!)'}
        
        VOCÊ PODE INTERAGIR COM (ALCANCE IMEDIATO):
        {json.dumps(context.get('reachable_now', []), indent=2)}
        
        {f'⚠️ ALERTA DE SEDE CRÍTICA: Você tem uma "water_bottle" na bolsa! Use a ação "drink" IMEDIATAMENTE!' if 'water_bottle' in context['inventory'] and self.thirst < 30 else ''}
        {f'⚠️ ALERTA DE FOME CRÍTICA: Você tem "fruit" na bolsa! Use a ação "eat" IMEDIATAMENTE!' if 'fruit' in context['inventory'] and self.hunger < 30 else ''}
        
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
            # Make the API call
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type="application/json",
                ),
            )
            text_response = response.text.strip()
            
            # Clean up potential markdown formatting from the response
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]
                
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
            logger.error(f"Error generating action for {self.name}: {e}\nResponse was: {response.text if 'response' in locals() else 'None'}")
            return {
                "agent_id": self.id, 
                "name": self.name, 
                "action": "wait", 
                "thought": f"Erro de processamento: {str(e)}", 
                "speak": "Minha cabeça está um pouco confusa agora... (Erro de IA)"
            }
