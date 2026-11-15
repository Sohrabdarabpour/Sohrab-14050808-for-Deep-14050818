"""فرم ثبت سریع پکیج سند."""

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


def _to_int(val):
    if val is None or val == "" or val == 0 or val == "0":
        return None
    try:
        v = int(val)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


# ============================================================
# ★ ثبت سریع
# ============================================================
@work_package_bp.route("/new", methods=["GET", "POST"])
def new_package():
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

        # ★ خواندن رفرنس‌ها — هر دو حالت با براکت و بدون براکت
        references_with_bracket = request.form.getlist("references[]")
        references_without_bracket = request.form.getlist("references")

        all_references = references_with_bracket + references_without_bracket
        references = [r.strip() for r in all_references if r and r.strip()]
        # حذف تکراری‌ها با حفظ ترتیب
        references = list(dict.fromkeys(references))

        # اولین رفرنس به‌عنوان reference_no اصلی
        reference_no = references[0] if references else None

        # ★ دیباگ
        print(f"\n=== ROUTE DEBUG ===")
        print(f"  refs_with_bracket: {references_with_bracket}")
        print(f"  refs_without_bracket: {references_without_bracket}")
        print(f"  merged_references: {references}")
        print(f"  reference_no (first): {reference_no}")
        print(f"  form keys: {list(request.form.keys())}")

        # WPهای انتخاب‌شده
        selected_wps = request.form.getlist("selected_wps[]")
        selected_wps = [w.strip() for w in selected_wps if w and w.strip()]
        force_new = request.form.get("force_new_wp") == "1"
        use_force_new = force_new or (len(selected_wps) == 0)

        try:
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
                contract_number=request.form.get("contract_number", "").strip() or None,
                reference_no=reference_no,
                references=references,
                automation_number=request.form.get("automation_number", "").strip() or None,
                sender_name=request.form.get("sender_name", "").strip() or None,
                sender_type=request.form.get("sender_type", "other"),
                source_type=request.form.get("sender_type", "other"),
                description=request.form.get("description", "").strip() or None,
                contractor_id=_to_int(request.form.get("contractor_id")),
                project_id=_to_int(request.form.get("project_id")),
                force_new_wp=use_force_new,
            )
        except Exception as exc:
            print(f"❌ register_package exception: {exc}")
            import traceback
            traceback.print_exc()
            flash(f"خطا در ثبت: {exc}", "danger")
            return render_template(
                "work_package/new.html",
                draft=request.form,
                **_choices(),
            )

        print(f"\n=== new_package result ===")
        print(f"  ok: {result.get('ok')}")
        print(f"  error: {result.get('error')}")
        print(f"  package_id: {result.get('package_id')}")
        print(f"  dfc_code: {result.get('dfc_code')}")
        print(f"  references_count: {result.get('references_count')}")

        if not result["ok"]:
            flash(result.get("error", "خطا در ثبت"), "danger")
            return render_template(
                "work_package/new.html",
                draft=request.form,
                **_choices(),
            )

        package_id = result.get("package_id")

        if selected_wps and package_id:
            try:
                wp_service.link_package_to_wps(
                    package_id=package_id,
                    wp_codes=selected_wps,
                    linked_by=_uid(),
                    primary_wp=selected_wps[0],
                )
            except Exception as exc:
                print(f"⚠️ link_package_to_wps error: {exc}")

        try:
            if package_id:
                wp_sla_service.recalculate_sla(package_id, actor_id=_uid())
        except Exception as exc:
            print(f"⚠️ recalculate_sla error: {exc}")

        flash(
            f"سند با کد {result['dfc_code']} در پکیج "
            f"{result['work_package_code']} ثبت شد.",
            "success",
        )

        if package_id:
            return redirect(f"/work-package/{package_id}")
        return redirect("/work-package/")

    return render_template(
        "work_package/new.html",
        draft={},
        **_choices(),
    )