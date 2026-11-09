"""
Intent Registry - ثبت و مدیریت intentها
==========================================
با این ساختار، هر handler خودش intentهاش رو ثبت می‌کنه.
اضافه کردن intent جدید = فقط ۱ دکوراتور + ۱ تابع
"""
from typing import Callable, Dict, List, Any, Optional
import re


class IntentRegistry:
    """
    Registry مرکزی intentها

    الگو:
        @IntentRegistry.register(
            name="my_intent",
            patterns=[r"...", r"..."],
            priority=90,
            confidence=0.9,
        )
        def handle_my_intent(question, entities, user_id, is_admin):
            return Formatters.response(...)
    """

    _intents: Dict[str, Dict[str, Any]] = {}

    # ============================================================
    # ★ دکوراتور ثبت
    # ============================================================
    @classmethod
    def register(
        cls,
        name: str,
        patterns: List[str],
        priority: int = 50,
        confidence: float = 0.8,
        description: str = "",
        admin_only: bool = False,
        keywords: Optional[List[str]] = None,
    ):
        """
        دکوراتور برای ثبت یه intent

        Args:
            name: نام یکتای intent
            patterns: لیست regexها
            priority: اولویت (بالاتر = مهم‌تر)
            confidence: اطمینان (0-1)
            description: توضیح (برای debug)
            admin_only: فقط ادمین بتونه استفاده کنه
            keywords: کلیدواژه‌های کمکی (اختیاری)
        """
        def decorator(handler_func: Callable):
            if name in cls._intents:
                raise ValueError(
                    f"Intent '{name}' قبلاً ثبت شده! "
                    f"اسم دیگه‌ای انتخاب کن."
                )

            # کامپایل regexها
            compiled = []
            for p in patterns:
                try:
                    compiled.append(re.compile(p))
                except re.error as e:
                    raise ValueError(
                        f"regex نامعتبر در intent '{name}': {p} → {e}"
                    )

            cls._intents[name] = {
                "name": name,
                "patterns": compiled,
                "priority": priority,
                "confidence": confidence,
                "description": description,
                "admin_only": admin_only,
                "keywords": keywords or [],
                "handler": handler_func,
            }

            return handler_func

        return decorator

    # ============================================================
    # ★ دسترسی‌ها
    # ============================================================
    @classmethod
    def get(cls, name: str) -> Optional[Dict[str, Any]]:
        return cls._intents.get(name)

    @classmethod
    def all(cls) -> Dict[str, Dict[str, Any]]:
        return cls._intents.copy()

    @classmethod
    def names(cls) -> List[str]:
        return list(cls._intents.keys())

    @classmethod
    def count(cls) -> int:
        return len(cls._intents)

    # ============================================================
    # ★ تشخیص intent از متن
    # ============================================================
    @classmethod
    def detect(cls, text: str, is_admin: bool = False):
        """
        تشخیص intent از روی متن

        Returns:
            (intent_name, entities, confidence)
        """
        matches = []

        for name, item in cls._intents.items():
            # اگه admin_only بود و کاربر ادمین نیست، skip
            if item.get("admin_only") and not is_admin:
                continue

            for pattern in item["patterns"]:
                m = pattern.search(text)
                if m:
                    score = item["priority"] * item["confidence"]
                    matches.append({
                        "name": name,
                        "priority": item["priority"],
                        "confidence": item["confidence"],
                        "score": score,
                        "entities": m.groupdict() or {},
                    })
                    break  # فقط اولین pattern این intent

        if not matches:
            return "unknown", {}, 0.0

        # انتخاب بهترین
        matches.sort(key=lambda x: x["score"], reverse=True)
        best = matches[0]
        return best["name"], best["entities"], best["confidence"]

    # ============================================================
    # ★ اجرای intent
    # ============================================================
    @classmethod
    def execute(cls, name: str, question: str, entities: dict,
                user_id: int, is_admin: bool):
        item = cls._intents.get(name)
        if not item:
            return None
        return item["handler"](question, entities, user_id, is_admin)

    # ============================================================
    # ★ وضعیت (debug)
    # ============================================================
    @classmethod
    def info(cls) -> Dict[str, Any]:
        return {
            "total": len(cls._intents),
            "intents": [
                {
                    "name": name,
                    "priority": item["priority"],
                    "confidence": item["confidence"],
                    "patterns_count": len(item["patterns"]),
                    "description": item["description"],
                    "admin_only": item["admin_only"],
                }
                for name, item in cls._intents.items()
            ]
        }

    @classmethod
    def clear(cls):
        """فقط برای تست"""
        cls._intents.clear()