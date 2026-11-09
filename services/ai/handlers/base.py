"""
Base Handler - کلاس پایه برای همه Handlerها
============================================
"""
from services.ai.registry import IntentRegistry
from services.ai.formatters import Formatters


class BaseHandler:
    """
    کلاس پایه Handlerها

    روش استفاده:
        class MyHandler(BaseHandler):
            @IntentRegistry.register(
                name="my_intent",
                patterns=[r"..."],
                priority=90,
            )
            @staticmethod
            def handle_my_intent(question, entities, user_id, is_admin):
                return Formatters.response(...)
    """

    @classmethod
    def register_all(cls):
        """برای سازگاری - intentها خودکار با دکوراتور ثبت می‌شن"""
        pass