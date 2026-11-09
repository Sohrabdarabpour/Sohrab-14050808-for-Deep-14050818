# Sohrab/routes/search/search_routes.py
"""
روت‌های جستجوی پیشرفته اسناد
شامل:
    - صفحه اصلی جستجو
    - API جستجو (JSON)
    - API پیشنهادات (Autocomplete)
    - API خروجی اکسل
    - API زیرگروه‌ها (فیلتر پویا)
    - API آمار کلی
"""

from flask import (
    Blueprint, render_template, request, session,
    jsonify, redirect, url_for, send_file
)

from services.search import search_documents, get_search_suggestions
from database.connection import get_connection


# ============================================================
# ★ Blueprint
# ============================================================
search_bp = Blueprint(
    "search",
    __name__,
    url_prefix="/search",
    template_folder="../../templates/search",
)


# ============================================================
# ★ توابع کمکی — گرفتن لیست‌ها از دیتابیس
# ============================================================
def _fetch_list(sql, params=()):
    """اجرای یک کوئری SELECT و برگرداندن لیست دیکشنری‌ها"""
    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _get_departments():
    return _fetch_list("""
        SELECT id, title FROM departments
        WHERE is_active = 1
        ORDER BY sort_order ASC, title ASC
    """)


def _get_areas():
    return _fetch_list("""
        SELECT id, title FROM areas
        WHERE is_active = 1
        ORDER BY sort_order ASC, title ASC
    """)


def _get_groups():
    return _fetch_list("""
        SELECT id, title FROM document_groups
        WHERE is_active = 1
        ORDER BY sort_order ASC, title ASC
    """)


def _get_subgroups():
    """★ جدید: زیرگروه‌های اسناد"""
    return _fetch_list("""
        SELECT id, title FROM document_subgroups
        WHERE is_active = 1
        ORDER BY sort_order ASC, title ASC
    """)


def _get_contractors():
    return _fetch_list("""
        SELECT id, name FROM contractors
        WHERE is_active = 1
        ORDER BY sort_order ASC, name ASC
    """)


def _get_projects():
    return _fetch_list("""
        SELECT id, name FROM projects
        WHERE is_active = 1
        ORDER BY sort_order ASC, name ASC
    """)


def _get_users():
    return _fetch_list("""
        SELECT id, full_name, username, role, avatar
        FROM users
        WHERE is_active = 1
        ORDER BY full_name ASC
    """)


def _get_statuses():
    return _fetch_list("""
        SELECT id, title, code, color
        FROM document_statuses
        WHERE is_active = 1
        ORDER BY sort_order ASC
    """)


# ============================================================
# ★ Helper — تبدیل به عدد صحیح (امن)
# ============================================================
def _to_int(value):
    """تبدیل امن مقدار به عدد صحیح — اگر نامعتبر بود None برمی‌گرداند"""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ============================================================
# ★ Helper — ساخت دیکشنری فیلترهای مشترک از request.args
# ============================================================
def _build_filters_from_request():
    """
    تمام فیلترهای جستجو را از request.args استخراج می‌کند.
    این تابع بین api_search و api_export مشترک است.

    ★ پارامترهای پشتیبانی‌شده:
        q                  → عبارت جستجو (همه ستون‌ها)
        subject_keywords   → کلیدواژه‌های موضوع (با +)
        status             → کد وضعیت
        department         → شناسه دپارتمان
        area               → شناسه ناحیه
        group              → شناسه گروه
        subgroup           → شناسه زیرگروه
        contractor         → شناسه پیمانکار
        project            → شناسه پروژه
        user               → شناسه کاربر
        date_from          → از تاریخ
        date_to            → تا تاریخ
        date_column        → ستون تاریخ (پیش‌فرض: date_letter)
        sort_by            → ستون مرتب‌سازی
        sort_dir           → جهت مرتب‌سازی
    """
    return {
        "query": request.args.get("q", "").strip() or None,
        "subject_keywords": request.args.get("subject_keywords") or None,
        "keywords_mode": request.args.get("keywords_mode", "OR"),   # ★ جدید
        "status_code": request.args.get("status") or None,
        "department_id": _to_int(request.args.get("department")),
        "area_id": _to_int(request.args.get("area")),
        "group_id": _to_int(request.args.get("group")),
        "subgroup_id": _to_int(request.args.get("subgroup")),
        "contractor_id": _to_int(request.args.get("contractor")),
        "project_id": _to_int(request.args.get("project")),
        "user_id": _to_int(request.args.get("user")),
        "date_from": request.args.get("date_from") or None,
        "date_to": request.args.get("date_to") or None,
        "date_column": request.args.get("date_column") or "date_letter",
        "sort_by": request.args.get("sort_by", "id"),
        "sort_dir": request.args.get("sort_dir", "DESC"),
    }


# ============================================================
# ★ صفحه اصلی جستجو
# ============================================================
@search_bp.route("/", methods=["GET"])
def index():
    """صفحه جستجوی پیشرفته"""
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    return render_template(
        "search.html",
        departments=_get_departments(),
        areas=_get_areas(),
        groups=_get_groups(),
        subgroups=_get_subgroups(),         # ★ جدید
        contractors=_get_contractors(),
        projects=_get_projects(),
        users=_get_users(),
        statuses=_get_statuses(),
    )


# ============================================================
# ★ API جستجو (AJAX)
# ============================================================
@search_bp.route("/api/search", methods=["GET"])
def api_search():
    """API جستجو — خروجی JSON"""
    if not session.get("user_id"):
        return jsonify({"success": False, "message": "unauthorized"}), 401

    try:
        filters = _build_filters_from_request()

        page = _to_int(request.args.get("page")) or 1
        per_page = _to_int(request.args.get("per_page")) or 20

        result = search_documents(
            **filters,
            page=page,
            per_page=per_page,
        )

        return jsonify({"success": True, **result})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"خطا در جستجو: {str(e)}"
        }), 500


# ============================================================
# ★ API پیشنهادات Autocomplete
# ============================================================
@search_bp.route("/api/suggestions", methods=["GET"])
def api_suggestions():
    """پیشنهادات جستجو (موضوع، کد DFC، پیمانکار)"""
    if not session.get("user_id"):
        return jsonify({"success": False, "message": "unauthorized"}), 401

    query = request.args.get("q", "").strip()

    try:
        suggestions = get_search_suggestions(query, limit=8)
        return jsonify({"success": True, **suggestions})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# ★ API زیرگروه‌ها — فقط زیرگروه‌های هر گروه
# ============================================================
@search_bp.route("/api/subgroups", methods=["GET"])
def api_subgroups():
    """
    زیرگروه‌های یک گروه خاص.
    - اگر group_id داده شود → فقط زیرگروه‌های متصل به آن گروه
    - اگر داده نشود → همه زیرگروه‌ها
    """
    if not session.get("user_id"):
        return jsonify({"success": False, "message": "unauthorized"}), 401

    group_id = _to_int(request.args.get("group_id"))

    try:
        if group_id:
            subgroups = _fetch_list("""
                SELECT sg.id, sg.title
                FROM document_subgroups sg
                INNER JOIN group_subgroups gs ON gs.subgroup_id = sg.id
                WHERE gs.group_id = ?
                  AND gs.is_active = 1
                  AND sg.is_active = 1
                ORDER BY sg.sort_order ASC, sg.title ASC
            """, (group_id,))
        else:
            subgroups = _get_subgroups()

        return jsonify({"success": True, "subgroups": subgroups})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

# ============================================================
# ★ API — پروژه‌های یک پیمانکار + پیمانکار یک پروژه
# ============================================================
@search_bp.route("/api/contractor-projects", methods=["GET"])
def api_contractor_projects():
    """
    مدیریت ارتباط دوطرفه بین پیمانکار و پروژه.

    - اگر contractor_id داده شود → لیست پروژه‌های آن پیمانکار
    - اگر project_id داده شود → شناسه پیمانکار آن پروژه

    Query params:
        contractor_id : شناسه پیمانکار (اختیاری)
        project_id    : شناسه پروژه (اختیاری)
    """
    if not session.get("user_id"):
        return jsonify({"success": False, "message": "unauthorized"}), 401

    contractor_id = _to_int(request.args.get("contractor_id"))
    project_id = _to_int(request.args.get("project_id"))

    try:
        # ---- حالت ۱: گرفتن پروژه‌های یک پیمانکار ----
        if contractor_id:
            projects = _fetch_list("""
                SELECT id, name, code
                FROM projects
                WHERE contractor_id = ?
                  AND is_active = 1
                ORDER BY sort_order ASC, name ASC
            """, (contractor_id,))

            return jsonify({
                "success": True,
                "projects": projects,
            })

        # ---- حالت ۲: گرفتن پیمانکار یک پروژه ----
        if project_id:
            row = _fetch_list("""
                SELECT contractor_id
                FROM projects
                WHERE id = ?
                LIMIT 1
            """, (project_id,))

            contractor_id_result = None
            if row and row[0].get("contractor_id"):
                contractor_id_result = row[0]["contractor_id"]

            return jsonify({
                "success": True,
                "contractor_id": contractor_id_result,
            })

        # ---- حالت ۳: هیچ‌کدام ----
        return jsonify({
            "success": True,
            "projects": [],
            "contractor_id": None,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

    
# ============================================================
# ★ API خروجی اکسل
# ============================================================
@search_bp.route("/api/export", methods=["GET"])
def api_export():
    """
    خروجی اکسل از نتایج جستجو.
    ★ همه رکوردهای منطبق (تا ۱۰٬۰۰۰) را در یک فایل .xlsx می‌ریزد.
    """
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    try:
        filters = _build_filters_from_request()
        result = search_documents(
            **filters,
            page=1,
            per_page=10000,
        )

        # ---- ساخت فایل اکسل ----
        import io
        from datetime import datetime
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = "نتایج جستجو"
        ws.sheet_view.rightToLeft = True

        # ---- هدر ستون‌ها ----
        headers = [
            "کد DFC",
            "موضوع",
            "وضعیت",
            "پیمانکار",
            "پروژه",
            "تاریخ نامه",
            "شماره اتوماسیون",
            "شماره نامه پیمانکار",
            "شماره قرارداد",
            "دپارتمان",
            "ناحیه",
            "گروه مدرک",
            "زیرگروه",
            "مهلت پاسخ",
            "وضعیت پاسخ",
            "تاریخ دریافت",
            "تاریخ ارسال نهایی",
        ]
        ws.append(headers)

        # ---- استایل هدر ----
        header_font = Font(bold=True, color="FFFFFF", size=11, name="Tahoma")
        header_fill = PatternFill("solid", fgColor="1B698B")
        header_align = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align

        ws.row_dimensions[1].height = 28

        # ---- درج داده‌ها ----
        body_font = Font(size=10, name="Tahoma")
        body_align = Alignment(
            horizontal="right",
            vertical="center",
            wrap_text=False,
        )

        for rec in result["records"]:
            ws.append([
                rec.get("code_dfc", "") or "",
                rec.get("subject", "") or "",
                rec.get("status_title", "") or "",
                rec.get("contractor_name", "") or rec.get("contractor", "") or "",
                rec.get("project_title", "") or rec.get("project_name", "") or "",
                rec.get("date_letter_jalali", "") or rec.get("date_letter", "") or "",
                rec.get("automation_number", "") or "",
                rec.get("contractor_letter_number", "") or "",
                rec.get("contract_number", "") or "",
                rec.get("department_title", "") or "",
                rec.get("area_title", "") or "",
                rec.get("group_title", "") or "",
                rec.get("subgroup_title", "") or "",
                rec.get("deadline_jalali", "") or rec.get("deadline", "") or "",
                rec.get("doc_response_status", "") or "",
                rec.get("date_received_jalali", "") or rec.get("date_received", "") or "",
                rec.get("final_send_date_jalali", "") or rec.get("final_send_date", "") or "",
            ])

        # ---- استایل بدنه ----
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
            for cell in row:
                cell.font = body_font
                cell.alignment = body_align

        # ---- تنظیم عرض خودکار ستون‌ها ----
        for col_idx, column_cells in enumerate(ws.columns, start=1):
            max_len = 10
            for cell in column_cells:
                if cell.value:
                    cell_len = len(str(cell.value))
                    if cell_len > max_len:
                        max_len = cell_len
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 45)

        # ---- ذخیره در حافظه ----
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        # ---- نام فایل ----
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_results_{timestamp}.xlsx"

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except ImportError:
        return jsonify({
            "success": False,
            "message": "کتابخانه openpyxl نصب نیست. با دستور pip install openpyxl نصب کنید."
        }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"خطا در ساخت فایل اکسل: {str(e)}"
        }), 500


# ============================================================
# ★ API — آمار کلی نتایج
# ============================================================
@search_bp.route("/api/stats", methods=["GET"])
def api_stats():
    """
    آمار سریع از نتایج جستجو (برای نمایش خلاصه در بالای صفحه).
    """
    if not session.get("user_id"):
        return jsonify({"success": False, "message": "unauthorized"}), 401

    try:
        filters = _build_filters_from_request()
        result = search_documents(
            **filters,
            page=1,
            per_page=1,
        )

        return jsonify({
            "success": True,
            "total": result["total"],
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500