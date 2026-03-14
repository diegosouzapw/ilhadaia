"""
Base abstrata para todos os adapters de IA.
Define a interface que Gemini, OmniRouter e qualquer outro provider devem implementar.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import time


@dataclass
class AIResponse:
    """Resposta normalizada de qualquer adapter de IA."""
    thought: str
    speech: str
    action: str
    action_params: dict
    intent: str = "survive"
    target_name: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class AIAdapter(ABC):
    """Interface que todo adapter de IA deve implementar."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identificador do provider (ex: 'gemini', 'omnirouter')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nome completo do modelo (ex: 'gemini-2.5-flash-lite')."""
        ...

    @abstractmethod
    async def think(
        self,
        system_prompt: str,
        user_context: str,
        max_tokens: int = 300,
        temperature: float = 0.7,
    ) -> AIResponse:
        """Chama a IA e retorna uma resposta normalizada."""
        ...

    def _parse_action_from_dict(self, data: dict, latency: float,
                                 prompt_tokens: int = 0, completion_tokens: int = 0) -> AIResponse:
        """Converte um dicionário de ação para AIResponse."""
        params = data.get("params", {}) or {}
        return AIResponse(
            thought=str(data.get("thought", "")),
            speech=str(data.get("speak", data.get("speech", ""))),
            action=str(data.get("action", "wait")),
            action_params=params if isinstance(params, dict) else {},
            intent=str(data.get("intent", "survive")),
            target_name=str(data.get("target_name", "")),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency,
        )
