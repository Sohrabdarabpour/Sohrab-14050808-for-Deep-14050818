"""
Context Memory - حافظه گفتگو
==============================
- نگهداری تاریخچه گفتگو برای هر کاربر
- TTL خودکار (پاک‌سازی بعد از بی‌کاری)
- محدودیت تعداد تورن‌ها
- thread-safe ساده
- متدهای کاربردی برای دسترسی
"""
from collections import defaultdict
from datetime import datetime, timedelta
import threading


class ConversationContext:
    """حافظه هر کاربر برای پیگیری گفتگو"""

    # ============================================================
    # ★ تنظیمات
    # ============================================================
    MAX_TURNS = 15           # حداکثر تعداد تورن نگه‌داری
    TTL_MINUTES = 30         # زمان بی‌کاری برای پاک‌سازی
    MAX_ANSWER_LENGTH = 2000 # حداکثر طول پاسخ ذخیره‌شده
    MAX_QUESTION_LENGTH = 500

    # ============================================================
    # ★ ذخیره‌سازی + قفل
    # ============================================================
    _store = defaultdict(list)   # user_id -> list of turns
    _lock = threading.Lock()

    # ============================================================
    # ★ افزودن تورن جدید
    # ============================================================
    @classmethod
    def add_turn(cls, user_id, question, intent, entities, answer):
        """
        افزودن یک تورن (سوال + پاسخ) به تاریخچه

        Args:
            user_id: شناسه کاربر
            question: متن سوال
            intent: intent تشخیص داده شده
            entities: پارامترهای استخراج شده
            answer: پاسخ داده شده (HTML)
        """
        if not user_id:
            return

        # ★ محدودسازی طول‌ها
        question = str(question or "")[:cls.MAX_QUESTION_LENGTH]
        answer = str(answer or "")[:cls.MAX_ANSWER_LENGTH]

        turn = {
            "q": question,
            "intent": intent or "unknown",
            "entities": entities or {},
            "answer": answer,
            "at": datetime.now(),
        }

        with cls._lock:
            # ★ پاک‌سازی قبلی‌ها
            cls._cleanup_expired(user_id)

            # ★ افزودن
            cls._store[user_id].append(turn)

            # ★ نگه‌داشتن فقط آخرین N
            if len(cls._store[user_id]) > cls.MAX_TURNS:
                cls._store[user_id] = cls._store[user_id][-cls.MAX_TURNS:]

    # ============================================================
    # ★ دریافت آخرین تورن
    # ============================================================
    @classmethod
    def get_last(cls, user_id):
        """
        دریافت آخرین تورن کاربر
        Returns: dict یا None
        """
        if not user_id:
            return None

        with cls._lock:
            turns = cls._store.get(user_id, [])
            if not turns:
                return None

            last = turns[-1]

            # ★ چک TTL
            if datetime.now() - last["at"] > timedelta(minutes=cls.TTL_MINUTES):
                cls._store[user_id] = []
                return None

            return last

    # ============================================================
    # ★ دریافت آخرین intent
    # ============================================================
    @classmethod
    def get_last_intent(cls, user_id):
        """دریافت intent آخرین تورن"""
        last = cls.get_last(user_id)
        return last["intent"] if last else None

    # ============================================================
    # ★ دریافت آخرین entities
    # ============================================================
    @classmethod
    def get_last_entities(cls, user_id):
        """دریافت entities آخرین تورن"""
        last = cls.get_last(user_id)
        return last.get("entities", {}) if last else {}

    # ============================================================
    # ★ دریافت تاریخچه (برای LLM)
    # ============================================================
    @classmethod
    def get_history(cls, user_id, limit=4):
        """
        دریافت تاریخچه آخرین N تورن (برای ارسال به LLM)

        Args:
            user_id: شناسه کاربر
            limit: حداکثر تعداد تورن

        Returns:
            list of {"q": str, "answer": str}
        """
        if not user_id:
            return []

        with cls._lock:
            turns = cls._store.get(user_id, [])

            # ★ فیلتر بر اساس TTL
            cutoff = datetime.now() - timedelta(minutes=cls.TTL_MINUTES)
            turns = [t for t in turns if t["at"] > cutoff]

            # ★ آخرین N
            turns = turns[-limit:] if limit else turns

            return [
                {
                    "q": t.get("q", ""),
                    "intent": t.get("intent", ""),
                    "answer": t.get("answer", ""),
                    "at": t.get("at"),
                }
                for t in turns
            ]

    # ============================================================
    # ★ تعداد تورن‌های ذخیره‌شده
    # ============================================================
    @classmethod
    def count(cls, user_id):
        """تعداد تورن‌های کاربر"""
        if not user_id:
            return 0
        with cls._lock:
            cls._cleanup_expired(user_id)
            return len(cls._store.get(user_id, []))

    # ============================================================
    # ★ پاک‌کردن تاریخچه یک کاربر
    # ============================================================
    @classmethod
    def clear(cls, user_id):
        """پاک‌کردن تاریخچه کاربر"""
        if not user_id:
            return
        with cls._lock:
            cls._store[user_id] = []

    # ============================================================
    # ★ پاک‌کردن کل تاریخچه
    # ============================================================
    @classmethod
    def clear_all(cls):
        """پاک‌کردن تاریخچه همه کاربران"""
        with cls._lock:
            cls._store.clear()

    # ============================================================
    # ★ پاک‌سازی خودکار (داخلی)
    # ============================================================
    @classmethod
    def _cleanup_expired(cls, user_id=None):
        """
        پاک‌سازی تورن‌های منقضی
        اگه user_id بدی → فقط همون کاربر
        اگه None → همه کاربران
        """
        cutoff = datetime.now() - timedelta(minutes=cls.TTL_MINUTES)

        if user_id:
            turns = cls._store.get(user_id, [])
            cls._store[user_id] = [t for t in turns if t["at"] > cutoff]
            return

        # ★ برای همه
        for uid in list(cls._store.keys()):
            turns = cls._store[uid]
            cls._store[uid] = [t for t in turns if t["at"] > cutoff]
            if not cls._store[uid]:
                del cls._store[uid]

    # ============================================================
    # ★ پاک‌سازی دستی (برای cron یا شروع به کار)
    # ============================================================
    @classmethod
    def cleanup_all(cls):
        """پاک‌سازی همه تورن‌های منقضی (برای cron)"""
        with cls._lock:
            cls._cleanup_expired()
            return len(cls._store)

    # ============================================================
    # ★ آمار (برای debug)
    # ============================================================
    @classmethod
    def stats(cls):
        """آمار کلی حافظه"""
        with cls._lock:
            cls._cleanup_expired()
            return {
                "users_count": len(cls._store),
                "total_turns": sum(len(v) for v in cls._store.values()),
                "max_turns": cls.MAX_TURNS,
                "ttl_minutes": cls.TTL_MINUTES,
            }