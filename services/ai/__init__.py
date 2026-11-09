"""
پکیج هوش مصنوعی دستیار
=========================
"""

from .assistant_service import AssistantService
from .cache import Cache
from .context import ConversationContext
from .nlu import NLU
from .formatters import Formatters
from .registry import IntentRegistry

# LLM (اختیاری)
try:
    from .llm_config import LLMConfig
    from .llm_service import LLMService
    from .llm_tools import LLMTools
    LLM_AVAILABLE = True
except ImportError:
    LLMConfig = None
    LLMService = None
    LLMTools = None
    LLM_AVAILABLE = False

# Handlers
try:
    from .handlers import (
        StatusHandlers,
        ListHandlers,
        AnalyticsHandlers,
        SearchHandlers,
    )
    HANDLERS_AVAILABLE = True
except ImportError:
    StatusHandlers = None
    ListHandlers = None
    AnalyticsHandlers = None
    SearchHandlers = None
    HANDLERS_AVAILABLE = False


__all__ = [
    "AssistantService",
    "Cache",
    "ConversationContext",
    "NLU",
    "Formatters",
    "IntentRegistry",
    "LLMConfig",
    "LLMService",
    "LLMTools",
    "LLM_AVAILABLE",
    "StatusHandlers",
    "ListHandlers",
    "AnalyticsHandlers",
    "SearchHandlers",
    "HANDLERS_AVAILABLE",
]