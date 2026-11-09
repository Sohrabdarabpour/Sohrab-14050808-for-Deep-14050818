"""Handler جستجوی پیشرفته با فیلترهای طبیعی + خروجی اکسل.

مثال‌ها:
    «اسناد پیمانکار آبسان در ناحیه شمال با وضعیت تکمیل»
    «اسناد پروژه خط ۲ از فروردین تا خرداد»
    «خروجی اکسل اسناد پیمانکار MMTE»
"""

from services.ai.formatters import Formatters
from services.ai.handlers.base import BaseHandler
from services.ai.registry import IntentRegistry

# کلمات فیلتر (موجودیت‌ها و بازه)
FILTER_WORDS = (
    r"پیمانکار|پروژه|ناحیه|منطقه|گروه|زیرگروه|کارشناس|"
    r"از تاریخ|تا تاریخ|بازه|ماه گذشته|این ماه|امسال|سال گذشته|"
    r"فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند"
)

DOC_WORDS = r"اسناد|سند|مدارک|مدرک|پرونده"

EXPORT_WORDS = r"اکسل|excel|خروجی|دانلود"

MAX_PREVIEW = 8


def _export_url(filters):
    from services.search.search_filters import filters_to_query

    return filters_to_query(filters)


def _filter_summary(labels):
    if not labels:
        return ""
    return (
        '<span class="text-muted">فیلترها: </span>'
        + Formatters._safe(" · ".join(labels))
        + "\n\n"
    )


class FilterHandlers(BaseHandler):
    """جستجوی پیشرفته و خروجی اکسل"""

    # ============================================================
    # ★ ۱. جستجو با فیلتر
    # ============================================================
    @IntentRegistry.register(
        name="filtered_search",
        patterns=[
            rf"(?:{DOC_WORDS}).{{0,60}}(?:{FILTER_WORDS})",
            rf"(?:{FILTER_WORDS}).{{0,40}}(?:{DOC_WORDS})",
        ],
        priority=91,
        confidence=0.9,
        description="جستجوی اسناد با فیلتر پیمانکار/پروژه/ناحیه/تاریخ",
    )
    @staticmethod
    def handle_filtered_search(question, entities, user_id, is_admin):
        from services.ai.search_filter_builder import SearchFilterBuilder
        from services.search.search_service import search_documents

        filters, labels = SearchFilterBuilder(question).build()

        if not filters:
            return Formatters.response(
                '<i class="fa-solid fa-filter" style="color:#f59e0b"></i> '
                "<strong>فیلتر مشخصی پیدا نکردم.</strong>\n\n"
                '<span class="text-muted">مثلاً: «اسناد پیمانکار آبسان در ناحیه شمال '
                'با وضعیت تکمیل از فروردین تا خرداد»</span>',
                "text",
                suggestions=["راهنما", "آمار کلی"],
            )

        result = search_documents(**filters, page=1, per_page=MAX_PREVIEW)
        total = result.get("total", 0)
        records = result.get("records", [])

        answer = (
            f'<i class="fa-solid fa-filter" style="color:#3D8499"></i> '
            f"<strong>نتیجه جستجوی پیشرفته</strong>\n\n"
            f"{_filter_summary(labels)}"
        )

        if not total:
            answer += '<span class="text-muted">هیچ سندی با این فیلترها پیدا نشد.</span>'
            return Formatters.response(answer, "empty", suggestions=["راهنما", "کارهای من"])

        answer += (
            f'<strong class="num-highlight">{total}</strong> سند پیدا شد'
            + (f" — {MAX_PREVIEW} مورد اول:\n\n" if records else ".\n\n")
        )

        for index, record in enumerate(records, 1):
            subject = Formatters._safe(record.get("subject") or "بدون موضوع")
            doc_id = record.get("id")
            status = Formatters._safe(record.get("status_title") or "-")
            contractor = Formatters._safe(record.get("contractor_name") or "")

            answer += (
                f'<span class="doc-num">{index}.</span> '
                f'<a href="#" class="doc-link" data-doc-id="{doc_id}">{subject}</a>\n'
                f'&nbsp;&nbsp;<span class="text-muted">{status}'
                + (f" · {contractor}" if contractor else "")
                + "</span>\n"
            )

        answer += (
            f'\n<a href="{_export_url(filters)}" class="doc-link">'
            f'<i class="fa-solid fa-file-excel" style="color:#10b981"></i> '
            f"دانلود اکسل ({total} رکورد)</a>"
        )

        return Formatters.response(
            answer,
            "list",
            data=records,
            suggestions=[
                "خروجی اکسل همین نتایج",
                "اسناد دیرکرد",
                "آمار کلی",
            ],
        )

    # ============================================================
    # ★ ۲. خروجی اکسل
    # ============================================================
    @IntentRegistry.register(
        name="filtered_export",
        patterns=[
            rf"(?:{EXPORT_WORDS}).{{0,40}}(?:{DOC_WORDS}|فیلتر|جستجو)",
            rf"(?:{DOC_WORDS}).{{0,50}}(?:{EXPORT_WORDS})",
        ],
        priority=97,
        confidence=0.95,
        description="خروجی اکسل از نتایج جستجو",
    )
    @staticmethod
    def handle_filtered_export(question, entities, user_id, is_admin):
        from services.ai.search_filter_builder import SearchFilterBuilder
        from services.search.search_service import search_documents

        filters, labels = SearchFilterBuilder(question).build()

        if not filters:
            return Formatters.response(
                '<i class="fa-solid fa-file-excel" style="color:#10b981"></i> '
                "<strong>چه فیلتری برای خروجی اکسل؟</strong>\n\n"
                '<span class="text-muted">مثلاً: «خروجی اکسل اسناد پیمانکار آبسان '
                'با وضعیت تکمیل» یا «اکسل اسناد ناحیه شمال در ماه گذشته»</span>',
                "text",
                suggestions=["راهنما", "اسناد دیرکرد"],
            )

        result = search_documents(**filters, page=1, per_page=1)
        total = result.get("total", 0)

        if not total:
            return Formatters.response(
                '<i class="fa-solid fa-file-excel" style="color:#94a3b8"></i> '
                "<strong>هیچ سندی با این فیلترها نیست.</strong>\n\n"
                f"{_filter_summary(labels)}",
                "empty",
                suggestions=["راهنما", "کارهای من"],
            )

        answer = (
            f'<i class="fa-solid fa-file-excel" style="color:#10b981"></i> '
            f"<strong>فایل اکسل آماده است.</strong>\n\n"
            f"{_filter_summary(labels)}"
            f'<span class="text-muted">تعداد رکورد: </span>'
            f'<strong class="num-highlight">{total}</strong>\n\n'
            f'<a href="{_export_url(filters)}" class="doc-link">'
            f'<i class="fa-solid fa-download"></i> دانلود فایل اکسل</a>'
        )

        return Formatters.response(
            answer,
            "text",
            data=[{"url": _export_url(filters), "count": total}],
            suggestions=["اسناد دیرکرد", "آمار کلی", "راهنما"],
        )
