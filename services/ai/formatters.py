"""
Formatters - فرمت‌دهی پاسخ‌ها با آیکون‌های Font Awesome
=========================================================
- escape امن متن‌ها (ضد XSS)
- تبدیل تاریخ میلادی به شمسی
- پشتیبانی از لینک کلیک‌پذیر برای اسناد
- فرمت‌های آماده برای آمار، لیست، تحلیل
"""
from datetime import datetime
from html import escape

from helpers.date_helper import DateHelper


class Formatters:
    """فرمت‌دهی پاسخ‌های دستیار"""

    # ============================================================
    # ★ Helper داخلی: escape + تبدیل تاریخ
    # ============================================================
    @staticmethod
    def _safe(value):
        """escape امن با چک None"""
        if value is None or value == "":
            return ""
        return escape(str(value))

    @staticmethod
    def _safe_date(value):
        """تبدیل امن تاریخ به شمسی"""
        if not value:
            return ""
        try:
            return DateHelper.format_jalali(value)
        except Exception:
            return str(value)

    # ============================================================
    # ★ ساختار پایه پاسخ
    # ============================================================
    @staticmethod
    def response(answer, rtype="text", data=None, suggestions=None, meta=None):
        """
        ساخت پاسخ استاندارد

        Args:
            answer: متن HTML پاسخ (می‌تونه Font Awesome داشته باشه)
            rtype: نوع پاسخ (text, list, count, stats, chart, help, error, unknown)
            data: داده ساختاریافته (اختیاری)
            suggestions: لیست پیشنهادات بعدی
            meta: اطلاعات metadata
        """
        return {
            "answer": answer or "",
            "type": rtype,
            "data": data or [],
            "suggestions": suggestions or [],
            "meta": meta or {},
            "at": datetime.now().isoformat(),
        }

    # ============================================================
    # ★ لیست اسناد (با لینک کلیک‌پذیر + تاریخ شمسی)
    # ============================================================
    @staticmethod
    def doc_list(docs, title, show_deadline=False, show_status=True):
        """
        فرمت لیست اسناد

        Args:
            docs: لیست دیکشنری اسناد
            title: عنوان لیست
            show_deadline: نمایش مهلت
            show_status: نمایش وضعیت
        """
        if not docs:
            return Formatters.response(
                f'<i class="fa-solid fa-inbox" style="color:#94a3b8"></i> '
                f'<strong>{Formatters._safe(title)}</strong>\n\n'
                f'<span class="text-muted">هیچ سندی یافت نشد.</span>',
                "list",
                [],
                suggestions=["اسناد در حال بررسی", "کارهای من", "راهنما"]
            )

        lines = [
            f'<i class="fa-solid fa-list-check" style="color:#3D8499"></i> '
            f'<strong>{Formatters._safe(title)}</strong> '
            f'<span class="text-muted">({len(docs)} مورد)</span>\n'
        ]

        for i, d in enumerate(docs, 1):
            # ---- آماده‌سازی فیلدها ----
            subj = Formatters._safe(d.get("subject") or "بدون موضوع")
            code = Formatters._safe(d.get("code_dfc") or "-")
            status = Formatters._safe(d.get("status_title") or "-")
            doc_id = d.get("id")

            # ---- خط اصلی با لینک ----
            lines.append(
                f'<span class="doc-num">{i}.</span> '
                f'<a href="#" class="doc-link" data-doc-id="{doc_id}">'
                f'<i class="fa-solid fa-file-lines"></i> {subj}'
                f'</a>'
            )

            # ---- خط متادیتا ----
            meta_parts = []

            # کد
            if code and code != "-":
                meta_parts.append(
                    f'<i class="fa-solid fa-bookmark"></i> {code}'
                )

            # وضعیت
            if show_status and status and status != "-":
                meta_parts.append(
                    f'<i class="fa-solid fa-circle-dot"></i> {status}'
                )

            # مهلت (شمسی)
            if show_deadline and d.get("deadline"):
                deadline_jalali = Formatters._safe_date(d["deadline"])
                if deadline_jalali:
                    meta_parts.append(
                        f'<i class="fa-solid fa-clock"></i> {deadline_jalali}'
                    )

            # پیمانکار
            if d.get("contractor"):
                contractor = Formatters._safe(d["contractor"])
                meta_parts.append(
                    f'<i class="fa-solid fa-user-tie"></i> {contractor}'
                )

            # پروژه
            if d.get("project_name"):
                project = Formatters._safe(d["project_name"])
                meta_parts.append(
                    f'<i class="fa-solid fa-building"></i> {project}'
                )

            if meta_parts:
                lines.append(
                    f'<span class="doc-meta">'
                    f'{" &nbsp;•&nbsp; ".join(meta_parts)}'
                    f'</span>'
                )

            lines.append("")  # خط خالی بین اسناد

        return Formatters.response(
            "\n".join(lines),
            "list",
            docs,
            suggestions=[
                "فیلتر بر اساس وضعیت",
                "اسناد دیرکرد",
                "آمار کلی"
            ]
        )

    # ============================================================
    # ★ پاسخ آماری
    # ============================================================
    @staticmethod
    def stat_response(title, items):
        """
        فرمت پاسخ آماری

        Args:
            title: عنوان
            items: لیست [{"label": str, "value": int}]
        """
        if not items:
            return Formatters.response(
                f'<i class="fa-solid fa-chart-pie" style="color:#94a3b8"></i> '
                f'<strong>{Formatters._safe(title)}</strong>\n\n'
                f'<span class="text-muted">داده‌ای موجود نیست.</span>',
                "stats",
                []
            )

        lines = [
            f'<i class="fa-solid fa-chart-pie" style="color:#667eea"></i> '
            f'<strong>{Formatters._safe(title)}</strong>\n'
        ]

        for it in items:
            label = Formatters._safe(it.get("label") or "-")
            value = it.get("value", 0)
            color = it.get("color") or "#3D8499"

            lines.append(
                f'<i class="fa-solid fa-circle" style="color:{color};font-size:8px"></i> '
                f'{label}: <strong class="num-highlight">{value}</strong>'
            )

        return Formatters.response(
            "\n".join(lines),
            "stats",
            items,
            suggestions=["نمودار", "مقایسه با دپارتمان‌ها", "گزارش کامل"]
        )

    # ============================================================
    # ★ پاسخ شمارش (تکی)
    # ============================================================
    @staticmethod
    def count_response(title, count, icon="fa-circle-dot",
                       color="#3D8499", scope="شما", extra=None):
        """
        فرمت پاسخ شمارش

        Args:
            title: عنوان (مثلاً «در حال بررسی»)
            count: تعداد
            icon: نام آیکون FA
            color: رنگ آیکون
            scope: «شما» یا «کل سیستم»
            extra: متن اضافی اختیاری
        """
        answer = (
            f'<i class="fa-solid {icon}" style="color:{color}"></i> '
            f'در حال حاضر <strong class="num-highlight">{count}</strong> '
            f'سند «<strong>{Formatters._safe(title)}</strong>» '
            f'در <strong>{Formatters._safe(scope)}</strong> وجود دارد.'
        )

        if extra:
            answer += f"\n\n{extra}"

        return Formatters.response(
            answer,
            "count",
            [{"title": title, "count": count}],
            suggestions=[
                f"لیست {title}",
                "آمار کلی",
                "اسناد دیرکرد",
            ] if count > 0 else [
                "اسناد در حال بررسی",
                "کارهای من",
                "راهنما",
            ]
        )

    # ============================================================
    # ★ پاسخ خطا
    # ============================================================
    @staticmethod
    def error_response(message, suggestions=None):
        """فرمت پاسخ خطا"""
        return Formatters.response(
            f'<i class="fa-solid fa-triangle-exclamation" style="color:#ef4444"></i> '
            f'{Formatters._safe(message)}',
            "error",
            suggestions=suggestions or ["راهنما", "کارهای من"]
        )

    # ============================================================
    # ★ پاسخ خالی
    # ============================================================
    @staticmethod
    def empty_response(message="هیچ داده‌ای یافت نشد", suggestions=None):
        """فرمت پاسخ خالی"""
        return Formatters.response(
            f'<i class="fa-solid fa-inbox" style="color:#94a3b8"></i> '
            f'<span class="text-muted">{Formatters._safe(message)}</span>',
            "empty",
            suggestions=suggestions or ["راهنما", "کارهای من", "آمار کلی"]
        )

    # ============================================================
    # ★ پاسخ نمودار (برای Chart.js)
    # ============================================================
    @staticmethod
    def chart_response(title, labels, datasets, summary=None):
        """
        فرمت پاسخ نمودار

        Args:
            title: عنوان
            labels: برچسب‌ها (مثلاً ماه‌ها)
            datasets: لیست [{label, data, color}]
            summary: خلاصه آماری (اختیاری)
        """
        data = {
            "chart_type": "bar",
            "labels": labels,
            "datasets": datasets,
        }

        if summary:
            data["summary"] = summary

        answer = (
            f'<i class="fa-solid fa-chart-column" style="color:#667eea"></i> '
            f'<strong>{Formatters._safe(title)}</strong>\n'
        )

        if summary:
            for key, value in summary.items():
                answer += (
                    f'\n<i class="fa-solid fa-circle-dot" '
                    f'style="color:#3D8499;font-size:8px"></i> '
                    f'{Formatters._safe(key)}: <strong>{value}</strong>'
                )

        return Formatters.response(
            answer,
            "chart",
            [data],
            suggestions=["گزارش کامل", "مقایسه با سال قبل"]
        )

    # ============================================================
    # ★ پاسخ راهنما
    # ============================================================
    @staticmethod
    def help_response():
        """راهنمای دستیار"""
        text = (
            '<i class="fa-solid fa-robot" style="color:#3D8499"></i> '
            '<strong>راهنمای دستیار هوشمند</strong>\n\n'

            '<i class="fa-solid fa-chart-pie" style="color:#667eea"></i> '
            '<strong>آمار و شمارش:</strong>\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> چند سند در حال بررسی دارم؟\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> چند سند تکمیل شده؟\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> آمار کلی اسناد\n\n'

            '<i class="fa-solid fa-list-check" style="color:#10b981"></i> '
            '<strong>لیست‌ها:</strong>\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> لیست اسناد در حال بررسی\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> کارهای من چیه؟\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> اسناد دیرکرد\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> اسناد امروز\n\n'

            '<i class="fa-solid fa-arrow-trend-up" style="color:#f59e0b"></i> '
            '<strong>تحلیل‌های پیشرفته:</strong>\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> بهترین دپارتمان کدومه؟\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> پرمشغله‌ترین کارشناس کیست؟\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> روند ماهانه چطوره؟\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> رتبه‌بندی دپارتمان‌ها\n\n'

            '<i class="fa-solid fa-layer-group" style="color:#764ba2"></i> '
            '<strong>فیلتر:</strong>\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> گروه مهندسی چند سند؟\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> دپارتمان کنترل کیفیت چند سند؟\n\n'

            '<i class="fa-solid fa-magnifying-glass" style="color:#3D8499"></i> '
            '<strong>جستجو:</strong>\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> جستجو قرارداد\n'
            '&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> پیدا کن پروژه X'
        )

        return Formatters.response(
            text,
            "help",
            suggestions=["کارهای من", "آمار کلی", "بهترین دپارتمان کدومه؟"]
        )

    # ============================================================
    # ★ پاسخ unknown (عدم تشخیص)
    # ============================================================
    @staticmethod
    def unknown_response(question="", llm_available=False):
        """پاسخ وقتی intent تشخیص داده نشد"""
        q = str(question).strip()

        if len(q) < 4:
            hint = "سوال شما خیلی کوتاه بود."
            suggestions = ["راهنما", "کارهای من", "آمار کلی"]
        elif llm_available:
            hint = "سرویس AI در دسترس نیست."
            suggestions = ["راهنما", "کارهای من", "چند سند در حال بررسی دارم؟"]
        else:
            hint = "منظور شما رو متوجه نشدم."
            suggestions = ["راهنما", "کارهای من", "آمار کلی"]

        return Formatters.response(
            f'<i class="fa-solid fa-circle-question" style="color:#f59e0b"></i> '
            f'<strong>{hint}</strong>\n\n'
            f'<i class="fa-solid fa-lightbulb" style="color:#f59e0b"></i> '
            f'می‌تونید از نمونه‌های زیر استفاده کنید یا '
            f'<strong>راهنما</strong> بنویسید.',
            "unknown",
            suggestions=suggestions
        )