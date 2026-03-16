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
            assert profile.provider in ("gemini", "omnirouter")
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
            assert data["ai_provider"] in ("gemini", "omnirouter")
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
            assert data["provider"] == "gemini"
            assert isinstance(data["models"], list)
            assert len(data["models"]) > 0
