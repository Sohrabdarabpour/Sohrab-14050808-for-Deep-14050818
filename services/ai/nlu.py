"""
NLU - Natural Language Understanding
=====================================
وظایف این ماژول (و فقط اینا):
  ۱. نرمال‌سازی متن فارسی
  ۲. حذف filler words
  ۳. تبدیل اعداد (فارسی/عربی/حرفی → انگلیسی)
  ۴. استخراج زمان، عدد، ابهام

★ تشخیص intent کار Registry هست، نه NLU.
★ مترادف‌ها توی NLU بمونن چون برای نمایش/فیلتر استفاده می‌شن.
"""
import re


class NLU:
    """پردازش زبان طبیعی فارسی"""

    # ============================================================
    # ★ مترادف‌ها (فقط برای نگاشت وضعیت‌ها)
    # ★ توجه: اینا دیگه برای تشخیص intent نیستن!
    # ============================================================
    STATUS_SYNONYMS = {
        "in_progress": [
            "در حال بررسی", "درحال بررسی", "جاری", "باز",
            "در جریان", "در دست اقدام", "در دست بررسی",
            "ناتمام", "در حال انجام", "در حال پیگیری",
        ],
        "completed": [
            "تکمیل", "تکمیل شده", "تمام", "تمام شده",
            "بسته", "بسته شده", "انجام شد", "انجام شده",
            "خاتمه", "خاتمه یافته", "پایان یافته",
        ],
        "stopped": [
            "متوقف", "متوقف شده", "توقف", "نگه داشته",
            "نگه داشته شده", "توقف موقت",
        ],
        "deleted": [
            "ابطال", "ابطال شده", "حذف", "حذف شده",
            "کنسل", "کنسل شده", "لغو", "لغو شده", "منتفی",
        ],
        "informational": [
            "جهت اطلاع", "جهت آگاهی", "اطلاع", "آگاهی",
            "اطلاعیه", "خبری",
        ],
    }

    # ============================================================
    # ★ Filler Words — به دو دسته تقسیم شدن
    # ============================================================
    # اینا **همیشه** حذف می‌شن (کاملاً بی‌معنی برای تشخیص)
    SAFE_FILLERS = [
        "لطفا", "لطفاً", "لطفأ",
        "میشه", "می‌شه", "می شود",
        "میتونی", "می‌تونی", "می توانید", "می‌توانی",
        "ممکنه", "امکان داره",
        "بهم", "به من", "برام", "برای من",
        "بهم بگو", "بهم بگو؟",
        "بذار", "بگذار",
        "الان", "حالا", "الآن",
        "خب", "خُب",
        "ببین", "ببینم",
    ]

    # اینا **فقط وقتی** که جمله کوتاهه حذف می‌شن (تا معنی خراب نشه)
    CONDITIONAL_FILLERS = [
        "یک", "یه", "یه‌کم", "کمی",
        "بگو", "بیار", "نشون", "نمایش بده",
        "نشونم بده", "نشان بده",
    ]

    # ============================================================
    # ★ اعداد
    # ============================================================
    PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
    ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
    ENGLISH_DIGITS = "0123456789"

    WORD_NUMBERS = {
        "صفر": "0",
        "یک": "1", "یه": "1",
        "دو": "2", "سه": "3", "چهار": "4",
        "پنج": "5", "شش": "6", "هفت": "7",
        "هشت": "8", "نه": "9", "ده": "10",
        "بیست": "20", "سی": "30", "چهل": "40",
        "پنجاه": "50", "صد": "100", "هزار": "1000",
    }

    # ============================================================
    # ★ نرمال‌سازی
    # ============================================================
    @classmethod
    def normalize(cls, text):
        """نرمال‌سازی کامل متن فارسی"""
        if not text:
            return ""

        text = str(text)

        # ۱. یکسان‌سازی حروف عربی/فارسی
        text = text.replace("ي", "ی").replace("ك", "ک")
        text = text.replace("ۀ", "ه").replace("ة", "ه")
        text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        text = text.replace("ؤ", "و").replace("ئ", "ی")

        # ۲. حذف اعراب
        text = re.sub(r"[ًٌٍَُِّْٰ]", "", text)

        # ۳. حذف کاراکترهای خاص
        text = re.sub(r"[،؛،\u060C\u061B]", " ", text)

        # ۴. یکسان‌سازی فاصله‌ها
        text = re.sub(r"\s+", " ", text)

        # ۵. حذف فاصله اضافی دور پرانتز
        text = re.sub(r"\s*\(\s*", " (", text)
        text = re.sub(r"\s*\)\s*", ") ", text)

        return text.strip()

    # ============================================================
    # ★ حذف Filler Words (هوشمند)
    # ============================================================
    @classmethod
    def _strip_words(cls, text, words):
        """حذف کلمه‌ها با رعایت مرز کلمه.

        نکته‌ی مهم: \b در پایتون برای حروف فارسی کار نمی‌کند (چون حروف
        فارسی در re به‌عنوان word character شناسایی نمی‌شوند). بنابراین
        مرز را با «فاصله یا ابتدا/انتهای رشته» تعریف می‌کنیم.

        بدون این محدودیت، replace ساده کلمه‌ی «کمی» را در «تکمیل» هم پیدا
        می‌کرد و «تکمیل» را به «ت ل» تبدیل می‌کرد.
        """
        for word in sorted(words, key=len, reverse=True):
            pattern = r"(?<!\S)" + re.escape(word) + r"(?=\s|$|[،؛.,؟?!:])"
            text = re.sub(pattern, " ", text)
        return text

    @classmethod
    def clean(cls, text):
        """
        نرمال‌سازی + حذف filler words
        ★ حذف conditional fillers فقط وقتی جمله کوتاهه
        """
        text = cls.normalize(text)

        # ۱. حذف safe fillers (همیشه) — با مرز کلمه
        text = cls._strip_words(text, cls.SAFE_FILLERS)

        # ۲. آیا جمله کوتاهه؟ (کمتر از ۵ کلمه)
        word_count = len(text.split())
        if word_count <= 5:
            # فقط در این حالت conditional fillers رو حذف کن
            text = cls._strip_words(text, cls.CONDITIONAL_FILLERS)

        # ۳. حذف علائم پرسشی از انتها
        text = re.sub(r"[؟?!]+$", "", text)

        # ۴. فاصله‌های اضافی
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # ============================================================
    # ★ نرمال‌سازی اعداد
    # ============================================================
    @classmethod
    def normalize_digits(cls, text):
        """تبدیل اعداد فارسی/عربی به انگلیسی"""
        if not text:
            return ""

        text = str(text)
        for i, d in enumerate(cls.PERSIAN_DIGITS):
            text = text.replace(d, cls.ENGLISH_DIGITS[i])
        for i, d in enumerate(cls.ARABIC_DIGITS):
            text = text.replace(d, cls.ENGLISH_DIGITS[i])
        return text

    # ============================================================
    # ★ تبدیل اعداد حرفی (اصلاح‌شده با Unicode)
    # ============================================================
    @classmethod
    def convert_word_numbers(cls, text):
        """
        تبدیل اعداد حرفی («پنج» → «5»)
        ★ از \b استفاده نمی‌کنیم چون برای فارسی کار نمی‌کنه
        """
        if not text:
            return ""

        for word, num in cls.WORD_NUMBERS.items():
            # ★ الگوی دستی: قبل و بعد کلمه یا فاصله یا شروع/پایان رشته
            pattern = rf"(?:^|\s){re.escape(word)}(?:\s|$)"
            replacement = f" {num} "
            text = re.sub(pattern, replacement, text)

        # پاک‌سازی فاصله‌های اضافی
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    # ============================================================
    # ★ استخراج عدد
    # ============================================================
    @classmethod
    def extract_number(cls, text):
        """اولین عدد در متن رو استخراج می‌کنه"""
        if not text:
            return None

        text = cls.normalize_digits(text)
        text = cls.convert_word_numbers(text)

        match = re.search(r"\d+", text)
        if match:
            try:
                return int(match.group())
            except ValueError:
                return None
        return None

    # ============================================================
    # ★ توکن‌سازی
    # ============================================================
    @classmethod
    def tokenize(cls, text):
        if not text:
            return []
        return [t for t in re.split(r"\s+", text) if t]

    # ============================================================
    # ★ تشخیص وضعیت از متن (بهبودیافته)
    # ============================================================
    @classmethod
    def detect_status_hint(cls, text):
        """
        تشخیص وضعیت از متن
        ★ longest first (تا "در حال بررسی" قبل از "بررسی" match کنه)
        """
        if not text:
            return None

        normalized = cls.normalize(text)

        # همه‌ی مترادف‌ها رو با طول جمع کن
        all_syns = []
        for status, syns in cls.STATUS_SYNONYMS.items():
            for syn in syns:
                all_syns.append((syn, status))

        # طولانی‌ترین رو اول چک کن
        for syn, status in sorted(all_syns, key=lambda x: -len(x[0])):
            if syn in normalized:
                return status

        return None

    # ============================================================
    # ★ تشخیص زمان
    # ============================================================
    @classmethod
    def detect_time_hint(cls, text):
        """تشخیص محدوده زمانی"""
        if not text:
            return None

        text = cls.normalize(text)

        time_map = [
            (["امروز", "امروزه", "این روز"], "today"),
            (["دیروز"], "yesterday"),
            (["این هفته", "هفته جاری", "هفتگی"], "this_week"),
            (["هفته قبل", "هفته گذشته", "هفته پیش"], "last_week"),
            (["این ماه", "ماه جاری", "ماهانه"], "this_month"),
            (["ماه قبل", "ماه گذشته", "ماه پیش"], "last_month"),
            (["امسال", "سال جاری"], "this_year"),
            (["سال قبل", "سال گذشته", "سال پیش", "پارسال"], "last_year"),
        ]

        for keywords, hint in time_map:
            if any(w in text for w in keywords):
                return hint

        return None

    # ============================================================
    # ★ تشخیص ابهام
    # ============================================================
    @classmethod
    def is_ambiguous(cls, text):
        """آیا سوال مبهمه؟"""
        if not text:
            return True

        cleaned = cls.clean(text)
        tokens = cls.tokenize(cleaned)

        if len(tokens) < 2:
            return True
        if len(cleaned) < 3:
            return True

        return False

    # ============================================================
    # ★ خلاصه NLU (debug)
    # ============================================================
    @classmethod
    def analyze(cls, text):
        """تحلیل کامل (debug)"""
        normalized = cls.normalize(text)
        cleaned = cls.clean(text)
        tokens = cls.tokenize(cleaned)

        return {
            "original": text,
            "normalized": normalized,
            "cleaned": cleaned,
            "tokens": tokens,
            "status_hint": cls.detect_status_hint(text),
            "time_hint": cls.detect_time_hint(text),
            "number": cls.extract_number(text),
            "is_ambiguous": cls.is_ambiguous(text),
            "word_count": len(tokens),
        }