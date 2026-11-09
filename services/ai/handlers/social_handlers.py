"""Handlerهای احوال‌پرسی و گفت‌وگوی روزمره.

نکته‌ی مهم: همه‌ی الگوها با `^` و `$` لنگر انداخته‌اند تا فقط وقتی پیام
**کاملاً** یک احوال‌پرسی است فعال شوند. مثلاً «سلام، چند سند داریم؟» یک
سؤال واقعی است و نباید به intent سلام‌و‌علیکم برود.
"""

from services.ai.formatters import Formatters
from services.ai.handlers.base import BaseHandler
from services.ai.registry import IntentRegistry


def _first_name(user_id):
    """نام کوچک کاربر برای صمیمی‌تر شدن پاسخ (اگر در دسترس باشد)."""
    if not user_id:
        return ""
    try:
        from database.repositories.users import get_user

        user = get_user(user_id) or {}
        full_name = (user.get("full_name") or "").strip()
        return full_name.split()[0] if full_name else ""
    except Exception:  # noqa: BLE001 - پاسخ نباید به‌خاطر نام خراب شود
        return ""


def _time_greeting():
    """سلام متناسب با ساعت روز."""
    try:
        from helpers.date_helper import now_tehran

        hour = now_tehran().hour
    except Exception:  # noqa: BLE001
        return "سلام"

    if 4 <= hour < 12:
        return "صبح بخیر"
    if 12 <= hour < 17:
        return "وقت بخیر"
    if 17 <= hour < 21:
        return "عصر بخیر"
    return "شب بخیر"


SOCIAL_SUGGESTIONS = ["کارهای من", "آمار کلی", "لیست پروژه‌ها", "راهنما"]


class SocialHandlers(BaseHandler):
    """احوال‌پرسی، تشکر، خداحافظی و معرفی دستیار"""

    # ============================================================
    # ★ ۱. سلام
    # ============================================================
    @IntentRegistry.register(
        name="greeting",
        patterns=[
            r"^\s*(سلام|سلام علیکم|درود|صبح بخیر|صبح‌بخیر|عصر بخیر|شب بخیر|"
            r"وقت بخیر|روز بخیر|hi|hello)[\s!؟?.]*$",
        ],
        priority=96,
        confidence=1.0,
        description="سلام و احوال‌پرسی ابتدای گفتگو",
    )
    @staticmethod
    def handle_greeting(question, entities, user_id, is_admin):
        name = _first_name(user_id)
        greeting = _time_greeting()

        who = f" <strong>{Formatters._safe(name)}</strong>" if name else ""

        answer = (
            f'<i class="fa-solid fa-hand-sparkles" style="color:#10b981"></i> '
            f'<strong>{greeting}{who}!</strong> 🌿\n\n'
            f'<span class="text-muted">من دستیار هوشمند سامانه اسناد هستم. '
            f'می‌تونم آمار بدم، لیست بسازم، جستجو کنم یا وضعیت پروژه‌ها و '
            f'پیمانکاران رو بگم.</span>'
        )

        return Formatters.response(answer, "text", suggestions=SOCIAL_SUGGESTIONS)

    # ============================================================
    # ★ ۲. چطوری؟
    # ============================================================
    @IntentRegistry.register(
        name="how_are_you",
        patterns=[
            r"^\s*(خوبی|خوب هستی|چطوری|چه خبر|حالت چطوره|حال شما چطوره|"
            r"چطور هستی|خوبی تو)[\s!؟?.]*$",
        ],
        priority=95,
        confidence=1.0,
        description="احوال‌پرسی از دستیار",
    )
    @staticmethod
    def handle_how_are_you(question, entities, user_id, is_admin):
        name = _first_name(user_id)
        who = f" {Formatters._safe(name)}" if name else ""

        answer = (
            f'<i class="fa-solid fa-face-smile" style="color:#f59e0b"></i> '
            f'<strong>من خوبم، ممنون که پرسیدی{who}!</strong> 🌿\n\n'
            f'<span class="text-muted">آماده‌ام کمکت کنم — کافیه بگی چی می‌خوای.</span>'
        )

        return Formatters.response(answer, "text", suggestions=SOCIAL_SUGGESTIONS)

    # ============================================================
    # ★ ۳. تشکر
    # ============================================================
    @IntentRegistry.register(
        name="thanks",
        patterns=[
            r"^\s*(ممنون|مرسی|سپاس|سپاسگزارم|متشکرم|دستت درد نکنه|"
            r"دست شما درد نکنه|لطف کردی|لطف کردید|خیلی ممنون)[متم]?[\s!؟?.]*$",
        ],
        priority=95,
        confidence=1.0,
        description="تشکر از دستیار",
    )
    @staticmethod
    def handle_thanks(question, entities, user_id, is_admin):
        answer = (
            f'<i class="fa-solid fa-heart" style="color:#ef4444"></i> '
            f'<strong>خواهش می‌کنم!</strong> 🙏\n\n'
            f'<span class="text-muted">اگر سوال دیگری داشتی، در خدمتم.</span>'
        )
        return Formatters.response(answer, "text", suggestions=SOCIAL_SUGGESTIONS)

    # ============================================================
    # ★ ۴. خداحافظی
    # ============================================================
    @IntentRegistry.register(
        name="goodbye",
        patterns=[
            r"^\s*(خداحافظ|خدا حافظ|خدانگهدار|بای|فعلا|فعلاً|"
            r"خداحافظت|خدا نگهدار)[\s!؟?.]*$",
        ],
        priority=95,
        confidence=1.0,
        description="خداحافظی",
    )
    @staticmethod
    def handle_goodbye(question, entities, user_id, is_admin):
        name = _first_name(user_id)
        who = f" {Formatters._safe(name)}" if name else ""

        answer = (
            f'<i class="fa-solid fa-hand-wave" style="color:#3D8499"></i> '
            f'<strong>خدانگهدار{who}!</strong> 🙏\n\n'
            f'<span class="text-muted">هر وقت کاری داشتی سراغم بیا.</span>'
        )
        return Formatters.response(answer, "text", suggestions=["راهنما"])

    # ============================================================
    # ★ ۵. تو کی هستی؟
    # ============================================================
    @IntentRegistry.register(
        name="who_are_you",
        patterns=[
            r"^\s*(تو کی هستی|شما کی هستید|اسمت چیه|اسم شما چیه|"
            r"تو چیکاره‌ای|تو چی هستی|کی هستی)[\s!؟?.]*$",
        ],
        priority=94,
        confidence=1.0,
        description="معرفی دستیار",
    )
    @staticmethod
    def handle_who_are_you(question, entities, user_id, is_admin):
        total = IntentRegistry.count()

        answer = (
            f'<i class="fa-solid fa-robot" style="color:#3D8499"></i> '
            f'<strong>من دستیار هوشمند سامانه اسناد هستم.</strong>\n\n'
            f'<span class="text-muted">'
            f'روی داده‌های همین سیستم کار می‌کنم — نه اینترنت. '
            f'الان <strong>{total}</strong> قابلیت دارم:'
            f'</span>\n\n'
            f'<i class="fa-solid fa-chart-simple" style="color:#667eea"></i> '
            f'آمار و شمارش اسناد، پروژه‌ها و پیمانکاران\n'
            f'<i class="fa-solid fa-list-check" style="color:#10b981"></i> '
            f'لیست کارها، دیرکردها و اسناد امروز\n'
            f'<i class="fa-solid fa-magnifying-glass" style="color:#3D8499"></i> '
            f'جستجو در اسناد، پروژه‌ها و پیمانکاران\n'
            f'<i class="fa-solid fa-arrow-trend-up" style="color:#f59e0b"></i> '
            f'تحلیل روند، رتبه‌بندی و عملکرد'
        )

        return Formatters.response(answer, "text", suggestions=SOCIAL_SUGGESTIONS)
