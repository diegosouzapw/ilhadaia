"""
T21 — Relevância Episódica com Keyword Scoring.

Implementa busca semântica leve para a memória episódica do AgentMemory,
sem dependências pesadas como ChromaDB. Usa TF-IDF simplificado com
pesos por tipo de evento e relevância contextual.
"""
import math
import re
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.memory import EpisodicEntry


def tokenize(text: str) -> list[str]:
    """Tokenização simples: lowercase, remover pontuação, split."""
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return [t for t in text.split() if len(t) > 2]


# Pesos por tipo de evento — eventos críticos têm mais relevância
EVENT_TYPE_WEIGHT = {
    "death":    3.0,
    "attack":   2.5,
    "win":      3.0,
    "zombie":   2.0,
    "alliance": 2.0,
    "found_item": 1.5,
    "move":     0.5,
    "wait":     0.3,
}


def event_weight(event_type: str) -> float:
    return EVENT_TYPE_WEIGHT.get(event_type.lower(), 1.0)


class EpisodicRelevanceEngine:
    """
    Motor de relevância para a memória episódica.
    Pontua eventos e retorna os mais relevantes para um contexto.
    """

    def __init__(self, decay_rate: float = 0.005):
        """
        decay_rate: quanto a relevância decresce por tick passado.
        Ex: 0.005 → evento de 200 ticks atrás tem ~37% da relevância original.
        """
        self.decay_rate = decay_rate

    def score_entry(
        self,
        entry: "EpisodicEntry",
        query_tokens: list[str],
        current_tick: int,
    ) -> float:
        """
        Calcula score de relevância de um evento episódico.

        Score = type_weight × text_match × recency_decay
        """
        # 1. Peso do tipo de evento
        type_w = event_weight(entry.event_type)

        # 2. Correspondência de texto (tf-idf simplificado)
        entry_tokens = tokenize(entry.description)
        if not entry_tokens or not query_tokens:
            text_score = 0.5  # texto vazio tem relevância neutra
        else:
            entry_counter = Counter(entry_tokens)
            matches = sum(min(entry_counter[t], 1) for t in query_tokens if t in entry_counter)
            text_score = matches / math.sqrt(len(query_tokens) * len(entry_tokens) + 1)

        # 3. Decaimento temporal
        ticks_ago = max(0, current_tick - entry.tick)
        recency = math.exp(-self.decay_rate * ticks_ago)

        return type_w * (0.4 + 0.6 * text_score) * recency

    def get_relevant(
        self,
        episodes: list["EpisodicEntry"],
        context: str,
        current_tick: int,
        top_k: int = 5,
    ) -> list["EpisodicEntry"]:
        """
        Retorna os `top_k` episódios mais relevantes para o contexto dado.
        """
        query_tokens = tokenize(context)
        scored = [
            (entry, self.score_entry(entry, query_tokens, current_tick))
            for entry in episodes
        ]
        scored.sort(key=lambda x: -x[1])
        return [entry for entry, score in scored[:top_k] if score > 0.1]

    def get_relevant_summary(
        self,
        episodes: list["EpisodicEntry"],
        context: str,
        current_tick: int,
        top_k: int = 5,
    ) -> str:
        """Equivalente a AgentMemory.get_episodic_summary() mas com relevância."""
        relevant = self.get_relevant(episodes, context, current_tick, top_k)
        if not relevant:
            return "Sem eventos relevantes para o contexto atual."
        return "\n".join(
            [f"T{e.tick} [{e.event_type}]: {e.description}" for e in relevant]
        )


# Instância global (singleton leve)
_engine = EpisodicRelevanceEngine()


def get_relevant_episodes(episodes, context: str, current_tick: int, top_k: int = 5) -> list:
    return _engine.get_relevant(episodes, context, current_tick, top_k)


def get_relevant_summary(episodes, context: str, current_tick: int, top_k: int = 5) -> str:
    return _engine.get_relevant_summary(episodes, context, current_tick, top_k)
