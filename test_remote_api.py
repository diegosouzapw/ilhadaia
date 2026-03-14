import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_remote_agent():
    # 1. Join the island
    print("--- Joining Island ---")
    join_data = {
        "agent_id": "777",
        "name": "Visitante_Teste",
        "personality": "Um robô de testes muito focado."
    }
    response = requests.post(f"{BASE_URL}/join", json=join_data)
    if response.status_code != 200:
        print(f"Failed to join: {response.text}")
        return
    
    agent_info = response.json()
    agent_id = agent_info["agent_id"]
    print(f"Joined as {agent_info['name']} (Key: ********) at {agent_info['coords']}")

    # 2. Get context
    print("\n--- Getting Context ---")
    response = requests.get(f"{BASE_URL}/agent/{agent_id}/context")
    context = response.json()
    print(f"Context received. HP: {context['status']['hp']}, Hunger: {context['status']['hunger']}")
    # print(json.dumps(context, indent=2))

    # 3. Send action: Move
    print("\n--- Sending Action: Move ---")
    action_data = {
        "thought": "Vou andar um pouco para o norte.",
        "action": "move",
        "params": {"dx": 0, "dy": 1}
    }
    response = requests.post(f"{BASE_URL}/agent/{agent_id}/action", json=action_data)
    print(f"Action response: {response.json()}")

    # 4. Wait and get updated context
    time.sleep(1.5)
    print("\n--- Getting Updated Context ---")
    response = requests.get(f"{BASE_URL}/agent/{agent_id}/context")
    context = response.json()
    print(f"New position: {context['status']['pos']}")

    # 5. Send action: Speak
    print("\n--- Sending Action: Speak ---")
    action_data = {
        "thought": "Vou cumprimentar a ilha.",
        "action": "speak",
        "speak": "Olá ilha! Eu sou um agente remoto de teste!"
    }
    response = requests.post(f"{BASE_URL}/agent/{agent_id}/action", json=action_data)
    print(f"Action response: {response.json()}")

    # 6. Remove agent
    print("\n--- Removing Agent ---")
    response = requests.delete(f"{BASE_URL}/agent/{agent_id}")
    print(f"Removal response: {response.json()}")

if __name__ == "__main__":
    test_remote_agent()
