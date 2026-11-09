"""تنظیمات اتصال به LLM

Provider پیش‌فرض: AvalAI (سرویس واسط ایرانی، بدون VPN)
Providerهای پشتیبان: ollama | groq | openai | deepseek

⚠️ هیچ کلید API‌ای در این فایل نوشته نمی‌شود.
همه‌ی مقادیر از متغیرهای محیطی (فایل .env) خوانده می‌شوند.
نمونه‌ی کامل: .env.example
"""

import os


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class LLMConfig:
    """تنظیمات LLM — همه از متغیر محیطی خوانده می‌شود."""

    # ============================================================
    # ★★★ Provider فعال ★★★
    # ============================================================
    # مقادیر ممکن: avalai | ollama | groq | openai | deepseek
    PROVIDER = os.environ.get("LLM_PROVIDER", "deepseek").strip().lower()

    # ============================================================
    # ★ AvalAI — سرویس واسط ایرانی (بدون VPN)
    # ============================================================
    AVALAI_API_KEY = os.environ.get("AVALAI_API_KEY", "")
    AVALAI_BASE_URL = os.environ.get("AVALAI_BASE_URL", "https://api.avalai.ir/v1")
    AVALAI_MODEL = os.environ.get("AVALAI_MODEL", "gpt-5.4-mini")

    # ============================================================
    # ★ DeepSeek — پلتفرم رسمی (نیازمند VPN)
    # ============================================================
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    # ============================================================
    # ★ Ollama (محلی)
    # ============================================================
    OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "ollama")
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

    # ============================================================
    # ★ Groq
    # ============================================================
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    # ============================================================
    # ★ OpenAI
    # ============================================================
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    # ============================================================
    # ★ تنظیمات عمومی
    # ============================================================
    MAX_TOKENS = _env_int("LLM_MAX_TOKENS", 1500)
    TEMPERATURE = _env_float("LLM_TEMPERATURE", 0.3)
    TIMEOUT = _env_int("LLM_TIMEOUT", 60)
    ENABLED = _env_bool("LLM_ENABLED", True)

    @classmethod
    def get_active_config(cls):
        """برمی‌گردونه: (api_key, base_url, model)"""
        if not cls.ENABLED:
            return None, None, None

        provider = cls.PROVIDER

        if provider == "avalai" and cls.AVALAI_API_KEY:
            return cls.AVALAI_API_KEY, cls.AVALAI_BASE_URL, cls.AVALAI_MODEL

        if provider == "deepseek" and cls.DEEPSEEK_API_KEY:
            return cls.DEEPSEEK_API_KEY, cls.DEEPSEEK_BASE_URL, cls.DEEPSEEK_MODEL

        if provider == "ollama":
            return cls.OLLAMA_API_KEY, cls.OLLAMA_BASE_URL, cls.OLLAMA_MODEL

        if provider == "groq" and cls.GROQ_API_KEY:
            return cls.GROQ_API_KEY, cls.GROQ_BASE_URL, cls.GROQ_MODEL

        if provider == "openai" and cls.OPENAI_API_KEY:
            return cls.OPENAI_API_KEY, cls.OPENAI_BASE_URL, cls.OPENAI_MODEL

        return None, None, None

    @classmethod
    def is_available(cls):
        """آیا سرویس AI آماده است؟"""
        api_key, _, _ = cls.get_active_config()
        return bool(api_key)

    @classmethod
    def describe(cls):
        """وضعیت تنظیمات بدون افشای کلید (برای /assistant/llm-health)"""
        api_key, base_url, model = cls.get_active_config()
        return {
            "provider": cls.PROVIDER,
            "enabled": cls.ENABLED,
            "configured": bool(api_key),
            "base_url": base_url,
            "model": model,
            "timeout": cls.TIMEOUT,
        }
