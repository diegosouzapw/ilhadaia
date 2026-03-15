"""
Adapter para Google Gemini via google-genai SDK.
Mantém a lógica atual isolada do agent.py para ser intercambiável.
"""
import json
import logging
import os
import time

from .base import AIAdapter, AIResponse
from runtime.schemas import ActionDecision

logger = logging.getLogger("BBB_IA.adapters.gemini")


class GeminiAdapter(AIAdapter):
    """Chama Gemini via google.genai SDK com response_mime_type=application/json."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash-lite"):
        api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._model_id = model
        if not api_key:
            # Sem chave, não inicializa cliente para evitar erro assíncrono de fechamento.
            self._client = None
            self._genai = None
            logger.warning("GeminiAdapter init skipped: GEMINI_API_KEY ausente")
            return
        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            self._genai = genai
        except Exception as e:
            logger.error(f"GeminiAdapter init error: {e}")
            self._client = None
            self._genai = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_id

    async def think(self, system_prompt: str, user_context: str,
                    max_tokens: int = 300, temperature: float = 0.7) -> AIResponse:
        if not self._client:
            return AIResponse(thought="No API client", speech="...", action="wait", action_params={})

        t0 = time.time()
        try:
            response = self._client.models.generate_content(
                model=self._model_id,
                contents=user_context,
                config=self._genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
            )
            latency = (time.time() - t0) * 1000
            text = response.text.strip()

            # Limpar markdown se presente
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]

            try:
                decision = ActionDecision.model_validate_json(text)
                data = decision.model_dump()
            except Exception:
                # Fallback: parse de texto/JSON livre com coerção para schema válido
                try:
                    data = json.loads(text)
                except Exception:
                    data = {}
                decision = ActionDecision.from_dict(data)
                data = decision.model_dump()

            usage = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            completion_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

            return self._parse_action_from_dict(data, latency, prompt_tokens, completion_tokens)

        except Exception as e:
            latency = (time.time() - t0) * 1000
            logger.error(f"GeminiAdapter.think error: {e}")
            return AIResponse(thought=f"Error: {e}", speech="(mente em branco)", action="wait",
                              action_params={}, latency_ms=latency)
