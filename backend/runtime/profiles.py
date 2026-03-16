"""
Agent Profiles — define o perfil de IA de cada agente para benchmark multi-provider.
Cada perfil determina: provider, modelo, budget de tokens, cooldown e temperatura.

Todos os perfis OmniRoute usam o mesmo endpoint (OMNIROUTER_URL) — só o modelo muda.
O endpoint é lido de OMNIROUTER_URL no .env (default: http://192.168.0.15:20128/v1).
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentProfile:
    profile_id: str
    provider: str              # "gemini" | "omnirouter"
    model: str                 # nome do modelo (ex: "kr/claude-sonnet-4.5")
    base_url: Optional[str] = None   # URL do provider (para omnirouter)
    temperature: float = 0.7
    max_tokens: int = 300
    token_budget: int = 10_000       # limite de tokens por sessão
    cooldown_ticks: int = 3          # ticks mínimos entre pensamentos
    api_key: str = "none"


# ── Configuração central do OmniRoute ──────────────────────────────────────────
# Lê do .env — fallback para o endereço local padrão
OMNIROUTER_URL = (
    os.getenv("OMNIROUTER_URL")
    or os.getenv("OMNIROUTE_URL")
    or "http://192.168.0.15:20128/v1"
)

# ── Chave de API do OmniRoute (qualquer string serve como proxy local) ─────────
OMNIROUTER_API_KEY = (
    os.getenv("OMNIROUTER_API_KEY")
    or os.getenv("OMNIROUTE_API_KEY")
    or "omniroute-local"
)


# ── Perfis disponíveis ──────────────────────────────────────────────────────────
#
# Convenção de prefixo de modelo no 9router/OmniRoute:
#   kr/  → Kiro (AWS Builder ID — grátis e ilimitado)
#   if/  → iFlow (Google OAuth — grátis e ilimitado)
#   qw/  → Qwen (Device Code — grátis e ilimitado)
#   gc/  → Gemini CLI (Google OAuth — 180K tok/mês grátis)
#   groq/ → Groq API (30 RPM grátis)
#   gemini/ → Gemini API Key direta
#
# Endpoint é SEMPRE o mesmo: OMNIROUTER_URL. Só o modelo/prefixo muda.
#
BUILTIN_PROFILES: dict[str, AgentProfile] = {

    # ── Claude Sonnet 4.5 via Kiro (padrão — grátis e ilimitado) ─────────────────────
    "claude-kiro": AgentProfile(
        profile_id="claude-kiro",
        provider="omnirouter",
        model="kr/claude-sonnet-4.5",   # ponto, não hífen
        base_url=OMNIROUTER_URL,
        api_key=OMNIROUTER_API_KEY,
        max_tokens=400,
        token_budget=15_000,
        cooldown_ticks=4,
        temperature=0.7,
    ),

    # ── Claude Haiku 4.5 via Kiro (rápido e leve, grátis) ──────────────────────
    "claude-haiku": AgentProfile(
        profile_id="claude-haiku",
        provider="omnirouter",
        model="kr/claude-haiku-4.5",    # ponto, não hífen
        base_url=OMNIROUTER_URL,
        api_key=OMNIROUTER_API_KEY,
        max_tokens=250,
        token_budget=8_000,
        cooldown_ticks=2,
        temperature=0.8,
    ),

    # ── Kimi K2 via iFlow (grátis) ─────────────────────────────────────────────────
    "kimi-thinking": AgentProfile(
        profile_id="kimi-thinking",
        provider="omnirouter",
        model="if/kimi-k2",             # kimi-k2 disponível via iFlow
        base_url=OMNIROUTER_URL,
        api_key=OMNIROUTER_API_KEY,
        max_tokens=500,
        token_budget=20_000,
        cooldown_ticks=6,
        temperature=0.6,
    ),

    # ── Qwen3 Coder via iFlow (código, grátis) ───────────────────────────────
    "qwen-coder": AgentProfile(
        profile_id="qwen-coder",
        provider="omnirouter",
        model="if/qwen3-coder-plus",
        base_url=OMNIROUTER_URL,
        api_key=OMNIROUTER_API_KEY,
        max_tokens=350,
        token_budget=10_000,
        cooldown_ticks=3,
        temperature=0.7,
    ),

    # ── Kimi K2 via Groq (kimi-k2-instruct, testado OK, grátis) ──────────────────
    "kimi-groq": AgentProfile(
        profile_id="kimi-groq",
        provider="omnirouter",
        model="groq/moonshotai/kimi-k2-instruct",
        base_url=OMNIROUTER_URL,
        api_key=OMNIROUTER_API_KEY,
        max_tokens=300,
        token_budget=10_000,
        cooldown_ticks=3,
        temperature=0.7,
    ),

    # ── Gemini Flash via Gemini CLI (grátis, pode ter cooldown) ────────────────
    "gemini-flash": AgentProfile(
        profile_id="gemini-flash",
        provider="omnirouter",
        model="gc/gemini-2.5-flash",
        base_url=OMNIROUTER_URL,
        api_key=OMNIROUTER_API_KEY,
        max_tokens=300,
        token_budget=10_000,
        cooldown_ticks=3,
        temperature=0.7,
    ),

    # ── Llama via Groq (ultra-rápido, 30 RPM grátis) ─────────────────────────
    "llama-groq": AgentProfile(
        profile_id="llama-groq",
        provider="omnirouter",
        model="groq/llama-3.3-70b-versatile",
        base_url=OMNIROUTER_URL,
        api_key=OMNIROUTER_API_KEY,
        max_tokens=250,
        token_budget=8_000,
        cooldown_ticks=2,
        temperature=0.8,
    ),

    # ── Gemini nativo (sem OmniRoute — usa GEMINI_API_KEY diretamente) ────────
    "gemini-native": AgentProfile(
        profile_id="gemini-native",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        max_tokens=300,
        token_budget=10_000,
        cooldown_ticks=3,
    ),
}


def get_profile(profile_id: str) -> AgentProfile:
    """Retorna o perfil pelo ID. Usa 'claude-kiro' como fallback padrão."""
    return BUILTIN_PROFILES.get(profile_id, BUILTIN_PROFILES["claude-kiro"])


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
