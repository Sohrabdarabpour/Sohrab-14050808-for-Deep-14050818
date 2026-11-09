"""نگاشت پارامترهای فیلتر جستجو بین URL و تابع `search_documents`.

چرا لازم است: هم صفحه‌ی جستجو و هم دستیار هوشمند باید فیلترها را از یک
شکل واحد بخوانند و بتوانند به هم تبدیل کنند (برای ساخت لینک خروجی اکسل).
"""

# نام پارامتر در URL -> نام آرگومان در search_documents
PARAM_TO_ARG = {
    "q": "query",
    "subject_keywords": "subject_keywords",
    "keywords_mode": "keywords_mode",
    "status": "status_code",
    "department": "department_id",
    "area": "area_id",
    "group": "group_id",
    "subgroup": "subgroup_id",
    "contractor": "contractor_id",
    "project": "project_id",
    "user": "user_id",
    "date_from": "date_from",
    "date_to": "date_to",
    "date_column": "date_column",
    "sort_by": "sort_by",
    "sort_dir": "sort_dir",
}

ARG_TO_PARAM = {arg: param for param, arg in PARAM_TO_ARG.items()}

INT_ARGS = {
    "department_id",
    "area_id",
    "group_id",
    "subgroup_id",
    "contractor_id",
    "project_id",
    "user_id",
}


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def filters_from_mapping(mapping):
    """ساخت دیکشنری فیلتر از request.args یا هر mapping دیگر."""
    filters = {}
    for param, arg in PARAM_TO_ARG.items():
        raw = mapping.get(param)
        if raw is None:
            continue
        if isinstance(raw, str):
            raw = raw.strip()
        if raw in ("", None):
            continue
        if arg in INT_ARGS:
            parsed = _to_int(raw)
            if parsed is None:
                continue
            filters[arg] = parsed
        else:
            filters[arg] = raw
    return filters


def filters_to_query(filters, base="/assistant/export/search"):
    """ساخت URL با query string از دیکشنری فیلتر (برای لینک دانلود)."""
    from urllib.parse import urlencode

    params = {}
    for arg, value in filters.items():
        param = ARG_TO_PARAM.get(arg)
        if not param or value in (None, "", []):
            continue
        params[param] = value

    query_string = urlencode(params)
    return f"{base}?{query_string}" if query_string else base


def describe_filters(filters):
    """توضیح انسانی فیلترهای فعال (برای نمایش در پاسخ دستیار)."""
    from database.repositories.areas import get_all_areas
    from database.repositories.contractors import get_all_contractors
    from database.repositories.projects import get_all_projects

    labels = []

    if filters.get("query"):
        labels.append(f'متن: «{filters["query"]}»')

    if filters.get("status_code"):
        status_titles = {
            "completed": "تکمیل‌شده",
            "in_progress": "در حال بررسی",
            "stopped": "متوقف‌شده",
            "deleted": "ابطال‌شده",
            "informational": "جهت اطلاع",
        }
        labels.append(
            "وضعیت: " + status_titles.get(filters["status_code"], filters["status_code"])
        )

    if filters.get("contractor_id"):
        for contractor in get_all_contractors() or []:
            if contractor["id"] == filters["contractor_id"]:
                labels.append(f'پیمانکار: {contractor["name"]}')
                break

    if filters.get("project_id"):
        for project in get_all_projects() or []:
            if project["id"] == filters["project_id"]:
                labels.append(f'پروژه: {project["name"]}')
                break

    if filters.get("area_id"):
        for area in get_all_areas() or []:
            if area["id"] == filters["area_id"]:
                labels.append(f'ناحیه: {area["title"]}')
                break

    if filters.get("date_from") or filters.get("date_to"):
        labels.append(
            f'بازه: {filters.get("date_from") or "…"} تا {filters.get("date_to") or "…"}'
        )

    return labels


__all__ = [
    "PARAM_TO_ARG",
    "ARG_TO_PARAM",
    "filters_from_mapping",
    "filters_to_query",
    "describe_filters",
]
