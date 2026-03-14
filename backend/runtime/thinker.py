"""
Thinker — orquestrador central de decisões de IA.
Verifica elegibilidade (cooldown/budget), monta contexto, chama o adapter
correto, valida via ActionDecision (T11) e registra no DecisionLog.
Integrado com AgentMemory 4 camadas (T10).
"""
import json
import logging
from typing import Optional

from .adapters.base import AIAdapter, AIResponse
from .adapters.gemini import GeminiAdapter
from .adapters.openai_compatible import OpenAICompatibleAdapter
from .profiles import AgentProfile, get_profile
from .schemas import ActionDecision
from storage.decision_log import DecisionLog, DecisionRecord

logger = logging.getLogger("BBB_IA.Thinker")


class Thinker:
    """Ponto central que orquestra chamadas de IA para qualquer agente."""

    def __init__(self, decision_log: DecisionLog):
        self.log = decision_log
        self._adapters: dict[str, AIAdapter] = {}

    # ── Adapter cache ───────────────────────────────────────────────────────

    def get_adapter(self, profile: AgentProfile) -> AIAdapter:
        """Retorna (ou cria) o adapter para o perfil dado. Cache por profile_id."""
        key = profile.profile_id
        if key not in self._adapters:
            if profile.provider == "gemini":
                self._adapters[key] = GeminiAdapter(model=profile.model)
            else:
                self._adapters[key] = OpenAICompatibleAdapter(
                    base_url=profile.base_url or "http://192.168.0.15:20128",
                    model=profile.model,
                    api_key=profile.api_key,
                )
        return self._adapters[key]

    # ── Main think ──────────────────────────────────────────────────────────

    async def think(
        self,
        agent,
        world_context: dict,
        current_tick: int,
        session_id: str,
    ) -> Optional[dict]:
        """
        Tenta fazer o agente pensar. Retorna dict de ação ou None se skipped.
        1. Verifica cooldown e budget
        2. Chama adapter → raw AIResponse
        3. Valida via ActionDecision (T11)
        4. Atualiza memória 4 camadas (T10)
        5. Loga no DecisionLog
        """
        # 1. Verificar elegibilidade
        if not agent.can_think(current_tick):
            reason = (
                "skip_cooldown"
                if current_tick - agent.last_thought_tick < agent.cooldown_ticks
                else "skip_budget"
            )
            logger.debug(f"[{agent.name}] skip: {reason}")
            return None

        # 2. Buscar perfil e adapter
        profile = get_profile(getattr(agent, "profile_id", "gemini-native"))
        adapter = self.get_adapter(profile)

        # 3. Montar prompts
        system_prompt = self._build_system_prompt(agent)
        user_context = self._build_user_context(agent, world_context, current_tick)

        # 4. Chamar IA
        try:
            response: AIResponse = await adapter.think(
                system_prompt=system_prompt,
                user_context=user_context,
                max_tokens=profile.max_tokens,
                temperature=profile.temperature,
            )
        except Exception as e:
            logger.error(f"[{agent.name}] adapter error: {e}")
            self.log.log(DecisionRecord(
                session_id=session_id, tick=current_tick,
                agent_id=agent.id, agent_name=agent.name,
                model=profile.model, provider=profile.provider,
                latency_ms=0.0, prompt_tokens=0, completion_tokens=0,
                thought="", speech="", action="wait", action_params={},
                result="error",
            ))
            return None

        # 5. Validar via ActionDecision (T11)
        raw_dict = {
            "thought": response.thought,
            "speak": response.speech,
            "action": response.action,
            "target_name": response.target_name,
            "intent": response.intent,
            "params": response.action_params,
        }
        decision = ActionDecision.from_dict(raw_dict)
        is_invalid = response.action != decision.action  # action foi corrigida para wait?

        # 6. Atualizar estado do agente
        agent.tokens_used += response.total_tokens
        agent.last_thought_tick = current_tick
        agent.benchmark["decisions_made"] += 1
        if is_invalid:
            agent.benchmark["invalid_actions"] += 1

        # 7. Atualizar memória 4 camadas (T10)
        agent_memory = getattr(agent, "agent_memory", None)
        if agent_memory is not None:
            agent_memory.add_short_term(
                tick=current_tick,
                action=decision.action,
                thought=decision.thought[:100],
                result="ok" if not is_invalid else "action_corrected",
            )
            # Evento episódico para ações críticas
            if decision.action in ("attack", "bury", "pickup_body"):
                agent_memory.add_episodic(
                    tick=current_tick,
                    event_type=decision.action,
                    description=f"{agent.name} executou {decision.action} em {decision.target_name or 'alvo'}",
                    agents_involved=[decision.target_name] if decision.target_name else [],
                )

        # 8. Logar decisão
        self.log.log(DecisionRecord(
            session_id=session_id,
            tick=current_tick,
            agent_id=agent.id,
            agent_name=agent.name,
            model=profile.model,
            provider=profile.provider,
            latency_ms=response.latency_ms,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            thought=decision.thought,
            speech=decision.speak,
            action=decision.action,
            action_params=decision.params,
            result="invalid" if is_invalid else "success",
        ))

        # 9. Formatar retorno compatível com o World
        return decision.to_world_action(agent.id, agent.name)

    # ── Prompt builders ─────────────────────────────────────────────────────

    def _build_system_prompt(self, agent) -> str:
        """Constrói o system prompt incluindo o schema JSON (T11)."""
        base_instruction = getattr(agent, "system_instruction", None)
        if base_instruction:
            return base_instruction

        from .schemas import ActionDecision
        return f"""Você é {agent.name}, um personagem em uma simulação de sobrevivência.
Sua personalidade: {agent.personality}

{ActionDecision.get_json_schema_prompt()}"""

    def _build_user_context(self, agent, world_context: dict, tick: int) -> str:
        """Constrói o contexto do usuário integrando a memória 4 camadas (T10)."""
        # Pega o contexto de memória se disponível
        memory_ctx = ""
        agent_memory = getattr(agent, "agent_memory", None)
        if agent_memory is not None:
            memory_ctx = f"\n{agent_memory.to_prompt_context()}\n"

        base = f"""
TICK ATUAL: {tick}
PERÍODO: {"🌙 NOITE" if world_context.get('is_night') else "☀️ DIA"}

SEU STATUS:
Posição: x={agent.x}, y={agent.y}
ZUMBI: {"SIM!" if getattr(agent, 'is_zombie', False) else "NÃO"}
Fome: {agent.hunger}/100 | Sede: {agent.thirst}/100 | HP: {agent.hp}/100
Bolsa: {world_context.get('inventory', [])}
Carregando corpo: {"SIM" if world_context.get('is_carrying_body') else "NÃO"}
{memory_ctx}
VOCÊ PODE INTERAGIR COM (ALCANCE IMEDIATO):
{json.dumps(world_context.get('reachable_now', []), indent=2, ensure_ascii=False)}

VOCÊ ESTÁ VENDO:
{json.dumps(world_context.get('visible_entities', []), indent=2, ensure_ascii=False)}

📊 BENCHMARK: tokens={agent.tokens_used}/{agent.token_budget} | decisões={agent.benchmark.get('decisions_made', 0)} | score={agent.benchmark.get('score', 0.0):.1f}

Qual é sua próxima ação? Retorne APENAS o JSON.
"""
        return base
