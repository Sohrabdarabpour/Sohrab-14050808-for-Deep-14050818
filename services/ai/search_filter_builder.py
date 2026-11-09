"""تبدیل سؤال فارسی کاربر به فیلترهای جستجوی پیشرفته.

مثال:
    «اسناد پیمانکار آبسان در ناحیه شمال با وضعیت تکمیل از فروردین تا خرداد»
        ↓
    {
        "contractor_id": 2,
        "area_id": 3,
        "status_code": "completed",
        "date_from": "2026/03/21",
        "date_to": "2026/06/21",
    }

این ماژول فقط تشخیص می‌دهد؛ اجرای جستجو با
`services/search/search_service.search_documents` است.
"""

import re
from datetime import date, timedelta

import jdatetime

from services.ai.nlu import NLU

# ---------------------------------------------------------------- وضعیت‌ها
STATUS_WORDS = {
    "completed": ["تکمیل", "تمام شد", "تمام شده", "بسته", "خاتمه", "انجام شد"],
    "in_progress": ["در حال بررسی", "در حال انجام", "جاری", "باز", "ناتمام", "در دست"],
    "stopped": ["متوقف", "توقف", "نگه داشته"],
    "deleted": ["ابطال", "حذف", "کنسل", "لغو"],
    "informational": ["جهت اطلاع", "اطلاعیه", "آگاهی", "خبری"],
}

# ---------------------------------------------------------------- تاریخ‌ها
DATE_COLUMN_HINTS = [
    ("تاریخ دریافت", "date_received"),
    ("مهلت", "deadline"),
    ("تاریخ ارسال", "final_send_date"),
    ("تاریخ ارجاع", "date_referral"),
    ("تاریخ نامه", "date_letter"),
]

# کلماتی که در عبارت جستجوی متنی نباید بمانند
STOPWORDS = {
    "اسناد", "سند", "مدارک", "مدرک", "پرونده", "کارها", "کار", "مورد",
    "لیست", "فهرست", "نشان", "نشون", "بده", "بدهید", "بیار", "بگو",
    "چند", "تا", "که", "را", "رو", "در", "با", "از", "و", "برای", "همه",
    "فیلتر", "جستجو", "جست‌وجو", "اکسل", "خروجی", "گزارش", "دانلود",
    "وضعیت", "داریم", "دارد", "هست", "است", "می‌خواهم", "میخوام",
    "پیمانکار", "پروژه", "ناحیه", "منطقه", "گروه", "زیرگروه", "کارشناس",
    "تاریخ", "بازه", "بین", "ماه", "سال", "هفته", "روز",
}

PERSIAN_MONTHS = {
    "فروردین": 1, "اردیبهشت": 2, "خرداد": 3, "تیر": 4,
    "مرداد": 5, "شهریور": 6, "مهر": 7, "آبان": 8,
    "آذر": 9, "دی": 10, "بهمن": 11, "اسفند": 12,
}

DATE_PATTERN = re.compile(r"(\d{4})\s*[/\-]\s*(\d{1,2})\s*[/\-]\s*(\d{1,2})")


def _gregorian_str(value):
    return value.strftime("%Y/%m/%d")


def _to_gregorian(year, month, day):
    """اگر سال کوچک باشد، جلالی فرض می‌شود."""
    if year >= 1500:
        try:
            return date(year, month, day)
        except ValueError:
            return None
    try:
        return jdatetime.date(year, month, day).togregorian()
    except ValueError:
        return None


class SearchFilterBuilder:
    """استخراج فیلترهای جستجو از متن فارسی."""

    def __init__(self, text):
        self.raw = text or ""
        self.text = NLU.normalize(self.raw)
        self.filters = {}
        self.labels = []
        self._consumed = []

    # ------------------------------------------------------------ عمومی
    def build(self):
        self._detect_status()
        self._detect_date_column()
        self._detect_dates()
        self._detect_entities()
        self._detect_free_text()
        return self.filters, self.labels

    def _consume(self, phrase):
        if phrase and phrase not in self._consumed:
            self._consumed.append(phrase)

    # ------------------------------------------------------------ وضعیت
    def _detect_status(self):
        for code, words in STATUS_WORDS.items():
            for word in words:
                if word in self.text:
                    self.filters["status_code"] = code
                    self.labels.append(f"وضعیت: {word}")
                    self._consume(word)
                    return

    # ------------------------------------------------------------ ستون تاریخ
    def _detect_date_column(self):
        for hint, column in DATE_COLUMN_HINTS:
            if hint in self.text:
                self.filters["date_column"] = column
                self._consume(hint)
                return

    # ------------------------------------------------------------ تاریخ‌ها
    def _detect_dates(self):
        explicit = DATE_PATTERN.findall(self.text)
        parsed = [_to_gregorian(int(y), int(m), int(d)) for y, m, d in explicit]
        parsed = [item for item in parsed if item]
        if parsed:
            parsed.sort()
            self.filters["date_from"] = _gregorian_str(parsed[0])
            self.filters["date_to"] = _gregorian_str(parsed[-1])
            self.labels.append(f"بازه: {self.filters['date_from']} تا {self.filters['date_to']}")
            for year, month, day in explicit:
                self._consume(f"{year}/{int(month):02d}/{int(day):02d}")
                self._consume(f"{year}/{month}/{day}")
            return

        start, end, phrase = self._relative_range()
        if start and end:
            self.filters["date_from"] = _gregorian_str(start)
            self.filters["date_to"] = _gregorian_str(end)
            self.labels.append(f"بازه: {phrase}")
            self._consume(phrase)

    def _relative_range(self):
        today = date.today()
        today_j = jdatetime.date.fromgregorian(date=today)

        if "امروز" in self.text:
            return today, today, "امروز"
        if "دیروز" in self.text:
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday, "دیروز"
        if "این هفته" in self.text or "هفته جاری" in self.text:
            return today - timedelta(days=6), today, "این هفته"
        if "هفته گذشته" in self.text or "هفته قبل" in self.text:
            return today - timedelta(days=13), today - timedelta(days=7), "هفته گذشته"
        if "ماه گذشته" in self.text or "ماه قبل" in self.text:
            first_of_this = jdatetime.date(today_j.year, today_j.month, 1)
            last_of_prev = first_of_this - timedelta(days=1)
            first_of_prev = jdatetime.date(last_of_prev.year, last_of_prev.month, 1)
            return (
                first_of_prev.togregorian(),
                last_of_prev.togregorian(),
                "ماه گذشته",
            )
        if "این ماه" in self.text or "ماه جاری" in self.text:
            first_of_this = jdatetime.date(today_j.year, today_j.month, 1)
            return first_of_this.togregorian(), today, "این ماه"
        if "سال گذشته" in self.text or "سال قبل" in self.text:
            start = jdatetime.date(today_j.year - 1, 1, 1)
            end = jdatetime.date(today_j.year - 1, 12, 29)
            return start.togregorian(), end.togregorian(), "سال گذشته"
        if "امسال" in self.text or "سال جاری" in self.text:
            start = jdatetime.date(today_j.year, 1, 1)
            return start.togregorian(), today, "امسال"

        # نام ماه شمسی: «خرداد» یا «از فروردین تا خرداد»
        months = [num for name, num in PERSIAN_MONTHS.items() if name in self.text]
        if months:
            start_month = min(months)
            end_month = max(months)
            start = jdatetime.date(today_j.year, start_month, 1)
            if end_month == 12:
                end = jdatetime.date(today_j.year, 12, 29)
            else:
                end = jdatetime.date(today_j.year, end_month + 1, 1) - timedelta(days=1)
            label = "ماه " + " تا ".join(
                name for name, num in PERSIAN_MONTHS.items() if num in months
            )
            return start.togregorian(), end.togregorian(), label

        return None, None, ""

    # ------------------------------------------------------------ موجودیت‌ها
    def _detect_entities(self):
        self._match_names("contractor_id", self._load_contractors(), "پیمانکار")
        self._match_names("area_id", self._load_areas(), "ناحیه")
        self._match_names("group_id", self._load_groups(), "گروه")
        self._match_names("subgroup_id", self._load_subgroups(), "زیرگروه")
        self._match_names("user_id", self._load_users(), "کارشناس")
        self._detect_project()

    @staticmethod
    def _load_contractors():
        from database.repositories.contractors import get_all_contractors

        return [(item["id"], item["name"]) for item in (get_all_contractors() or [])]

    @staticmethod
    def _load_areas():
        from database.repositories.areas import get_all_areas

        return [(item["id"], item["title"]) for item in (get_all_areas() or [])]

    @staticmethod
    def _load_groups():
        from database.connection import get_connection

        conn = get_connection()
        try:
            rows = conn.execute("SELECT id, title FROM document_groups").fetchall()
            return [(row["id"], row["title"]) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def _load_subgroups():
        from database.connection import get_connection

        conn = get_connection()
        try:
            rows = conn.execute("SELECT id, title FROM document_subgroups").fetchall()
            return [(row["id"], row["title"]) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def _load_users():
        from database.repositories.users import get_all_users_for_select

        return [
            (item["id"], item.get("full_name") or "")
            for item in (get_all_users_for_select() or [])
        ]

    def _match_names(self, key, candidates, label):
        """طولانی‌ترین نامی که در متن آمده را انتخاب می‌کند."""
        if key in self.filters:
            return

        best = None
        for item_id, name in candidates:
            if not name or len(name) < 3:
                continue
            normalized = NLU.normalize(name)
            if normalized in self.text:
                if best is None or len(normalized) > len(best[1]):
                    best = (item_id, normalized, name)

        if best:
            self.filters[key] = best[0]
            self.labels.append(f"{label}: {best[2]}")
            self._consume(best[1])

    def _detect_project(self):
        from database.repositories.projects import search_projects

        match = re.search(
            r"پروژه\s+(?P<name>.{2,60}?)(?:\s+(?:در|با|از|تا|و|که)\s+|$)",
            self.text,
        )
        if not match:
            return

        name = match.group("name").strip(" ،؛.؟?")
        if len(name) < 2:
            return

        found = search_projects(name) or []
        if len(found) == 1:
            self.filters["project_id"] = found[0]["id"]
            self.labels.append(f"پروژه: {found[0]['name']}")
            self._consume(name)

    # ------------------------------------------------------------ متن آزاد
    def _detect_free_text(self):
        remaining = self.text
        for phrase in self._consumed:
            remaining = remaining.replace(phrase, " ")

        tokens = [
            token.strip("،؛.:!؟?")
            for token in re.split(r"\s+", remaining)
            if token.strip("،؛.:!؟?")
        ]
        meaningful = [token for token in tokens if token not in STOPWORDS and len(token) > 1]

        if meaningful:
            self.filters["query"] = " ".join(meaningful)
            self.labels.append(f'متن: «{self.filters["query"]}»')


__all__ = ["SearchFilterBuilder", "PERSIAN_MONTHS", "STATUS_WORDS"]
