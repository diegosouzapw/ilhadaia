"""
Adapter para qualquer provider OpenAI-compatible: OmniRouter, Groq, Anthropic, etc.
Usa o openai Python SDK com base_url customizável.
"""
import json
import logging
import time
from typing import Optional

from .base import AIAdapter, AIResponse

logger = logging.getLogger("BBB_IA.adapters.openai_compat")


class OpenAICompatibleAdapter(AIAdapter):
    """
    Adapter genérico para qualquer API OpenAI-compatible.
    Testado com OmniRouter em http://192.168.0.15:20128/.
    """

    def __init__(self, base_url: str, model: str, api_key: str = "none"):
        self._base_url = base_url
        self._model_id = model
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        except ImportError:
            logger.error("openai package não instalado. Execute: pip install openai")
            self._client = None

    @property
    def provider_name(self) -> str:
        return "omnirouter"

    @property
    def model_name(self) -> str:
        return self._model_id

    async def think(self, system_prompt: str, user_context: str,
                    max_tokens: int = 300, temperature: float = 0.7) -> AIResponse:
        if not self._client:
            return AIResponse(thought="No client", speech="...", action="wait", action_params={})

        t0 = time.time()
        try:
            response = await self._client.chat.completions.create(
                model=self._model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_context},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            latency = (time.time() - t0) * 1000
            content = response.choices[0].message.content or ""
            usage = response.usage

            # Tentar parsear como JSON
            data = self._extract_json(content)

            return self._parse_action_from_dict(
                data, latency,
                prompt_tokens=getattr(usage, "prompt_tokens", 0),
                completion_tokens=getattr(usage, "completion_tokens", 0),
            )

        except Exception as e:
            latency = (time.time() - t0) * 1000
            logger.error(f"OpenAICompatibleAdapter.think error [{self._model_id}]: {e}")
            return AIResponse(thought=f"Error: {e}", speech="(silêncio)", action="wait",
                              action_params={}, latency_ms=latency)

    def _extract_json(self, text: str) -> dict:
        """Tenta extrair JSON do texto, com fallback para wait."""
        text = text.strip()
        # Remover markdown
        if "```json" in text:
            text = text.split("```json", 1)[1]
        if "```" in text:
            text = text.split("```")[0]
        # Tentar parse direto
        try:
            return json.loads(text)
        except Exception:
            pass
        # Tentar extrair objeto JSON com regex
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        # Fallback total
        logger.warning(f"JSON parse failed for: {text[:100]}")
        return {"thought": "Erro de parse", "speak": "...", "action": "wait", "params": {}}
