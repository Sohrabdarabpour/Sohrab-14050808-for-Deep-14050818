"""
اتصال به LLM با Function Calling
=================================
- پشتیبانی از Ollama / Groq / OpenAI
- تبدیل خودکار تاریخ به شمسی (با DateHelper)
- هشدار به LLM درباره تاریخ‌های شمسی
- مدیریت خطا و retry
- لاگ دقیق در حالت debug
"""
import json
import re
import time
from datetime import datetime

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from services.ai.llm_config import LLMConfig
from services.ai.llm_tools import LLMTools
from helpers.date_helper import DateHelper


class LLMService:
    """سرویس اتصال به LLM با Function Calling"""

    # ============================================================
    # ★ System Prompt با هشدار تاریخ شمسی
    # ============================================================
    SYSTEM_PROMPT = """شما «دستیار هوشمند اسناد» یک سامانه مدیریت اسناد مهندسی هستید.

وظیفه شما:
- پاسخ دقیق و کوتاه به سوالات کاربر درباره اسناد
- استفاده از توابع ارائه‌شده برای گرفتن اطلاعات از دیتابیس
- هرگز اطلاعات را از خودت نساز — همیشه از توابع استفاده کن

★ نکات مهم درباره تاریخ‌ها:
- تمام تاریخ‌هایی که در نتایج توابع می‌بینی، **از قبل به شمسی تبدیل شده‌اند**
- شما نیازی به تبدیل نداری — فقط همان‌طور که هست نمایش بده
- فرمت تاریخ‌ها: YYYY/MM/DD با اعداد فارسی (مثلاً ۱۴۰۳/۰۲/۲۶)
- اگر تاریخی با سال بالای ۱۷۰۰ دیدی (میلادی)، اون رو به شمسی تبدیل کن

قواعد پاسخ‌دهی:
1. اگر سوال نیاز به داده داره، حتماً تابع مربوطه رو صدا بزن
2. پاسخ رو به فارسی روان و با جزئیات بنویس
3. از آیکون‌های Font Awesome استفاده کن (نه ایموجی):
   - در حال بررسی: <i class="fa-solid fa-list-check"></i>
   - تکمیل: <i class="fa-solid fa-circle-check"></i>
   - متوقف: <i class="fa-solid fa-circle-pause"></i>
   - ابطال: <i class="fa-solid fa-circle-xmark"></i>
   - اطلاع: <i class="fa-solid fa-circle-info"></i>
   - آمار: <i class="fa-solid fa-chart-pie"></i>
   - لیست: <i class="fa-solid fa-list"></i>
   - سند: <i class="fa-solid fa-file-lines"></i>
   - هشدار: <i class="fa-solid fa-triangle-exclamation"></i>
   - موفقیت: <i class="fa-solid fa-champagne-glasses"></i>
   - کارشناس: <i class="fa-solid fa-user"></i>
   - گروه: <i class="fa-solid fa-folder-tree"></i>
   - رتبه ۱: <i class="fa-solid fa-medal" style="color:#f59e0b"></i>
   - رتبه ۲: <i class="fa-solid fa-award" style="color:#f59e0b"></i>
   - رتبه ۳: <i class="fa-solid fa-star" style="color:#f59e0b"></i>

4. اعداد مهم رو با <strong> برجسته کن
5. پاسخ‌ها کوتاه و مفید (حداکثر ۱۰ خط)
6. اگر سوال واضح نیست، از کاربر بپرس منظورش چیه

امروز (شمسی): {today_jalali}
امروز (میلادی): {today_gregorian}"""

    # ============================================================
    # ★ ساختار داخلی
    # ============================================================
    _client = None
    _model = None
    MAX_ITERATIONS = 5

    # ============================================================
    # ★ ساخت کلاینت (Lazy)
    # ============================================================
    @classmethod
    def _get_client(cls):
        """کلاینت OpenAI-compatible می‌سازه"""
        if cls._client is not None:
            return cls._client

        if not OPENAI_AVAILABLE:
            return None

        api_key, base_url, model = LLMConfig.get_active_config()
        if not api_key:
            return None

        try:
            cls._client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=LLMConfig.TIMEOUT,
            )
            cls._model = model
            return cls._client
        except Exception:
            return None

    @classmethod
    def reset_client(cls):
        """ریست کلاینت (برای تغییر تنظیمات)"""
        cls._client = None
        cls._model = None

    # ============================================================
    # ★ ورودی اصلی
    # ============================================================
    @classmethod
    def ask(cls, question, user_id, is_admin, context=None, debug=False):
        """
        ارسال سوال به LLM با Function Calling

        Args:
            question: متن سوال
            user_id: شناسه کاربر
            is_admin: آیا ادمین است
            context: لیست تورن‌های قبلی [{q, answer}]
            debug: نمایش لاگ

        Returns:
            dict: {
                "success": bool,
                "answer": str | None,
                "tools_used": [...],
                "iterations": int,
                "error": str | None
            }
        """
        # ---- ساخت کلاینت ----
        client = cls._get_client()
        if not client:
            return {
                "success": False,
                "answer": None,
                "error": "LLM not available",
                "tools_used": [],
            }

        # ---- ساخت System Prompt ----
        today_gregorian = datetime.now().strftime("%Y/%m/%d")
        today_jalali = DateHelper.format_jalali(today_gregorian)

        try:
            system = cls.SYSTEM_PROMPT.format(
                today_jalali=today_jalali,
                today_gregorian=today_gregorian,
            )
        except Exception:
            # اگه فرمت prompt خراب بود، از یک نسخه ساده استفاده کن
            system = (
                f"شما دستیار هوشمند اسناد هستید. "
                f"امروز: {today_jalali} شمسی ({today_gregorian} میلادی). "
                f"همیشه از توابع استفاده کن و پاسخ‌ها رو فارسی بنویس."
            )

        # ---- ساخت پیام‌ها ----
        messages = [{"role": "system", "content": system}]

        # ★ context قبلی (حداکثر ۴ تورن آخر)
        if context and isinstance(context, list):
            for turn in context[-4:]:
                if turn.get("q"):
                    messages.append({
                        "role": "user",
                        "content": str(turn["q"])[:500]
                    })
                if turn.get("answer"):
                    # ★ حذف HTML از پاسخ قبلی
                    clean = re.sub(r"<[^>]+>", "", str(turn["answer"]))
                    clean = re.sub(r"\s+", " ", clean).strip()[:500]
                    if clean:
                        messages.append({
                            "role": "assistant",
                            "content": clean
                        })

        messages.append({"role": "user", "content": question})

        # ---- دریافت Schema توابع ----
        try:
            tools = LLMTools.get_tools_schema(is_admin=is_admin)
        except Exception as e:
            return {
                "success": False,
                "answer": None,
                "error": f"Tools schema error: {e}",
                "tools_used": [],
            }

        tools_used = []
        start_time = time.time()

        # ============================================================
        # ★ حلقه Function Calling
        # ============================================================
        for iteration in range(cls.MAX_ITERATIONS):
            # ---- فراخوانی LLM ----
            try:
                response = client.chat.completions.create(
                    model=cls._model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=LLMConfig.TEMPERATURE,
                    max_tokens=LLMConfig.MAX_TOKENS,
                )
            except Exception as e:
                error_msg = str(e)

                # ★ پیام خطای واضح‌تر
                if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                    return {
                        "success": False,
                        "answer": None,
                        "error": (
                            "اتصال به سرویس AI برقرار نشد. "
                            "لطفاً مطمئن شو Ollama در حال اجراست."
                        ),
                        "tools_used": tools_used,
                    }

                if "model" in error_msg.lower() and "not found" in error_msg.lower():
                    return {
                        "success": False,
                        "answer": None,
                        "error": (
                            f"مدل '{cls._model}' پیدا نشد. "
                            f"لطفاً با 'ollama pull {cls._model}' دانلودش کن."
                        ),
                        "tools_used": tools_used,
                    }

                return {
                    "success": False,
                    "answer": None,
                    "error": f"LLM API error: {error_msg}",
                    "tools_used": tools_used,
                }

            if not response or not response.choices:
                return {
                    "success": False,
                    "answer": None,
                    "error": "Empty response from LLM",
                    "tools_used": tools_used,
                }

            msg = response.choices[0].message

            # ============================================================
            # ★ Tool Calls
            # ============================================================
            if msg.tool_calls:
                # ★ اضافه کردن پیام assistant با tool_calls
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        }
                        for tc in msg.tool_calls
                    ]
                })

                # ★ اجرای هر Tool
                for tc in msg.tool_calls:
                    fn_name = tc.function.name

                    # parse arguments
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    # اجرا
                    try:
                        result = LLMTools.execute(
                            fn_name, args, user_id, is_admin
                        )
                    except Exception as e:
                        result = {"error": f"اجرای {fn_name} خطا داد: {str(e)}"}

                    tools_used.append({
                        "name": fn_name,
                        "args": args,
                        "success": "error" not in result,
                    })

                    # ★ اضافه کردن نتیجه به messages
                    try:
                        content = json.dumps(result, ensure_ascii=False, default=str)
                    except Exception:
                        content = json.dumps({"error": "cannot serialize result"})

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content,
                    })

                    if debug:
                        elapsed = int((time.time() - start_time) * 1000)
                        print(f"  🔧 {fn_name}({args}) → {elapsed}ms")

                # ★ ادامه حلقه — LLM باید پاسخ نهایی رو بده
                continue

            # ============================================================
            # ★ پاسخ نهایی
            # ============================================================
            answer = (msg.content or "").strip()

            if not answer:
                return {
                    "success": False,
                    "answer": None,
                    "error": "Empty answer from LLM",
                    "tools_used": tools_used,
                }

            elapsed_ms = int((time.time() - start_time) * 1000)

            if debug:
                print(f"  ✅ پاسخ در {iteration + 1} iteration ({elapsed_ms}ms)")

            return {
                "success": True,
                "answer": answer,
                "tools_used": tools_used,
                "iterations": iteration + 1,
                "elapsed_ms": elapsed_ms,
            }

        # ============================================================
        # ★ حداکثر تکرار رد شد
        # ============================================================
        return {
            "success": False,
            "answer": None,
            "error": "تعداد درخواست‌های متوالی به LLM از حد گذشت",
            "tools_used": tools_used,
        }

    # ============================================================
    # ★ تست سلامت سرویس
    # ============================================================
    @classmethod
    def health_check(cls):
        """
        بررسی سلامت اتصال به LLM
        Returns: dict {ok: bool, message: str, model: str}
        """
        client = cls._get_client()
        if not client:
            return {
                "ok": False,
                "message": "کلاینت LLM ساخته نشد (کلید یا base_url مشکل داره)",
                "model": None,
            }

        try:
            response = client.chat.completions.create(
                model=cls._model,
                messages=[
                    {"role": "user", "content": "فقط کلمه «سالم» رو بنویس."}
                ],
                max_tokens=10,
                temperature=0,
            )
            answer = response.choices[0].message.content or ""
            return {
                "ok": True,
                "message": f"اتصال موفق. پاسخ تست: {answer.strip()[:50]}",
                "model": cls._model,
            }
        except Exception as e:
            return {
                "ok": False,
                "message": f"خطا: {str(e)[:150]}",
                "model": cls._model,
            }