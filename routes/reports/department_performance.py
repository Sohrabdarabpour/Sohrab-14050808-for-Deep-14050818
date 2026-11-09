from flask import render_template, request, jsonify
from . import reports_bp
from services.departments.department_performance_service import (
    DepartmentPerformanceService
)


# ============================================================
# HELPERS — نرمال‌سازی پارامترها
# ============================================================

def _normalize_int(value):
    """
    ورودی رو به int یا None تبدیل می‌کنه.
    مقادیر all/خالی/None → None
    """
    if value in (None, "", "all"):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _normalize_year(value):
    """
    سال رو نرمال می‌کنه.
    all/خالی → 'all'
    عدد → رشته عدد
    """
    if value in (None, "", "all"):
        return "all"
    return str(value)


# ============================================================
# ★ صفحه اصلی — تحلیل عملکرد دپارتمان‌ها
# ============================================================
@reports_bp.route(
    "/department-performance",
    methods=["GET"]
)
def department_performance():
    """
    صفحه تحلیل عملکرد دپارتمان‌ها.
    پارامترهای ورودی (اختیاری):
      - year         : سال شمسی یا all
      - department_id: شناسه دپارتمان یا all
      - area_id      : شناسه ناحیه یا all
    """
    year = _normalize_year(request.args.get("year"))
    department_id = _normalize_int(request.args.get("department_id"))
    area_id = _normalize_int(request.args.get("area_id"))

    data = DepartmentPerformanceService.get_dashboard_data(
        year=year,
        department_id=department_id,
        area_id=area_id
    )

    # ★★★ داده‌ی ماهانه per-department برای Brush ★★★
    monthly_per_department = (
        DepartmentPerformanceService.get_monthly_per_department(
            year=year,
            department_id=department_id,
            area_id=area_id
        )
    )

    return render_template(
        "reports/department_performance.html",
        **data,
        monthly_per_department=monthly_per_department
    )


# ============================================================
# ★ روت JSON — برای AJAX (تغییر فیلترها بدون رفرش)
# ============================================================
@reports_bp.route(
    "/department-performance/data.json",
    methods=["GET"]
)
def department_performance_data():
    """
    داده‌های صفحه به صورت JSON.
    برای تغییر فیلترها بدون رفرش صفحه.
    """
    year = _normalize_year(request.args.get("year"))
    department_id = _normalize_int(request.args.get("department_id"))
    area_id = _normalize_int(request.args.get("area_id"))

    data = DepartmentPerformanceService.get_dashboard_data(
        year=year,
        department_id=department_id,
        area_id=area_id
    )

    # ★★★ داده‌ی ماهانه per-department برای Brush ★★★
    data["monthly_per_department"] = (
        DepartmentPerformanceService.get_monthly_per_department(
            year=year,
            department_id=department_id,
            area_id=area_id
        )
    )

    return jsonify(data)