"""خروجی اکسل از نتایج جستجوی پیشرفته‌ی دستیار.

مسیر: `/assistant/export/search?status=completed&contractor=2&...`

پارامترها دقیقاً همان پارامترهای صفحه‌ی جستجو هستند
(`q`, `status`, `contractor`, `project`, `area`, `group`, `subgroup`,
`user`, `date_from`, `date_to`, `date_column`) تا لینکی که دستیار
می‌سازد با همان اکسل صفحه‌ی جستجو یکی باشد.
"""

from flask import current_app, request, send_file

from .assistant import assistant_bp, json_error, login_required

EXCEL_MIMETYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

MAX_ROWS = 10000


@assistant_bp.route("/export/search", methods=["GET"])
@login_required
def export_search():
    """ساخت و دانلود فایل اکسل از نتایج جستجوی فیلترشده."""
    from services.search.search_excel_service import (
        build_filename,
        build_search_excel,
    )
    from services.search.search_filters import filters_from_mapping
    from services.search.search_service import search_documents

    try:
        filters = filters_from_mapping(request.args)
        result = search_documents(**filters, page=1, per_page=MAX_ROWS)
        records = result.get("records", [])

        if not records:
            return json_error(
                "هیچ سندی با این فیلترها پیدا نشد؛ فایل اکسل ساخته نشد.",
                404,
                "no_results",
            )

        output = build_search_excel(records, sheet_title="نتایج جستجوی دستیار")
        filename = build_filename("assistant_search")

        return send_file(
            output,
            mimetype=EXCEL_MIMETYPE,
            as_attachment=True,
            download_name=filename,
        )

    except Exception as exc:  # noqa: BLE001 - خطا نباید صفحه‌ی خام بدهد
        current_app.logger.exception("assistant search export failed")
        return json_error(
            f"خطا در ساخت فایل اکسل: {exc}",
            500,
            "excel_export_error",
        )
