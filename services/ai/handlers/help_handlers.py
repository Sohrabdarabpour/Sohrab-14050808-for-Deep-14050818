"""Handler راهنمای دستیار.

چرا لازم است: پاسخ‌های «نامفهوم» و «خالی» به کاربر پیشنهاد می‌دهند
«راهنما» بنویسد، ولی هیچ intent‌ای این عبارت را نمی‌شناخت؛ در نتیجه کاربر
در حلقه می‌افتاد. این handler همان intent را ثبت می‌کند.
"""

from services.ai.handlers.base import BaseHandler
from services.ai.registry import IntentRegistry


class HelpHandlers(BaseHandler):
    """راهنمای دستیار و فهرست قابلیت‌ها"""

    @IntentRegistry.register(
        name="help",
        patterns=[
            r"^\s*(راهنما|راهنمایی|کمک|کمکی|help)\s*[؟?!]*\s*$",
            r"(چه|چی)\s*(کارایی|کاری|کارهایی|کارها).{0,20}(داری|داری؟|می‌تونی|می‌توانی|بلدی)",
            r"(قابلیت|قابلیت‌ها|امکانات|دستورات).{0,15}(چیست|چیه|چی|هست)",
            r"(چطور|چگونه).{0,15}(استفاده|کار).{0,10}(کنم|بکنم)",
        ],
        priority=99,
        confidence=1.0,
        description="راهنمای دستیار و فهرست قابلیت‌ها",
    )
    @staticmethod
    def handle_help(question, entities, user_id, is_admin):
        # import داخل تابع برای جلوگیری از import چرخه‌ای
        from services.ai.assistant_service import AssistantService

        return AssistantService._help_response()
