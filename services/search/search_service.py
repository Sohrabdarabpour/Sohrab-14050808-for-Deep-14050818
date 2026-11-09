# Sohrab/services/search/search_service.py
"""
سرویس جستجوی پیشرفته در جدول اسناد
جستجو در تمام ستون‌های جدول documents + جداول مرتبط

★ نکته مهم:
    تاریخ‌ها در دیتابیس به صورت میلادی ذخیره می‌شوند (مثل "2024/08/15")
    ورودی کاربر از فرم به صورت جلالی می‌آید (مثل "1403/05/25")
    قبل از مقایسه در SQL، با DateHelper.convert_to_gregorian() تبدیل می‌شوند.

★ دو نوع جستجو:
    1) query            → جستجو در همه ۵۰+ ستون (OR بین ستون‌ها)
    2) subject_keywords → فقط ستون subject (AND بین کلیدواژه‌ها)
"""

from datetime import datetime
from database.connection import get_connection
from helpers.date_helper import DateHelper


# ================================================================
# ستون‌های قابل جستجو (تمام فیلدها + JOIN ها)
# ★ نکته: final_send_date اینجا نیست چون ممکنه توی دیتابیس قدیمی نباشه
# ================================================================
SEARCHABLE_COLUMNS = {
    # ---- فیلدهای مستقیم documents ----
    "d.code_dfc": "کد DFC",
    "d.date_letter": "تاریخ نامه",
    "d.automation_number": "شماره اتوماسیون",
    "d.contractor_letter_number": "شماره نامه پیمانکار",
    "d.subject": "موضوع",
    "d.contract_number": "شماره قرارداد",
    "d.project_name": "نام پروژه",
    "d.contractor": "پیمانکار",
    "d.area": "ناحیه",
    "d.date_received": "تاریخ دریافت",
    "d.date_referral": "تاریخ ارجاع",
    "d.expert_name": "نام کارشناس",
    "d.unit": "واحد",
    "d.document_group": "گروه مدرک",
    "d.sub_group": "زیرگروه",
    "d.deadline": "مهلت پاسخ",
    "d.request_complete_docs": "درخواست تکمیل مدارک",
    "d.complete_docs_by_contractor": "تکمیل مدارک توسط پیمانکار",
    "d.doc_response_status": "وضعیت پاسخ مدرک",
    "d.response_announce_date": "تاریخ اعلام پاسخ",
    "d.final_letter_number": "شماره نامه نهایی",
    "d.final_delay": "تاخیر نهایی",
    "d.colleague": "همکار",
    "d.Responsible_Party": "مسئول پاسخ",

    # ---- JOIN: users ----
    "u.full_name": "نام کاربر",
    "u.username": "نام کاربری",
    "u.position": "سمت کاربر",
    "u.email": "ایمیل کاربر",
    "u.phone": "تلفن کاربر",

    # ---- JOIN: document_statuses ----
    "s.title": "وضعیت سند",
    "s.code": "کد وضعیت",

    # ---- JOIN: areas ----
    "a.title": "ناحیه",

    # ---- JOIN: departments ----
    "dep.title": "دپارتمان",

    # ---- JOIN: document_groups ----
    "g.title": "گروه مدرک",
    "g.code": "کد گروه",

    # ---- JOIN: document_subgroups ----
    "sg.title": "زیرگروه مدرک",
    "sg.code": "کد زیرگروه",

    # ---- JOIN: contractors ----
    "c.name": "نام پیمانکار",
    "c.code": "کد پیمانکار",
    "c.manager_name": "مدیر پیمانکار",
    "c.phone": "تلفن پیمانکار",
    "c.mobile": "موبایل پیمانکار",
    "c.national_id": "شناسه ملی پیمانکار",

    # ---- JOIN: projects ----
    "p.name": "نام پروژه",
    "p.code": "کد پروژه",
    "p.project_number": "شماره پروژه",
    "p.contract_number": "شماره قرارداد پروژه",
    "p.location": "موقعیت پروژه",
}


# ستون‌های مجاز برای مرتب‌سازی
SORTABLE_COLUMNS = {
    "id": "d.id",
    "code_dfc": "d.code_dfc",
    "subject": "d.subject",
    "date_letter": "d.date_letter",
    "date_received": "d.date_received",
    "deadline": "d.deadline",
    "status": "s.title",
    "contractor": "c.name",
    "project": "p.name",
    "department": "dep.title",
    "created_at": "d.id",
}


# ================================================================
# ستون‌های مجاز تاریخ
# ★ اینجا final_send_date هست چون فقط وقتی کاربر انتخابش کنه استفاده می‌شه
# ★ اگه ستون دیتابیس نباشه، فقط موقع انتخاب کاربر خطا می‌ده (نه همیشه)
# ================================================================
ALLOWED_DATE_COLUMNS = {
    "date_letter",
    "date_received",
    "date_referral",
    "deadline",
    "response_announce_date",
    "final_send_date",          # ★ برای فیلتر تاریخ
}


# ================================================================
# JOIN مشترک
# ================================================================
def _build_joins():
    """JOIN مشترک برای همه کوئری‌ها"""
    return """
        FROM documents d
        LEFT JOIN users u               ON u.id = d.user_id
        LEFT JOIN document_statuses s   ON s.id = d.status_id
        LEFT JOIN areas a               ON a.id = d.area_id
        LEFT JOIN departments dep       ON dep.id = d.department_id
        LEFT JOIN document_groups g     ON g.id = d.group_id
        LEFT JOIN document_subgroups sg ON sg.id = d.subgroup_id
        LEFT JOIN contractors c         ON c.id = d.contractor_id
        LEFT JOIN projects p            ON p.id = d.project_id
    """


# ================================================================
# ★ Helper — تبدیل امن sqlite3.Row به dict
# ================================================================
def _row_to_dict(row):
    """
    تبدیل sqlite3.Row به dict به صورت امن.
    ★ این تابع مشکل 'sqlite3.Row' object has no attribute 'get' را حل می‌کند.
    """
    if row is None:
        return None
    try:
        return dict(row)
    except (TypeError, ValueError):
        return None


def _rows_to_dicts(rows):
    """تبدیل لیست sqlite3.Row به لیست dict"""
    if not rows:
        return []
    result = []
    for r in rows:
        d = _row_to_dict(r)
        if d:
            result.append(d)
    return result


# ================================================================
# ★ Helper — نرمال‌سازی کلیدواژه‌های موضوع
# ================================================================
# def _normalize_subject_keywords(subject_keywords):
#     """
#     ورودی می‌تواند:
#         - None
#         - رشته با کاما: "قرارداد, تمدید, مهلت"
#         - لیست: ["قرارداد", "تمدید", "مهلت"]
#     خروجی: لیست تمیز شده کلیدواژه‌ها
#     """
#     if not subject_keywords:
#         return []

#     if isinstance(subject_keywords, str):
#         raw = subject_keywords.split(",")
#     elif isinstance(subject_keywords, (list, tuple, set)):
#         raw = subject_keywords
#     else:
#         raw = [str(subject_keywords)]

#     return [str(k).strip() for k in raw if str(k).strip()]


# ================================================================
# ★ Helper — نرمال‌سازی کلیدواژه‌های موضوع
# ★ جداکننده: + (به جای کاما)
# ================================================================
def _normalize_subject_keywords(subject_keywords):
    """
    ورودی می‌تواند:
        - None
        - رشته با + : "قرارداد + تمدید + مهلت"
        - لیست: ["قرارداد", "تمدید", "مهلت"]
    خروجی: لیست تمیز شده کلیدواژه‌ها

    ★ جداکننده: علامت + (به جای کاما)
    """
    if not subject_keywords:
        return []

    if isinstance(subject_keywords, str):
        raw = subject_keywords.split("+")           # ★ تغییر از "," به "+"
    elif isinstance(subject_keywords, (list, tuple, set)):
        raw = subject_keywords
    else:
        raw = [str(subject_keywords)]

    return [str(k).strip() for k in raw if str(k).strip()]


# ================================================================
# جستجوی پیشرفته
# ================================================================
def search_documents(
    query=None,
    subject_keywords=None,          # ★ جدید: کلیدواژه‌های موضوع (AND)
    keywords_mode="OR",
    status_code=None,
    department_id=None,
    area_id=None,
    group_id=None,
    subgroup_id=None,
    contractor_id=None,
    project_id=None,
    user_id=None,
    date_from=None,
    date_to=None,
    date_column="date_letter",
    page=1,
    per_page=20,
    sort_by="id",
    sort_dir="DESC",
):
    """
    جستجوی پیشرفته در اسناد با فیلترهای چندگانه.

    Args:
        query: عبارت جستجو (در همه ستون‌ها — OR بین ستون‌ها)
        subject_keywords: کلیدواژه‌های موضوع (رشته با کاما یا لیست — AND بین‌شون)
        status_code: کد وضعیت
        department_id: شناسه دپارتمان
        area_id: شناسه ناحیه
        group_id: شناسه گروه
        subgroup_id: شناسه زیرگروه
        contractor_id: شناسه پیمانکار
        project_id: شناسه پروژه
        user_id: شناسه کاربر
        date_from: از تاریخ
        date_to: تا تاریخ
        date_column: ستون تاریخ برای مقایسه
        page: شماره صفحه
        per_page: تعداد در صفحه
        sort_by: ستون مرتب‌سازی
        sort_dir: جهت مرتب‌سازی

    Returns:
        dict با کلیدهای: records, total, page, per_page, pages, has_more, query
    """
    connection = get_connection()
    try:
        where_clauses = ["1=1"]
        params = []

        # ============================================================
        # ★★★ جستجوی متنی در همه ستون‌ها (منطق قبلی — دست‌نخورده) ★★★
        # ============================================================
        if query and str(query).strip():
            search_term = f"%{str(query).strip()}%"
            search_parts = []
            for col in SEARCHABLE_COLUMNS.keys():
                search_parts.append(f"IFNULL({col}, '') LIKE ?")
                params.append(search_term)
            where_clauses.append("(" + " OR ".join(search_parts) + ")")

        # ============================================================
        # ★★★ فیلتر کلیدواژه‌های موضوع (AND یا OR بر اساس keywords_mode) ★★★
        # ============================================================
        keywords = _normalize_subject_keywords(subject_keywords)

        if keywords:
            # امنیت: فقط OR یا AND مجاز
            mode = "AND" if str(keywords_mode).upper() == "AND" else "OR"

            if mode == "AND":
                # همه کلیدواژه‌ها باید موجود باشند
                for kw in keywords:
                    where_clauses.append("IFNULL(d.subject, '') LIKE ?")
                    params.append(f"%{kw}%")
            else:
                # هر کلیدواژه‌ای موجود باشد کافی است
                keyword_parts = []
                for kw in keywords:
                    keyword_parts.append("IFNULL(d.subject, '') LIKE ?")
                    params.append(f"%{kw}%")
                where_clauses.append("(" + " OR ".join(keyword_parts) + ")")
                
        # ============================================================
        # ★ فیلترهای دقیق
        # ============================================================
        if status_code:
            where_clauses.append("s.code = ?")
            params.append(status_code)
        if department_id:
            where_clauses.append("d.department_id = ?")
            params.append(department_id)
        if area_id:
            where_clauses.append("d.area_id = ?")
            params.append(area_id)
        if group_id:
            where_clauses.append("d.group_id = ?")
            params.append(group_id)
        if subgroup_id:
            where_clauses.append("d.subgroup_id = ?")
            params.append(subgroup_id)
        if contractor_id:
            where_clauses.append("d.contractor_id = ?")
            params.append(contractor_id)
        if project_id:
            where_clauses.append("d.project_id = ?")
            params.append(project_id)
        if user_id:
            where_clauses.append("d.user_id = ?")
            params.append(user_id)

        # ============================================================
        # ★★★ فیلتر تاریخ — تبدیل جلالی → میلادی ★★★
        # ★ final_send_date فقط وقتی استفاده می‌شه که کاربر انتخابش کنه
        # ============================================================
        if date_column not in ALLOWED_DATE_COLUMNS:
            date_column = "date_letter"

        if date_from and str(date_from).strip():
            greg_from = DateHelper.convert_to_gregorian(date_from)
            if greg_from:
                where_clauses.append(f"d.{date_column} >= ?")
                params.append(greg_from)

        if date_to and str(date_to).strip():
            greg_to = DateHelper.convert_to_gregorian(date_to)
            if greg_to:
                where_clauses.append(f"d.{date_column} <= ?")
                params.append(greg_to)

        # ============================================================
        # ★ ساخت WHERE و JOIN
        # ============================================================
        where_sql = " AND ".join(where_clauses)
        joins_sql = _build_joins()

        # ============================================================
        # ★ شمارش کل
        # ============================================================
        count_sql = f"""
            SELECT COUNT(DISTINCT d.id) AS total
            {joins_sql}
            WHERE {where_sql}
        """
        total_row = connection.execute(count_sql, params).fetchone()
        total = 0
        if total_row:
            total_dict = _row_to_dict(total_row) or {}
            total = int(total_dict.get("total") or 0)

        # ============================================================
        # ★ مرتب‌سازی
        # ============================================================
        sort_column = SORTABLE_COLUMNS.get(sort_by, "d.id")
        sort_direction = "DESC" if str(sort_dir).upper() == "DESC" else "ASC"

        # ============================================================
        # ★ صفحه‌بندی — حداکثر ۱۰۰۰۰ برای export
        # ============================================================
        page = max(1, int(page))
        per_page = max(1, min(int(per_page), 10000))
        offset = (page - 1) * per_page

        # ============================================================
        # ★ کوئری اصلی
        # ============================================================
        data_sql = f"""
            SELECT
                d.*,
                s.title     AS status_title,
                s.code      AS status_code,
                s.color     AS status_color,
                u.full_name AS user_full_name,
                u.username  AS user_username,
                a.title     AS area_title,
                dep.title   AS department_title,
                g.title     AS group_title,
                g.color     AS group_color,
                sg.title    AS subgroup_title,
                sg.color    AS subgroup_color,
                c.name      AS contractor_name,
                c.code      AS contractor_code,
                p.name      AS project_title,
                p.code      AS project_code
            {joins_sql}
            WHERE {where_sql}
            ORDER BY {sort_column} {sort_direction}
            LIMIT ? OFFSET ?
        """
        data_params = params + [per_page, offset]
        rows = connection.execute(data_sql, data_params).fetchall()

        # ★ تبدیل امن
        records = _rows_to_dicts(rows)

        # ============================================================
        # ★ تاریخ‌های جلالی + days_left برای هر رکورد
        # ============================================================
        for rec in records:
            rec["deadline_jalali"] = DateHelper.format_jalali(rec.get("deadline"))
            rec["date_letter_jalali"] = DateHelper.format_jalali(rec.get("date_letter"))
            rec["date_received_jalali"] = DateHelper.format_jalali(rec.get("date_received"))
            rec["date_referral_jalali"] = DateHelper.format_jalali(rec.get("date_referral"))
            rec["response_announce_date_jalali"] = DateHelper.format_jalali(
                rec.get("response_announce_date")
            )
            # ★ فقط اگه ستون توی رکورد باشه (برای دیتابیس‌های جدید)
            if "final_send_date" in rec:
                rec["final_send_date_jalali"] = DateHelper.format_jalali(
                    rec.get("final_send_date")
                )
            rec["days_left"] = _calc_days_left(rec.get("deadline"))

        # ============================================================
        # ★ تعداد صفحات
        # ============================================================
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0

        return {
            "records": records,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_more": (page * per_page) < total,
            "query": query or "",
        }

    finally:
        connection.close()


# ================================================================
# محاسبه روزهای باقی‌مانده تا مهلت
# ================================================================
def _calc_days_left(deadline_str):
    """محاسبه روزهای باقی‌مانده تا مهلت (منفی = گذشته از مهلت)"""
    if not deadline_str or str(deadline_str).strip() == "":
        return None

    try:
        from datetime import date as date_type

        today = datetime.now().date()
        value = str(deadline_str).strip()
        value = DateHelper.normalize_digits(value).replace("-", "/")

        parts = value.split("/")
        if len(parts) != 3:
            return None

        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2].split(" ")[0])
        except (ValueError, TypeError):
            return None

        if year >= 1700:
            deadline_date = date_type(year, month, day)
        else:
            import jdatetime
            gregorian = jdatetime.date(year, month, day).togregorian()
            deadline_date = gregorian

        return (deadline_date - today).days

    except Exception:
        return None


# ================================================================
# ★★★ پیشنهادات جستجو (Autocomplete) ★★★
# ================================================================
def get_search_suggestions(query, limit=10):
    """
    پیشنهادات جستجو بر اساس موضوع، کد DFC و نام پیمانکار.

    Args:
        query: عبارت جستجو (حداقل ۲ کاراکتر)
        limit: حداکثر تعداد پیشنهاد در هر دسته

    Returns:
        dict:
            - subjects: لیست موضوعات مشابه
            - codes: لیست کدهای DFC مشابه
            - contractors: لیست نام پیمانکاران مشابه
    """
    if not query or len(str(query).strip()) < 2:
        return {"subjects": [], "codes": [], "contractors": []}

    connection = get_connection()
    try:
        term = f"%{str(query).strip()}%"

        # ═══════════════════════════════════════════════════════
        # ★ موضوعات اسناد
        # ═══════════════════════════════════════════════════════
        subject_rows = connection.execute("""
            SELECT DISTINCT subject AS value
            FROM documents
            WHERE subject IS NOT NULL
              AND TRIM(subject) != ''
              AND subject LIKE ?
            ORDER BY subject ASC
            LIMIT ?
        """, (term, limit)).fetchall()

        subjects = _rows_to_dicts(subject_rows)

        # ═══════════════════════════════════════════════════════
        # ★ کدهای DFC
        # ═══════════════════════════════════════════════════════
        code_rows = connection.execute("""
            SELECT DISTINCT code_dfc AS value
            FROM documents
            WHERE code_dfc IS NOT NULL
              AND TRIM(code_dfc) != ''
              AND code_dfc LIKE ?
            ORDER BY code_dfc ASC
            LIMIT ?
        """, (term, limit)).fetchall()

        codes = _rows_to_dicts(code_rows)

        # ═══════════════════════════════════════════════════════
        # ★ پیمانکاران
        # ═══════════════════════════════════════════════════════
        contractor_rows = connection.execute("""
            SELECT DISTINCT name AS value
            FROM contractors
            WHERE name IS NOT NULL
              AND TRIM(name) != ''
              AND is_active = 1
              AND name LIKE ?
            ORDER BY name ASC
            LIMIT ?
        """, (term, limit)).fetchall()

        contractors = _rows_to_dicts(contractor_rows)

        # ═══════════════════════════════════════════════════════
        # ★ بازگشت نتیجه
        # ═══════════════════════════════════════════════════════
        return {
            "subjects": subjects,
            "codes": codes,
            "contractors": contractors,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"subjects": [], "codes": [], "contractors": []}
    finally:
        connection.close()