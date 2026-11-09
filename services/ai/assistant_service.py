"""
دستیار هوشمند اسناد - نسخه Enterprise v3.0
============================================
★ معماری Registry-based
"""
import time
from collections import defaultdict

from services.ai.nlu import NLU
from services.ai.context import ConversationContext
from services.ai.formatters import Formatters
from services.ai.registry import IntentRegistry
from services.ai.llm_service import LLMService
from services.ai.llm_config import LLMConfig
from services.ai.sanitizer import sanitize_html



# ============================================================
# ★★★ import handlers برای ثبت intentها ★★★
# ============================================================
from services.ai.handlers import (   # noqa: F401
    StatusHandlers,
    ListHandlers,
    AnalyticsHandlers,
    SearchHandlers,
    GroupHandlers,   # ★ اضافه کن
    ExpertDocumentsHandlers,
    ClassificationHandlers,
    HelpHandlers,      # ★ راهنما
    SocialHandlers,    # ★ احوال‌پرسی
    ProjectHandlers,   # ★ پروژه/پیمانکار/ناحیه
    FilterHandlers,    # ★ جستجوی پیشرفته + اکسل

    )


class AssistantService:
    """موتور هوشمند اسناد — نسخه Registry-based"""

    _rate_store = defaultdict(list)
    RATE_LIMIT = 30
    RATE_WINDOW = 60

    @classmethod
    def ask(cls, question, user_id=None, is_admin=False, debug=False):
        start_time = time.time()

        if not cls._check_rate_limit(user_id):
            return Formatters.response(
                '<i class="fa-solid fa-triangle-exclamation" '
                'style="color:#ef4444"></i> '
                'تعداد درخواست‌های شما زیاد است. لطفاً چند لحظه صبر کنید.',
                "error",
                suggestions=["راهنما"]
            )

        if not question or not str(question).strip():
            return Formatters.response(
                '<i class="fa-solid fa-circle-question" '
                'style="color:#3D8499"></i> سوالی وارد نکردید.',
                "empty",
                suggestions=["راهنما", "کارهای من", "آمار کلی"]
            )

        if len(question) > 500:
            question = question[:500]

        normalized = NLU.normalize(question)
        cleaned = NLU.clean(question)

        intent_name, entities, confidence = IntentRegistry.detect(
            cleaned, is_admin=is_admin
        )

        if intent_name == "unknown":
            context_response = cls._try_context_resolution(normalized, user_id)
            if context_response:
                return context_response

            if LLMConfig.is_available():
                llm_response = cls._ask_llm(question, user_id, is_admin, debug)
                if llm_response:
                    ConversationContext.add_turn(
                        user_id, question, "llm", {},
                        llm_response.get("answer", "")
                    )
                    return llm_response

        result = None
        if intent_name != "unknown":
            try:
                result = IntentRegistry.execute(
                    intent_name, question, entities, user_id, is_admin
                )
            except Exception as e:
                if debug:
                    print(f"⚠️ Handler error for '{intent_name}': {e}")
                result = None

        if result is None:
            if intent_name == "unknown":
                result = cls._unknown_response(question)
            else:
                result = Formatters.response(
                    f'<i class="fa-solid fa-bug" style="color:#ef4444"></i> '
                    f'خطا در اجرای intent «{intent_name}».',
                    "error",
                    suggestions=["راهنما", "کارهای من"]
                )

        result["meta"] = {
            **(result.get("meta") or {}),
            "intent": intent_name,
            "confidence": confidence,
            "elapsed_ms": int((time.time() - start_time) * 1000),
        }

        if debug:
            result["meta"]["normalized"] = normalized
            result["meta"]["cleaned"] = cleaned
            result["meta"]["entities"] = entities

        ConversationContext.add_turn(
            user_id, question, intent_name, entities, result.get("answer", "")
        )

        return result

    @classmethod
    def _ask_llm(cls, question, user_id, is_admin, debug=False):
        try:
            context_turns = ConversationContext.get_history(user_id, limit=4)

            result = LLMService.ask(
                question=question,
                user_id=user_id,
                is_admin=is_admin,
                context=context_turns
            )

            if not result.get("success"):
                if debug:
                    print(f"⚠️ LLM error: {result.get('error')}")
                return None

            answer = result.get("answer", "").strip()
            if not answer:
                return None

            # ★ خروجی مدل قابل اعتماد نیست (prompt injection از دادهٔ اسناد)؛
            # فقط تگ‌های بی‌خطر نگه داشته می‌شوند.
            answer = sanitize_html(answer).strip()
            if not answer:
                return None

            meta = {
                "source": "llm",
                "tools_used": result.get("tools_used", []),
                "iterations": result.get("iterations", 1),
            }

            suggestions = cls._build_llm_suggestions(result.get("tools_used", []))

            return Formatters.response(
                answer, "text",
                suggestions=suggestions,
                meta=meta,
            )
        except Exception as e:
            if debug:
                print(f"⚠️ LLM exception: {e}")
            return None

    @staticmethod
    def _build_llm_suggestions(tools_used):
        if not tools_used:
            return ["کارهای من", "آمار کلی", "راهنما"]

        names = {t.get("name") for t in tools_used}
        suggestions = []

        if "get_department_ranking" in names:
            suggestions.extend(["روند ماهانه چطوره؟", "پرمشغله‌ترین کارشناس کیست؟"])
        if "get_performance_summary" in names:
            suggestions.extend(["رتبه‌بندی دپارتمان‌ها", "روند ماهانه"])
        if "get_monthly_trend" in names:
            suggestions.extend(["بهترین ماه کدوم بود؟", "مقایسه با سال قبل"])
        if "search_documents" in names:
            suggestions.extend(["جزئیات اولین سند", "کارهای من"])
        if "list_users" in names or "get_top_experts" in names:
            suggestions.extend(["آمار کلی", "گزارش دپارتمان‌ها"])

        if not suggestions:
            suggestions = ["آمار کلی", "کارهای من", "راهنما"]

        return suggestions[:3]

    @classmethod
    def _check_rate_limit(cls, user_id):
        if not user_id:
            return True
        now = time.time()
        cls._rate_store[user_id] = [
            t for t in cls._rate_store[user_id]
            if now - t < cls.RATE_WINDOW
        ]
        if len(cls._rate_store[user_id]) >= cls.RATE_LIMIT:
            return False
        cls._rate_store[user_id].append(now)
        return True

    @classmethod
    def _try_context_resolution(cls, normalized, user_id):
        last = ConversationContext.get_last(user_id)
        if not last:
            return None

        if any(w in normalized for w in ["بیشتر", "ادامه", "توضیح", "جزئیات", "کامل"]):
            prev_q = last.get("q", "")
            return Formatters.response(
                f'<i class="fa-solid fa-circle-info" style="color:#3D8499"></i> '
                f'سوال قبلی شما: <strong>«{prev_q}»</strong>\n\n'
                f'<i class="fa-solid fa-lightbulb" style="color:#f59e0b"></i> '
                f'لطفاً سوال دقیق‌تری بپرسید یا از پیشنهادات زیر استفاده کنید.',
                "text",
                suggestions=["کارهای من", "آمار کلی", "راهنما"]
            )

        if len(normalized.split()) <= 3:
            prev_intent = last.get("intent", "")
            if prev_intent.startswith("count_"):
                return None

        return None

    @classmethod
    def _help_response(cls):
        intents = IntentRegistry.all()
        total = len(intents)

        text = (
            '<i class="fa-solid fa-robot" style="color:#3D8499"></i> '
            '<strong>راهنمای دستیار هوشمند</strong>\n\n'
            f'<span class="text-muted">تعداد قابلیت‌ها: </span>'
            f'<strong class="num-highlight">{total}</strong>\n\n'
            '<i class="fa-solid fa-chart-pie" style="color:#667eea"></i> '
            '<strong>آمار و شمارش:</strong>\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> چند سند در حال بررسی دارم؟\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> چند سند تکمیل شده؟\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> آمار کلی اسناد\n\n'
            '<i class="fa-solid fa-list-check" style="color:#10b981"></i> '
            '<strong>لیست‌ها:</strong>\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> کارهای من چیه؟\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> اسناد دیرکرد\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> اسناد امروز\n\n'
            '<i class="fa-solid fa-arrow-trend-up" style="color:#f59e0b"></i> '
            '<strong>تحلیل‌ها:</strong>\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> پرمشغله‌ترین کارشناس کیست؟\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> روند هفتگی\n\n'
            '<i class="fa-solid fa-magnifying-glass" style="color:#3D8499"></i> '
            '<strong>جستجو:</strong>\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> جستجو قرارداد'
        )
        return Formatters.response(
            text, "help",
            suggestions=["کارهای من", "آمار کلی", "اسناد دیرکرد"]
        )

    @staticmethod
    def _unknown_response(question):
        if len(str(question).strip()) < 4:
            suggestions = ["راهنما", "کارهای من", "آمار کلی"]
            hint = "سوال شما خیلی کوتاه بود."
        else:
            suggestions = ["راهنما", "کارهای من", "چند سند در حال بررسی دارم؟", "آمار کلی"]
            hint = "منظور شما رو متوجه نشدم."

        return Formatters.response(
            f'<i class="fa-solid fa-circle-question" style="color:#f59e0b"></i> '
            f'<strong>{hint}</strong>\n\n'
            f'<i class="fa-solid fa-lightbulb" style="color:#f59e0b"></i> '
            f'می‌تونید از نمونه‌های زیر استفاده کنید یا '
            f'<strong>راهنما</strong> بنویسید.',
            "unknown",
            suggestions=suggestions
        )