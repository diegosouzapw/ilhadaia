"""
T12 — Testes Unitários do Engine BBBia.

Cobertura:
- runtime/schemas.py (ActionDecision)
- runtime/memory.py (AgentMemory)
- runtime/adapters/base.py (AIResponse)
- runtime/profiles.py (get_profile, list_profiles)
- storage/decision_log.py (DecisionLog)
- storage/session_store.py (SessionStore)

Execute com: pytest backend/tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
import json
import tempfile
import sqlite3
import pytest
import importlib


# ══════════════════════════════════════════════════════════════
# T11 — ActionDecision Schema
# ══════════════════════════════════════════════════════════════

class TestActionDecision:
    def setup_method(self):
        from runtime.schemas import ActionDecision
        self.ActionDecision = ActionDecision

    def test_valid_action_parsed(self):
        d = self.ActionDecision.from_dict({"action": "move", "speak": "Olá", "thought": "Vou explorar"})
        assert d.action == "move"
        assert d.speak == "Olá"
        assert d.thought == "Vou explorar"

    def test_invalid_action_coerced_to_wait(self):
        d = self.ActionDecision.from_dict({"action": "fly", "speak": ""})
        assert d.action == "wait"

    def test_invalid_intent_coerced_to_survive(self):
        d = self.ActionDecision.from_dict({"action": "move", "intent": "dance"})
        assert d.intent == "survive"

    def test_speech_alias(self):
        """Suporta 'speech' como alias de 'speak'."""
        d = self.ActionDecision.from_dict({"action": "speak", "speech": "Oi!", "thought": ""})
        assert d.speak == "Oi!"

    def test_empty_dict_becomes_wait(self):
        d = self.ActionDecision.from_dict({})
        assert d.action == "wait"
        assert d.intent == "survive"

    def test_to_world_action_format(self):
        d = self.ActionDecision.from_dict({
            "action": "attack", "speak": "", "thought": "ataque", "target_name": "Maria"
        })
        world = d.to_world_action("agent-1", "João")
        assert world["agent_id"] == "agent-1"
        assert world["name"] == "João"
        assert world["action"] == "attack"
        assert world["target_name"] == "Maria"

    def test_is_valid(self):
        valid = self.ActionDecision.from_dict({"action": "eat"})
        invalid = self.ActionDecision.from_dict({"action": "teleport"})
        assert valid.is_valid()
        assert invalid.action == "wait"  # coercido para wait, que é válido

    def test_thought_max_length_raises(self):
        """Pydantic V2 rejeita strings acima de max_length (comportamento correto)."""
        import pytest
        from pydantic import ValidationError
        long_thought = "x" * 1000
        with pytest.raises(ValidationError):
            self.ActionDecision(thought=long_thought, speak="", action="wait")

    def test_thought_within_limit_works(self):
        d = self.ActionDecision(thought="x" * 499, speak="", action="wait")
        assert len(d.thought) == 499

    def test_schema_prompt_contains_all_actions(self):
        schema = self.ActionDecision.get_json_schema_prompt()
        for action in ["move", "attack", "speak", "wait", "eat", "drink"]:
            assert action in schema


# ══════════════════════════════════════════════════════════════
# T10 — AgentMemory 4 Camadas
# ══════════════════════════════════════════════════════════════

class TestAgentMemory:
    def setup_method(self):
        from runtime.memory import AgentMemory
        self.mem = AgentMemory()

    def test_short_term_add_and_get(self):
        self.mem.add_short_term(tick=1, action="move", thought="Vou E", result="ok")
        assert len(self.mem.short_term) == 1
        assert self.mem.short_term[0].action == "move"

    def test_short_term_max_size(self):
        for i in range(20):
            self.mem.add_short_term(tick=i, action="wait")
        assert len(self.mem.short_term) == 20  # max 20

    def test_episodic_add(self):
        self.mem.add_episodic(5, "attack", "João atacou Maria", ["Maria"])
        assert len(self.mem.episodic) == 1
        assert self.mem.episodic[0].event_type == "attack"
        assert "Maria" in self.mem.episodic[0].agents_involved

    def test_episodic_max_size(self):
        for i in range(60):
            self.mem.add_episodic(i, "win", f"evento {i}")
        assert len(self.mem.episodic) == 50

    def test_relational_update(self):
        self.mem.update_relation("Maria", +0.5, tick=10, note="ajudou")
        self.mem.update_relation("Maria", +0.3, tick=11)
        r = self.mem.get_relation("Maria")
        assert r is not None
        assert r.opinion == pytest.approx(0.8)
        assert r.interactions == 2

    def test_relational_clamped(self):
        self.mem.update_relation("Zeca", +1.5)
        r = self.mem.get_relation("Zeca")
        assert r.opinion <= 1.0

    def test_relational_clamped_negative(self):
        self.mem.update_relation("Elly", -2.0)
        r = self.mem.get_relation("Elly")
        assert r.opinion >= -1.0

    def test_to_prompt_context_has_sections(self):
        self.mem.add_short_term(1, "eat")
        self.mem.add_episodic(2, "death", "alguém morreu")
        self.mem.update_relation("João", 0.2)
        ctx = self.mem.to_prompt_context()
        assert "MEMÓRIA RECENTE" in ctx
        assert "EVENTOS MARCANTES" in ctx
        assert "PERCEPÇÃO" in ctx

    def test_to_dict_serializable(self):
        self.mem.add_short_term(1, "move")
        self.mem.add_episodic(2, "win", "ganhou")
        self.mem.update_relation("X", 0.1)
        d = self.mem.to_dict()
        # Deve serializar para JSON sem erros
        json_str = json.dumps(d)
        assert len(json_str) > 10


# ══════════════════════════════════════════════════════════════
# Profiles
# ══════════════════════════════════════════════════════════════

class TestProfiles:
    def test_list_profiles_returns_all(self):
        from runtime.profiles import list_profiles, BUILTIN_PROFILES
        profiles = list_profiles()
        assert len(profiles) == len(BUILTIN_PROFILES)

    def test_get_profile_known(self):
        from runtime.profiles import get_profile
        p = get_profile("claude-kiro")
        assert p.profile_id == "claude-kiro"
        assert p.provider == "omnirouter"

    def test_get_profile_unknown_returns_default(self):
        from runtime.profiles import get_profile
        p = get_profile("nonexistent-model")
        assert p.profile_id == "claude-kiro"

    def test_profiles_have_required_fields(self):
        from runtime.profiles import BUILTIN_PROFILES
        for pid, profile in BUILTIN_PROFILES.items():
            assert profile.profile_id == pid
            assert profile.provider == "omnirouter"
            assert profile.token_budget > 0
            assert profile.cooldown_ticks >= 0
            assert profile.max_tokens > 0


# ══════════════════════════════════════════════════════════════
# Agent Budget/Cooldown
# ══════════════════════════════════════════════════════════════

class TestAgentBudgetCooldown:
    def test_can_think_respects_cooldown_and_budget(self):
        from agent import Agent
        a = Agent("Tester", "Pragmático", 0, 0)
        a.cooldown_ticks = 3
        a.last_thought_tick = 10
        assert not a.can_think(12)
        assert a.can_think(13)

        a.token_budget = 100
        a.tokens_used = 100
        assert not a.can_think(20)


# ══════════════════════════════════════════════════════════════
# AIResponse (base)
# ══════════════════════════════════════════════════════════════

class TestAIResponse:
    def test_total_tokens(self):
        from runtime.adapters.base import AIResponse
        r = AIResponse(
            thought="t", speech="s", action="wait", action_params={},
            prompt_tokens=100, completion_tokens=50
        )
        assert r.total_tokens == 150

    def test_parse_action_from_dict(self):
        from runtime.adapters.base import AIAdapter, AIResponse
        # Instanciar o método via subclasse mínima
        class DummyAdapter(AIAdapter):
            @property
            def provider_name(self): return "test"
            @property
            def model_name(self): return "test-model"
            async def think(self, *a, **kw): pass

        adapter = DummyAdapter()
        data = {"thought": "ok", "speak": "olá", "action": "eat", "params": {"dx": 1}}
        result = adapter._parse_action_from_dict(data, 100.0, 50, 30)
        assert result.action == "eat"
        assert result.speech == "olá"
        assert result.prompt_tokens == 50


# ══════════════════════════════════════════════════════════════
# DecisionLog
# ══════════════════════════════════════════════════════════════

class TestDecisionLog:
    def test_log_creates_file(self):
        from storage.decision_log import DecisionLog, DecisionRecord
        with tempfile.TemporaryDirectory() as tmpdir:
            dl = DecisionLog(log_dir=tmpdir)
            dl.start_session("test-session-001")
            dl.log(DecisionRecord(
                session_id="test-session-001", tick=1,
                agent_id="a1", agent_name="João",
                model="test-model", provider="test",
                latency_ms=100.0, prompt_tokens=50, completion_tokens=30,
                thought="pensei", speech="falei", action="move",
                action_params={"dx": 1},
                result="success",
            ))
            dl.close()

            import os
            logs = os.listdir(tmpdir)
            assert len(logs) == 1
            # Ler o arquivo e verificar NDJSON
            with open(os.path.join(tmpdir, logs[0])) as f:
                line = f.readline()
            entry = json.loads(line)
            assert entry["action"] == "move"
            assert entry["agent_name"] == "João"

    def test_log_multiple_entries(self):
        from storage.decision_log import DecisionLog, DecisionRecord
        with tempfile.TemporaryDirectory() as tmpdir:
            dl = DecisionLog(log_dir=tmpdir)
            dl.start_session("ses-002")
            for i in range(5):
                dl.log(DecisionRecord(
                    session_id="ses-002", tick=i, agent_id=f"a{i}", agent_name=f"Agent{i}",
                    model="m", provider="p", latency_ms=10.0,
                    prompt_tokens=10, completion_tokens=5,
                    thought="", speech="", action="wait", action_params={},
                    result="success",
                ))
            dl.close()
            with open(os.path.join(tmpdir, os.listdir(tmpdir)[0])) as f:
                lines = [l for l in f if l.strip()]
            assert len(lines) == 5


# ══════════════════════════════════════════════════════════════
# SessionStore
# ══════════════════════════════════════════════════════════════

class TestSessionStore:
    def setup_method(self):
        import tempfile
        self.tmpdir = tempfile.mkdtemp()
        from storage.session_store import SessionStore
        self.store = SessionStore(db_path=os.path.join(self.tmpdir, "test.db"))

    def teardown_method(self):
        self.store.close()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_and_get_session(self):
        sid = self.store.create_session({"ai_interval": 5})
        sessions = self.store.get_sessions()
        assert any(s["id"] == sid for s in sessions)

    def test_end_session(self):
        sid = self.store.create_session({})
        self.store.end_session(sid, winner_id="a1", winner_model="gemini")
        sessions = self.store.get_sessions()
        s = next(s for s in sessions if s["id"] == sid)
        assert s["winner_model"] == "gemini"

    def test_upsert_and_scoreboard(self):
        from types import SimpleNamespace
        sid = self.store.create_session({})
        agent = SimpleNamespace(
            id="a1",
            name="TestAgent",
            profile_id="claude-kiro",
            benchmark={"score": 42.0, "decisions_made": 10, "cost_usd": 0.01,
                       "ticks_survived": 5, "invalid_actions": 0},
            tokens_used=500,
            owner_id="owner1",
            model_name="kr/claude-sonnet-4.5",
            provider="omnirouter",
        )
        self.store.upsert_agent_score(sid, agent)
        board = self.store.get_scoreboard()
        assert any(b["agent_name"] == "TestAgent" for b in board)

    def test_multiple_sessions(self):
        for i in range(3):
            self.store.create_session({"i": i})
        sessions = self.store.get_sessions(limit=10)
        assert len(sessions) >= 3


# ══════════════════════════════════════════════════════════════
# API Endpoint: /profiles
# ══════════════════════════════════════════════════════════════

class TestProfilesEndpoint:
    def test_profiles_endpoint_returns_profiles(self):
        from fastapi.testclient import TestClient
        import main

        app = importlib.reload(main).app
        with TestClient(app) as client:
            resp = client.get("/profiles")
            assert resp.status_code == 200
            data = resp.json()
            assert "profiles" in data
            assert isinstance(data["profiles"], list)
            assert len(data["profiles"]) > 0


class TestConnectionManager:
    class FakeWebSocket:
        def __init__(self, send_error: Exception | None = None):
            self.accepted = False
            self.sent_messages: list[str] = []
            self.send_error = send_error

        async def accept(self):
            self.accepted = True

        async def send_text(self, message: str):
            if self.send_error is not None:
                raise self.send_error
            self.sent_messages.append(message)

    def test_connect_does_not_keep_socket_when_init_send_fails(self):
        import main

        main = importlib.reload(main)
        manager = main.ConnectionManager()
        websocket = self.FakeWebSocket(send_error=RuntimeError("closed"))

        connected = asyncio.run(manager.connect(websocket))

        assert connected is False
        assert websocket.accepted is True
        assert manager.active_connections == []

    def test_broadcast_prunes_dead_connections(self):
        import main

        main = importlib.reload(main)
        manager = main.ConnectionManager()
        good_socket = self.FakeWebSocket()
        bad_socket = self.FakeWebSocket(send_error=RuntimeError("closed"))
        manager.active_connections = [good_socket, bad_socket]

        asyncio.run(manager.broadcast({"type": "update", "data": {}}))

        assert good_socket in manager.active_connections
        assert bad_socket not in manager.active_connections
        assert len(good_socket.sent_messages) == 1


class TestAISettingsEndpoints:
    def test_get_ai_settings_exposes_catalog_scope(self):
        from fastapi.testclient import TestClient
        import main

        app = importlib.reload(main).app
        with TestClient(app) as client:
            resp = client.get("/settings/ai")
            assert resp.status_code == 200
            data = resp.json()
            assert data["scope"] == "catalog_default"
            assert data["ai_provider"] == "omnirouter"
            assert "note" in data

    def test_post_ai_settings_updates_catalog_preset(self):
        from fastapi.testclient import TestClient
        import main

        main = importlib.reload(main)
        app = main.app
        with TestClient(app) as client:
            resp = client.post(
                "/settings/ai",
                headers={"X-Admin-Token": main.ADMIN_TOKEN},
                json={
                    "ai_provider": "omnirouter",
                    "ai_model": "kr/claude-sonnet-4.5",
                    "omniroute_url": "http://localhost:20128/v1/chat/completions",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["scope"] == "catalog_default"
            assert data["ai_provider"] == "omnirouter"
            assert data["omniroute_url"] == "http://localhost:20128/v1"

    def test_models_endpoint_returns_catalog_list(self):
        from fastapi.testclient import TestClient
        import main

        app = importlib.reload(main).app
        with TestClient(app) as client:
            resp = client.get("/models?provider=gemini")
            assert resp.status_code == 200
            data = resp.json()
            assert data["scope"] == "catalog"
            assert data["provider"] == "omnirouter"
            assert data["base_url"]
            assert isinstance(data["models"], list)
            assert len(data["models"]) > 0


# ══════════════════════════════════════════════════════════════
# P00 — Game Mode: Matriz de Spawn por Modo
# ══════════════════════════════════════════════════════════════

class TestGameMode:
    def test_survival_mode_has_no_extra_objects(self):
        from world import World
        w = World(size=32, game_mode="survival")
        mode_objs = w._get_mode_spawn_objects()
        assert mode_objs == [], "survival não deve spawnar objetos extras"

    def test_gincana_mode_spawns_checkpoints(self):
        from world import World
        w = World(size=32, game_mode="gincana")
        mode_objs = w._get_mode_spawn_objects()
        types = [o["type"] for o in mode_objs]
        assert "checkpoint" in types
        assert "artifact" in types
        assert "delivery_marker" in types

    def test_warfare_mode_spawns_bases_and_ammo(self):
        from world import World
        w = World(size=32, game_mode="warfare")
        mode_objs = w._get_mode_spawn_objects()
        types = [o["type"] for o in mode_objs]
        assert "team_base" in types
        assert "ammo_cache" in types
        assert "supply_crate" in types
        assert "control_zone" in types

    def test_economy_mode_spawns_market(self):
        from world import World
        w = World(size=36, game_mode="economy")
        mode_objs = w._get_mode_spawn_objects()
        types = [o["type"] for o in mode_objs]
        assert "market_post" in types
        assert "trade_order" in types

    def test_hybrid_mode_spawns_black_market(self):
        from world import World
        w = World(size=44, game_mode="hybrid")
        mode_objs = w._get_mode_spawn_objects()
        types = [o["type"] for o in mode_objs]
        assert "black_market" in types
        assert "sabotage_target" in types
        assert "team_inventory_depot" in types

    def test_game_mode_exposed_in_get_state(self):
        from world import World
        from agent import Agent
        w = World(size=32, game_mode="gincana")
        w.reset_agents(Agent)
        state = w.get_state()
        assert state["game_mode"] == "gincana"

    def test_invalid_mode_falls_back_to_survival(self):
        from world import World
        w = World(size=32, game_mode="invalid_mode_xyz")
        assert w.game_mode == "survival"

    def test_game_mode_persisted_in_session_store(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            sid = store.create_session({"ai_interval": 5}, game_mode="warfare")
            sessions = store.get_sessions()
            s = next(s for s in sessions if s["id"] == sid)
            assert s["game_mode"] == "warfare"
            store.close()

    def test_mode_objects_within_map_bounds(self):
        from world import World
        for mode, size in [("gincana", 32), ("warfare", 40), ("economy", 36), ("hybrid", 44)]:
            w = World(size=size, game_mode=mode)
            for obj in w._get_mode_spawn_objects():
                assert 0 <= obj["x"] < size, f"{mode}: x={obj['x']} fora dos limites"
                assert 0 <= obj["y"] < size, f"{mode}: y={obj['y']} fora dos limites"


# ══════════════════════════════════════════════════════════════
# F01 — Modo Comandante
# ══════════════════════════════════════════════════════════════

class TestModoComandante:
    def test_set_command_updates_agent(self):
        from fastapi.testclient import TestClient
        import main
        app = importlib.reload(main).app
        with TestClient(app) as client:
            state = client.get("/").json()
            # Pega o primeiro agente da lista
            world_data = client.get("/").json()
            # Obtém estado e acha um agente vivo
            import main as m
            agents = [a for a in m.world.agents if a.is_alive]
            assert agents, "Deve haver pelo menos um agente vivo"
            agent_id = agents[0].id

            resp = client.post(f"/agents/{agent_id}/command",
                               json={"command": "Vai buscar água!", "expire_ticks": 50})
            assert resp.status_code == 200
            data = resp.json()
            assert data["command"] == "Vai buscar água!"
            assert agents[0].human_command == "Vai buscar água!"

    def test_cancel_command_clears_agent(self):
        from fastapi.testclient import TestClient
        import main
        app = importlib.reload(main).app
        with TestClient(app) as client:
            import main as m
            agents = [a for a in m.world.agents if a.is_alive]
            agent_id = agents[0].id
            # Seta depois cancela
            client.post(f"/agents/{agent_id}/command",
                        json={"command": "Teste", "expire_ticks": 10})
            client.post(f"/agents/{agent_id}/command/cancel")
            assert agents[0].human_command is None
            assert agents[0].command_source == "ai"

    def test_get_command_returns_active_status(self):
        from fastapi.testclient import TestClient
        import main
        app = importlib.reload(main).app
        with TestClient(app) as client:
            import main as m
            agents = [a for a in m.world.agents if a.is_alive]
            agent_id = agents[0].id
            client.post(f"/agents/{agent_id}/command",
                        json={"command": "Explorar norte", "expire_ticks": 100})
            resp = client.get(f"/agents/{agent_id}/command")
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_active"] is True
            assert data["human_command"] == "Explorar norte"

    def test_command_expiration_in_context(self):
        from world import World
        from agent import Agent
        w = World(size=32, game_mode="survival")
        w.reset_agents(Agent)
        agent = w.agents[0]
        # Define comando que já expirou (tick 0, expire tick 0)
        agent.human_command = "Comando antigo"
        agent.command_expire_tick = 0  # Já expirou
        w.ticks = 5
        ctx = w._get_context_for_agent(agent)
        assert ctx["human_command"] is None  # Deve ter sido expirado


# ══════════════════════════════════════════════════════════════
# F03 — Decision Inspector
# ══════════════════════════════════════════════════════════════

class TestDecisionInspector:
    def test_get_recent_returns_filtered_decisions(self):
        from storage.decision_log import DecisionLog, DecisionRecord
        with tempfile.TemporaryDirectory() as tmpdir:
            dl = DecisionLog(log_dir=tmpdir)
            dl.start_session("s1")
            for i in range(8):
                dl.log(DecisionRecord(
                    session_id="s1", tick=i, agent_id="a1", agent_name="João",
                    model="m", provider="p", latency_ms=10.0,
                    prompt_tokens=10, completion_tokens=5,
                    thought=f"pensamento {i}", speech="", action="wait",
                    action_params={}, result="success",
                ))
            # Decisões de outro agente
            dl.log(DecisionRecord(
                session_id="s1", tick=9, agent_id="a2", agent_name="Maria",
                model="m", provider="p", latency_ms=10.0,
                prompt_tokens=10, completion_tokens=5,
                thought="pensamento de Maria", speech="", action="move",
                action_params={}, result="success",
            ))
            dl.close()
            # Recuperar apenas de a1
            recent = dl.get_recent("s1", "a1", n=5)
            assert len(recent) == 5
            for r in recent:
                assert r["agent_id"] == "a1"

    def test_decisions_endpoint_returns_list(self):
        from fastapi.testclient import TestClient
        import main
        app = importlib.reload(main).app
        with TestClient(app) as client:
            import main as m
            agents = m.world.agents
            agent_id = agents[0].id
            resp = client.get(f"/agents/{agent_id}/decisions?n=5")
            assert resp.status_code == 200
            data = resp.json()
            assert "decisions" in data
            assert isinstance(data["decisions"], list)

    def test_memory_relevant_endpoint(self):
        from fastapi.testclient import TestClient
        import main
        app = importlib.reload(main).app
        with TestClient(app) as client:
            import main as m
            agent_id = m.world.agents[0].id
            resp = client.get(f"/agents/{agent_id}/memory/relevant")
            assert resp.status_code == 200
            data = resp.json()
            assert "short_term" in data
            assert "tokens_used" in data


# ══════════════════════════════════════════════════════════════
# F05 — Console Admin
# ══════════════════════════════════════════════════════════════

class TestAdminConsole:
    def test_spawn_without_token_returns_401(self):
        from fastapi.testclient import TestClient
        import main
        app = importlib.reload(main).app
        with TestClient(app) as client:
            resp = client.post("/admin/spawn",
                               json={"type": "stone", "x": 5, "y": 5})
            assert resp.status_code in (401, 422)  # sem token → não autorizado

    def test_spawn_with_token_adds_entity(self):
        from fastapi.testclient import TestClient
        import main
        main = importlib.reload(main)
        app = main.app
        with TestClient(app) as client:
            initial_count = len(main.world.entities)
            resp = client.post("/admin/spawn",
                               headers={"X-Admin-Token": main.ADMIN_TOKEN},
                               json={"type": "stone", "x": 5, "y": 5})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "spawned"
            assert len(main.world.entities) > initial_count

    def test_event_trigger_tempestade(self):
        from fastapi.testclient import TestClient
        import main
        main = importlib.reload(main)
        app = main.app
        with TestClient(app) as client:
            resp = client.post("/admin/event",
                               headers={"X-Admin-Token": main.ADMIN_TOKEN},
                               json={"event_type": "tempestade"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["event_type"] == "tempestade"

    def test_admin_profile_change(self):
        from fastapi.testclient import TestClient
        import main
        main = importlib.reload(main)
        app = main.app
        with TestClient(app) as client:
            agent_id = main.world.agents[0].id
            resp = client.post("/admin/agent/profile",
                               headers={"X-Admin-Token": main.ADMIN_TOKEN},
                               json={"agent_id": agent_id, "profile_id": "kimi-thinking"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["new_profile"] == "kimi-thinking"
            assert main.world.agents[0].profile_id == "kimi-thinking"

    def test_admin_world_state_without_token_returns_401(self):
        from fastapi.testclient import TestClient
        import main
        app = importlib.reload(main).app
        with TestClient(app) as client:
            resp = client.get("/admin/world/state")
            assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════
# F06 — Temporadas e ELO
# ══════════════════════════════════════════════════════════════

class TestTemporadasELO:
    def test_create_season(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            sid = store.create_season("Temporada 1", game_mode="survival", description="Teste")
            seasons = store.get_seasons()
            assert any(s["id"] == sid for s in seasons)
            s = next(s for s in seasons if s["id"] == sid)
            assert s["name"] == "Temporada 1"
            assert s["game_mode"] == "survival"
            assert s["status"] == "active"
            store.close()

    def test_elo_default_for_new_profile(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            sid = store.create_season("T1")
            elo = store.get_elo(sid, "claude-kiro")
            assert elo == store.ELO_DEFAULT
            store.close()

    def test_calc_elo_winner_gains_points(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            # Dois jogadores com ELO igual: vencedor deve ganhar, perdedor perder
            elos = store._calc_elo([1000.0, 1000.0])
            assert elos[0] > 1000.0, "Vencedor (placement 1) deve ganhar ELO"
            assert elos[1] < 1000.0, "Perdedor (placement 2) deve perder ELO"
            store.close()

    def test_record_elo_session_persists(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            season_id = store.create_season("T1")
            session_id = store.create_session({})
            placements = [
                {"profile_id": "claude-kiro", "score_total": 100.0},
                {"profile_id": "claude-haiku", "score_total": 80.0},
                {"profile_id": "gemini-flash", "score_total": 60.0},
            ]
            results = store.record_elo_session(season_id, session_id, placements)
            assert len(results) == 3
            # Vencedor deve ter delta positivo
            assert results[0]["delta"] > 0, "1° deve ganhar ELO"
            assert results[-1]["delta"] < 0, "Último deve perder ELO"
            # Verificar persistência no leaderboard
            lb = store.get_leaderboard_elo(season_id)
            assert len(lb) == 3
            # ELO do primeiro deve ser maior
            elos_by_profile = {r["profile_id"]: r["elo"] for r in lb}
            assert elos_by_profile["claude-kiro"] > elos_by_profile["gemini-flash"]
            store.close()

    def test_end_season(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            sid = store.create_season("T-end")
            store.end_season(sid)
            seasons = store.get_seasons()
            s = next(s for s in seasons if s["id"] == sid)
            assert s["status"] == "completed"
            assert s["ended_at"] is not None
            store.close()

    def test_seasons_endpoint(self):
        from fastapi.testclient import TestClient
        import main
        main = importlib.reload(main)
        app = main.app
        with TestClient(app) as client:
            resp = client.get("/seasons")
            assert resp.status_code == 200
            assert "seasons" in resp.json()

    def test_create_season_endpoint_requires_admin(self):
        from fastapi.testclient import TestClient
        import main
        app = importlib.reload(main).app
        with TestClient(app) as client:
            resp = client.post("/seasons", json={"name": "T-Unauth"})
            assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════
# F02 — Comparador A/B
# ══════════════════════════════════════════════════════════════

class TestComparadorAB:
    def test_record_ab_result_winner_a(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            sid = store.create_session({})
            result = store.record_ab_result(
                run_id="run1", session_id=sid,
                profile_a="claude-kiro", profile_b="claude-haiku",
                score_a=150.0, score_b=80.0,
                ticks_a=200, ticks_b=200,
                tokens_a=5000, tokens_b=3000,
            )
            assert result["winner"] == "A"
            store.close()

    def test_record_ab_result_tie(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            sid = store.create_session({})
            result = store.record_ab_result(
                run_id="run2", session_id=sid,
                profile_a="claude-kiro", profile_b="claude-haiku",
                score_a=100.0, score_b=100.0,
                ticks_a=200, ticks_b=200,
                tokens_a=4000, tokens_b=4000,
            )
            assert result["winner"] == "tie"
            store.close()

    def test_get_ab_summary_filters_by_profile(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            sid = store.create_session({})
            store.record_ab_result("r1", sid, "claude-kiro", "claude-haiku", 120, 80, 200, 200, 5000, 3000)
            store.record_ab_result("r2", sid, "gemini-flash", "kimi-groq", 90, 110, 200, 200, 4000, 5000)
            results = store.get_ab_summary(profile_a="claude-kiro")
            assert len(results) == 1  # Só r1 tem claude-kiro
            assert results[0]["profile_a"] == "claude-kiro"
            store.close()

    def test_get_ab_stats_aggregated(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            sid = store.create_session({})
            for i in range(3):
                store.record_ab_result(f"r{i}", sid, "claude-kiro", "claude-haiku",
                                       100 + i * 10, 80.0, 200, 200, 5000, 3000)
            stats = store.get_ab_stats()
            assert len(stats) >= 1
            row = next(r for r in stats if r["profile_a"] == "claude-kiro")
            assert row["total"] == 3
            assert row["wins_a"] == 3
            store.close()

    def test_ab_results_endpoint(self):
        from fastapi.testclient import TestClient
        import main
        app = importlib.reload(main).app
        with TestClient(app) as client:
            resp = client.get("/ab/results")
            assert resp.status_code == 200
            data = resp.json()
            assert "results" in data


# ══════════════════════════════════════════════════════════════
# F09 — Versionamento de Perfis
# ══════════════════════════════════════════════════════════════

class TestVersionamentoPerfis:
    def test_save_profile_version_increments(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            snap = {"model": "kr/claude-sonnet-4.5", "temperature": 0.7, "max_tokens": 400}
            v1 = store.save_profile_version("claude-kiro", snap, note="v1 inicial")
            v2 = store.save_profile_version("claude-kiro", {**snap, "temperature": 0.9}, note="v2 quente")
            assert v1 == 1
            assert v2 == 2
            store.close()

    def test_get_profile_versions_returns_all(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            snap = {"model": "kr/claude-sonnet-4.5", "temperature": 0.7}
            store.save_profile_version("claude-kiro", snap)
            store.save_profile_version("claude-kiro", snap)
            versions = store.get_profile_versions("claude-kiro")
            assert len(versions) == 2
            # Deve vir da mais nova para a mais antiga (ORDER BY version DESC)
            assert versions[0]["version"] == 2
            # Snapshot deve ser dict parseado
            assert isinstance(versions[0]["snapshot"], dict)
            store.close()

    def test_rollback_returns_correct_snapshot(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            snap_v1 = {"model": "kr/claude-sonnet-4.5", "temperature": 0.7, "max_tokens": 400}
            snap_v2 = {"model": "kr/claude-sonnet-4.5", "temperature": 0.9, "max_tokens": 200}
            store.save_profile_version("claude-kiro", snap_v1, note="v1")
            store.save_profile_version("claude-kiro", snap_v2, note="v2")
            rollback = store.rollback_profile_version("claude-kiro", 1)
            assert rollback["temperature"] == 0.7
            assert rollback["max_tokens"] == 400
            store.close()

    def test_rollback_nonexistent_version_returns_none(self):
        from storage.session_store import SessionStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=os.path.join(tmpdir, "test.db"))
            result = store.rollback_profile_version("claude-kiro", 999)
            assert result is None
            store.close()

    def test_profile_versions_endpoint(self):
        from fastapi.testclient import TestClient
        import main
        main = importlib.reload(main)
        app = main.app
        with TestClient(app) as client:
            resp = client.get("/profiles/claude-kiro/versions")
            assert resp.status_code == 200
            data = resp.json()
            assert "versions" in data
            assert data["profile_id"] == "claude-kiro"

    def test_save_version_endpoint_requires_admin(self):
        from fastapi.testclient import TestClient
        import main
        app = importlib.reload(main).app
        with TestClient(app) as client:
            resp = client.post("/profiles/claude-kiro/versions", json={"note": "teste"})
            assert resp.status_code == 401

    def test_save_version_endpoint_with_token(self):
        from fastapi.testclient import TestClient
        import main
        main = importlib.reload(main)
        app = main.app
        with TestClient(app) as client:
            resp = client.post("/profiles/claude-kiro/versions",
                               headers={"X-Admin-Token": main.ADMIN_TOKEN},
                               json={"note": "snapshot de teste", "temperature": 0.85})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "saved"
            assert data["version"] >= 1
            assert data["snapshot"]["temperature"] == 0.85
