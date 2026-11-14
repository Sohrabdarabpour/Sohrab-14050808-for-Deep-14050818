"""فرم ثبت سریع پکیج سند.

کاربر فقط اطلاعات اولیه را وارد می‌کند و همان لحظه کد DFC می‌گیرد.
ادامه‌ی فرایند (آپلود، ارسال به مدیریت، بازگشت، ارجاع) از صفحه‌ی پکیج انجام می‌شود.
"""

from flask import (
    flash, redirect, render_template, request, session, url_for,
)

from database.connection import get_connection
from helpers.date_helper import DateHelper
from services.work_package import wp_service, wp_sla_service

from . import work_package_bp


def _uid():
    return session.get("user_id")


def _require_login():
    if not _uid():
        return redirect(url_for("auth.login"))
    return None


def _choices():
    """لیست‌های کشویی."""
    connection = get_connection()
    try:
        contractors = [dict(r) for r in connection.execute(
            "SELECT id, name FROM contractors WHERE is_active=1 ORDER BY name"
        ).fetchall()]
        projects = [dict(r) for r in connection.execute(
            "SELECT id, name FROM projects WHERE is_active=1 ORDER BY name"
        ).fetchall()]
    finally:
        connection.close()
    return {"contractors": contractors, "projects": projects}


# ============================================================
# ★ ثبت سریع (تنها مرحله)
# ============================================================
@work_package_bp.route("/new", methods=["GET", "POST"])
def new_package():
    """فرم ثبت سریع سند — همان لحظه کد DFC می‌گیرد."""
    guard = _require_login()
    if guard:
        return guard

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()

        if not subject:
            flash("موضوع سند الزامی است", "danger")
            return render_template(
                "work_package/new.html",
                draft=request.form,
                **_choices(),
            )

        result = wp_service.register_package(
            subject=subject,
            registered_by=_uid(),
            date_letter=DateHelper.convert_to_gregorian(
                request.form.get("date_letter", "").strip()
            ),
            date_received=DateHelper.convert_to_gregorian(
                request.form.get("date_received", "").strip()
            ),
            sender_ref_no=request.form.get("sender_ref_no", "").strip() or None,
            sender_ref_date=DateHelper.convert_to_gregorian(
                request.form.get("sender_ref_date", "").strip()
            ),
            contract_number=request.form.get("contract_number", "").strip() or None,
            automation_number=request.form.get("automation_number", "").strip() or None,
            sender_name=request.form.get("sender_name", "").strip() or None,
            sender_type=request.form.get("sender_type", "other"),
            source_type=request.form.get("sender_type", "other"),
            description=request.form.get("description", "").strip() or None,
            contractor_id=int(request.form.get("contractor_id", 0)) or None,
            project_id=int(request.form.get("project_id", 0)) or None,
            force_new_wp=request.form.get("force_new_wp") == "1",
        )

        if not result["ok"]:
            flash(result.get("error", "خطا در ثبت"), "danger")
            return render_template(
                "work_package/new.html",
                draft=request.form,
                **_choices(),
            )

        # محاسبه SLA
        try:
            wp_sla_service.recalculate_sla(
                result["package_id"], actor_id=_uid(),
            )
        except Exception:
            pass

        flash(
            f"سند با کد {result['dfc_code']} در پکیج "
            f"{result['work_package_code']} ثبت شد. "
            f"حالا می‌توانید کد DFC را چاپ کرده و روی فیزیکی بچسبانید.",
            "success",
        )
        return redirect(url_for(
            "work_package.view",
            package_id=result["package_id"],
        ))

    # GET
    return render_template(
        "work_package/new.html",
        draft={},
        **_choices(),
    )