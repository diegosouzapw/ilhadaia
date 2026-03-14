"""
Agent Profiles — define o perfil de IA de cada agente para benchmark multi-provider.
Cada perfil determina: provider, modelo, budget de tokens, cooldown e temperatura.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentProfile:
    profile_id: str
    provider: str              # "gemini" | "omnirouter"
    model: str                 # nome do modelo
    base_url: Optional[str] = None   # URL do provider (para omnirouter)
    temperature: float = 0.7
    max_tokens: int = 300
    token_budget: int = 10_000       # limite de tokens por sessão
    cooldown_ticks: int = 3          # ticks mínimos entre pensamentos
    api_key: str = "none"


# ── Perfis disponíveis ──────────────────────────────────────────────────────
OMNIROUTER_URL = "http://192.168.0.15:20128"

BUILTIN_PROFILES: dict[str, AgentProfile] = {

    # Gemini nativo (sem OmniRouter)
    "gemini-native": AgentProfile(
        profile_id="gemini-native",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        max_tokens=300,
        token_budget=10_000,
        cooldown_ticks=3,
    ),

    # OmniRouter: modelos baratos e rápidos
    "cheap-fast": AgentProfile(
        profile_id="cheap-fast",
        provider="omnirouter",
        model="gemini/gemini-2.5-flash-lite",
        base_url=OMNIROUTER_URL,
        max_tokens=200,
        token_budget=5_000,
        cooldown_ticks=5,
    ),

    # OmniRouter: equilíbrio custo/qualidade
    "balanced": AgentProfile(
        profile_id="balanced",
        provider="omnirouter",
        model="gemini/gemini-2.5-flash",
        base_url=OMNIROUTER_URL,
        max_tokens=350,
        token_budget=10_000,
        cooldown_ticks=3,
    ),

    # OmniRouter: modelo mais inteligente
    "smart": AgentProfile(
        profile_id="smart",
        provider="omnirouter",
        model="gemini/gemini-2.5-pro",
        base_url=OMNIROUTER_URL,
        max_tokens=500,
        token_budget=20_000,
        cooldown_ticks=6,
    ),

    # OmniRouter: OSS via Groq (ultra-rápido)
    "oss-fast": AgentProfile(
        profile_id="oss-fast",
        provider="omnirouter",
        model="groq/llama-3.3-70b-versatile",
        base_url=OMNIROUTER_URL,
        max_tokens=250,
        token_budget=8_000,
        cooldown_ticks=2,
    ),

    # OmniRouter: DeepSeek criativo
    "creative": AgentProfile(
        profile_id="creative",
        provider="omnirouter",
        model="iflow/deepseek-v3",
        base_url=OMNIROUTER_URL,
        temperature=0.9,
        max_tokens=400,
        token_budget=12_000,
        cooldown_ticks=4,
    ),
}


def get_profile(profile_id: str) -> AgentProfile:
    """Retorna o perfil pelo ID. Usa 'gemini-native' como fallback."""
    return BUILTIN_PROFILES.get(profile_id, BUILTIN_PROFILES["gemini-native"])


def list_profiles() -> list[dict]:
    """Lista todos os perfis disponíveis (para endpoint /profiles)."""
    return [
        {
            "profile_id": p.profile_id,
            "provider": p.provider,
            "model": p.model,
            "cooldown_ticks": p.cooldown_ticks,
            "token_budget": p.token_budget,
            "max_tokens": p.max_tokens,
        }
        for p in BUILTIN_PROFILES.values()
    ]
