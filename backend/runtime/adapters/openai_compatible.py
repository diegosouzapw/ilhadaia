"""
Adapter para qualquer provider OpenAI-compatible: OmniRouter, Groq, Anthropic, etc.
Usa o openai Python SDK com base_url customizável.
"""
import json
import logging
import time
from typing import Optional

from .base import AIAdapter, AIResponse
from runtime.schemas import ActionDecision

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
            
            # Use model_dump to get a dict representation for easier inspection
            resp_dict = response.model_dump()
            
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0

            # Check alternative names if standard ones are zero
            if prompt_tokens == 0:
                # 1. Try common aliases in usage object
                if usage:
                    prompt_tokens = (getattr(usage, "in_tokens", 0) or getattr(usage, "input_tokens", 0)) or 0
                    if prompt_tokens == 0 and hasattr(usage, "model_dump"):
                        extra = getattr(usage, "model_extra", {}) or {}
                        prompt_tokens = (extra.get("in", 0) or extra.get("input", 0)) or 0
                
                # 2. Try top-level aliases in resp_dict
                if prompt_tokens == 0:
                    prompt_tokens = (resp_dict.get("in", 0) or resp_dict.get("input_tokens", 0)) or 0

            if completion_tokens == 0:
                # 1. Try common aliases in usage object
                if usage:
                    completion_tokens = (getattr(usage, "out_tokens", 0) or getattr(usage, "output_tokens", 0)) or 0
                    if completion_tokens == 0 and hasattr(usage, "model_dump"):
                        extra = getattr(usage, "model_extra", {}) or {}
                        completion_tokens = (extra.get("out", 0) or extra.get("output", 0)) or 0

                # 2. Try top-level aliases in resp_dict
                if completion_tokens == 0:
                    completion_tokens = (resp_dict.get("out", 0) or resp_dict.get("output_tokens", 0)) or 0

            # Log raw response if tokens are 0 to help debugging as requested by user
            if (prompt_tokens == 0 or completion_tokens == 0):
                logger.info(f"[{self._model_id}] TOKENS NOT FOUND. Raw response dict: {json.dumps(resp_dict)}")
            else:
                logger.info(f"[{self._model_id}] Tokens EXTRACTED: prompt={prompt_tokens}, completion={completion_tokens}")

            data = self._parse_decision(content)

            return self._parse_action_from_dict(
                data, latency,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
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

    def _parse_decision(self, text: str) -> dict:
        """Valida o output no schema ActionDecision com fallback robusto."""
        try:
            return ActionDecision.model_validate_json(text).model_dump()
        except Exception:
            data = self._extract_json(text)
            return ActionDecision.from_dict(data).model_dump()
