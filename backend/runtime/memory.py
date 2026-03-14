"""
T10 — Memória 4 Camadas do Agente.

Estrutura:
  1. short_term   — últimas N ações (lista circular, max 10)
  2. episodic     — eventos marcantes: mortes, ataques, alianças (cresce ilimitado, truncado em 50)
  3. relational   — percepção do agente sobre outros agentes (dict: name → opinion)
  4. benchmark    — métricas de performance da sessão (tokens, score, decisões)

O Thinker injeta a memória consolidada no contexto do agente ao montar o prompt.
"""
from dataclasses import dataclass, field
from typing import Optional


# ── Tipos de entrada de memória ────────────────────────────────────────────────

@dataclass
class ShortTermEntry:
    tick: int
    action: str
    thought: str = ""
    result: str = ""


@dataclass
class EpisodicEntry:
    tick: int
    event_type: str       # "death", "attack", "alliance", "zombie", "win", "found_item"
    description: str
    agents_involved: list[str] = field(default_factory=list)


@dataclass
class RelationalEntry:
    agent_name: str
    opinion: float        # -1.0 (inimigo) a +1.0 (aliado)
    interactions: int = 0
    last_seen_tick: int = 0
    notes: str = ""


# ── Classe principal ──────────────────────────────────────────────────────────

class AgentMemory:
    """Memória em 4 camadas para um agente. Stateful por sessão."""

    SHORT_TERM_MAX = 10
    EPISODIC_MAX   = 50

    def __init__(self):
        self.short_term:  list[ShortTermEntry]      = []
        self.episodic:    list[EpisodicEntry]        = []
        self.relational:  dict[str, RelationalEntry] = {}

    # ── Short-term ──────────────────────────────────────────────────────────

    def add_short_term(self, tick: int, action: str, thought: str = "", result: str = "") -> None:
        entry = ShortTermEntry(tick=tick, action=action, thought=thought, result=result)
        self.short_term.append(entry)
        if len(self.short_term) > self.SHORT_TERM_MAX:
            self.short_term.pop(0)

    def get_short_term_summary(self) -> str:
        if not self.short_term:
            return "Sem ações recentes."
        lines = [f"T{e.tick}: {e.action}" + (f" ({e.result})" if e.result else "") for e in self.short_term[-5:]]
        return "\n".join(lines)

    # ── Episodic ────────────────────────────────────────────────────────────

    def add_episodic(self, tick: int, event_type: str, description: str,
                     agents_involved: list[str] = None) -> None:
        entry = EpisodicEntry(
            tick=tick, event_type=event_type,
            description=description,
            agents_involved=agents_involved or [],
        )
        self.episodic.append(entry)
        if len(self.episodic) > self.EPISODIC_MAX:
            self.episodic.pop(0)

    def get_episodic_summary(self, max_events: int = 5) -> str:
        if not self.episodic:
            return "Sem eventos marcantes."
        recent = self.episodic[-max_events:]
        return "\n".join([f"T{e.tick} [{e.event_type}]: {e.description}" for e in recent])

    # ── Relational ──────────────────────────────────────────────────────────

    def update_relation(self, agent_name: str, opinion_delta: float,
                        tick: int = 0, note: str = "") -> None:
        """Atualiza a percepção sobre outro agente. Opinion é clamped em [-1, 1]."""
        if agent_name not in self.relational:
            self.relational[agent_name] = RelationalEntry(agent_name=agent_name, opinion=0.0)
        r = self.relational[agent_name]
        r.opinion = max(-1.0, min(1.0, r.opinion + opinion_delta))
        r.interactions += 1
        r.last_seen_tick = tick
        if note:
            r.notes = note

    def get_relation(self, agent_name: str) -> Optional[RelationalEntry]:
        return self.relational.get(agent_name)

    def get_relational_summary(self) -> str:
        if not self.relational:
            return "Sem percepções sobre outros agentes."
        lines = []
        for name, r in sorted(self.relational.items(), key=lambda x: -abs(x[1].opinion)):
            emoji = "❤️" if r.opinion > 0.3 else ("😡" if r.opinion < -0.3 else "😐")
            lines.append(f"{emoji} {name}: {r.opinion:+.2f} ({r.interactions} interações)")
        return "\n".join(lines)

    # ── Consolidated context ─────────────────────────────────────────────────

    def to_prompt_context(self) -> str:
        """Retorna string consolidada das memórias para injetar no prompt."""
        return f"""
🧠 MEMÓRIA RECENTE:
{self.get_short_term_summary()}

📖 EVENTOS MARCANTES:
{self.get_episodic_summary()}

🤝 PERCEPÇÃO DOS OUTROS:
{self.get_relational_summary()}
""".strip()

    def to_dict(self) -> dict:
        """Serializa para JSON (para incluir no estado do agente via API)."""
        return {
            "short_term": [
                {"tick": e.tick, "action": e.action, "thought": e.thought, "result": e.result}
                for e in self.short_term
            ],
            "episodic": [
                {"tick": e.tick, "type": e.event_type, "desc": e.description, "agents": e.agents_involved}
                for e in self.episodic
            ],
            "relational": {
                name: {"opinion": r.opinion, "interactions": r.interactions, "notes": r.notes}
                for name, r in self.relational.items()
            },
        }
