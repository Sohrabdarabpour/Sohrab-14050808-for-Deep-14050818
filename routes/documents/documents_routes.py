"""
Document Routes - مدیریت و مشاهده اسناد

★ اصلاحات:
   - ریدایرکت‌ها به search.index (نه نوتیفیکیشن‌ها)
   - چک دسترسی هوشمند:
       • admin/manager/supervisor/doc_controller → همه اسناد
       • expert → اسناد خودش + اسناد مرتبط با یادداشت
   - دیباگ در حالت debug برای عیب‌یابی
"""
from flask import (
    Blueprint, render_template, request,
    session, redirect, url_for, flash, abort,
    current_app,
)

from security.decorators import role_required
from services.documents.document_service import DocumentService
from database.connection import get_connection
from helpers.date_helper import DateHelper


documents_bp = Blueprint(
    "documents",
    __name__,
    url_prefix="/documents"
)


# ============================================================
# ★ نقش‌های مجاز به مشاهده همه اسناد
# ============================================================
PRIVILEGED_ROLES = ("admin", "manager", "supervisor", "doc_controller")


# ============================================================
# ★ لیست اسناد (فقط admin/manager)
# ============================================================
@documents_bp.route("/")
@role_required("admin", "manager")
def documents():
    """لیست اسناد با فیلتر سال و صفحه‌بندی (آمار در SQL محاسبه می‌شود)"""
    selected_year = request.args.get("year", "all")
    available_years = DocumentService.get_available_years()

    if selected_year != "all":
        try:
            selected_year = int(selected_year)
        except (ValueError, TypeError):
            selected_year = "all"

        if selected_year not in available_years:
            selected_year = "all"

    page = request.args.get("page", 1, type=int) or 1

    data = DocumentService.get_page(selected_year, page=page)
    statistics = DocumentService.get_statistics(selected_year)

    return render_template(
        "documents/index.html",
        records=data["records"],
        statistics=statistics,
        available_years=available_years,
        selected_year=selected_year,
        page=data["page"],
        pages=data["pages"],
        total=data["total"],
        per_page=data["per_page"],
    )


# ============================================================
# ★★★ مشاهده کامل سند — نسخه اصلاح‌شده نهایی ★★★
# ============================================================
@documents_bp.route("/view/<int:doc_id>", methods=["GET"])
def view_document(doc_id):
    """
    صفحه کامل مشاهده یک سند

    ★ دسترسی:
      ─────────────────────────────────────────────────
      admin / manager / supervisor / doc_controller → همه اسناد
      expert → فقط اسناد خودش + اسنادی که یادداشت دارد
      ─────────────────────────────────────────────────
    """
    # ─── چک احراز هویت ───
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    role = session.get("role", "expert")
    is_privileged = role in PRIVILEGED_ROLES

    # ─── دریافت سند از دیتابیس ───
    conn = get_connection()
    try:
        sql = """
            SELECT d.*,
                   s.title AS status_title, s.color AS status_color,
                   a.title AS area_title,
                   dep.title AS department_title,
                   g.title AS group_title,
                   sg.title AS subgroup_title,
                   u.full_name AS user_full_name,
                   u.username AS user_username,
                   u.avatar AS user_avatar
            FROM documents d
            LEFT JOIN document_statuses s ON s.id = d.status_id
            LEFT JOIN areas a ON a.id = d.area_id
            LEFT JOIN departments dep ON dep.id = d.department_id
            LEFT JOIN document_groups g ON g.id = d.group_id
            LEFT JOIN document_subgroups sg ON sg.id = d.subgroup_id
            LEFT JOIN users u ON u.id = d.user_id
            WHERE d.id = ?
        """
        row = conn.execute(sql, (doc_id,)).fetchone()

        # ─── دیباگ در حالت debug ───
        if current_app.debug:
            print(f"\n🔍 [view_document] doc_id={doc_id}")
            print(f"   user_id={user_id}, role={role}, is_privileged={is_privileged}")
            print(f"   row_found={bool(row)}")

        # ═══════════════════════════════════════════════════════════
        # ★★★ اگر سند پیدا نشد → به صفحه جستجو ★★★
        # ═══════════════════════════════════════════════════════════
        if not row:
            flash("سند مورد نظر پیدا نشد.", "danger")
            return redirect(url_for("search.index"))

        doc = dict(row)

        if current_app.debug:
            print(f"   doc.user_id={doc.get('user_id')}")
            print(f"   doc.subject={doc.get('subject')}")

        # ═══════════════════════════════════════════════════════════
        # ★★★ چک دسترسی هوشمند ★★★
        # ═══════════════════════════════════════════════════════════
        has_access = False

        # ─── ۱. نقش‌های privileged → دسترسی کامل ───
        if is_privileged:
            has_access = True

        # ─── ۲. صاحب سند → دسترسی ───
        elif doc.get("user_id") == user_id:
            has_access = True

        # ─── ۳. کارشناس/سایر → بررسی یادداشت‌های مرتبط ───
        else:
            note_row = conn.execute("""
                SELECT 1 FROM document_notes
                WHERE document_id = ?
                  AND (user_id = ? OR assigned_to = ?)
                LIMIT 1
            """, (doc_id, user_id, user_id)).fetchone()

            if note_row:
                has_access = True

            if current_app.debug:
                print(f"   note_found={bool(note_row)}")

        if not has_access:
            flash("دسترسی به این سند ندارید.", "danger")
            return redirect(url_for("search.index"))

    finally:
        conn.close()

    # ═══════════════════════════════════════════════════════════
    # ★ تبدیل تاریخ‌ها به شمسی
    # ═══════════════════════════════════════════════════════════
    date_fields = [
        "date_letter",
        "date_received",
        "date_referral",
        "deadline",
        "response_announce_date",
        "created_at",
        "updated_at",
    ]

    for field in date_fields:
        if doc.get(field):
            try:
                doc[field] = DateHelper.format_jalali(doc[field])
            except Exception:
                # در صورت خطا مقدار خام حفظ می‌شود
                pass

    # ─── رندر ───
    return render_template(
        "documents/view.html",
        doc=doc,
        is_admin=is_privileged,
    )