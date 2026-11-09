"""
روت‌های یادداشت گردش‌کار — نسخه اصلاح‌شده

★ تغییرات اصلی:
   - view_note: پاس دادن current_handler و is_current_handler به قالب
   - note_candidates: بهبود خطاها و امکان دیباگ
   - حفظ ساختار و URLهای قبلی
"""
from flask import (
    render_template, request, redirect, url_for,
    flash, session, jsonify, current_app,
)
from . import workflow_bp
from services.workflow import NoteService, NotificationService
from security.decorators import login_required


# ============================================================
# ★ کمکی — کاربر جاری
# ============================================================
def _user():
    return {
        "id": session.get("user_id"),
        "role": session.get("role"),
        "full_name": session.get("full_name"),
    }


def _is_ajax():
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.is_json
    )


# ============================================================
# ★ کارتابل
# ============================================================
@workflow_bp.route("/inbox", methods=["GET"])
@login_required
def inbox():
    u = _user()
    role = u["role"]

    notes = NoteService.get_inbox(user_id=u["id"], role_code=None)

    role_notes = []
    if role in ("supervisor", "manager", "admin", "doc_controller"):
        raw = NoteService.get_inbox(user_id=u["id"], role_code=role)
        already = {n["id"] for n in notes}
        role_notes = [n for n in raw if n["id"] not in already]

    return render_template("workflow/inbox.html",
                           notes=notes, role_notes=role_notes, current_role=role)


# ============================================================
# ★ مشاهده یادداشت
# ============================================================
@workflow_bp.route("/note/<int:note_id>", methods=["GET"])
@login_required
def view_note(note_id):
    from database.init_db import get_note, get_document, get_user

    u = _user()

    note = get_note(note_id)
    if not note:
        flash("یادداشت یافت نشد", "danger")
        return redirect(url_for("workflow.inbox"))

    document = get_document(note["document_id"])
    if not document:
        flash("سند یافت نشد", "danger")
        return redirect(url_for("workflow.inbox"))

    events = NoteService.get_events(note_id)

    # ★★★ کاربری که یادداشت در کارتابلش قرار دارد ★★★
    current_handler = None
    assigned_to = note.get("assigned_to")
    if assigned_to:
        current_handler = get_user(assigned_to)

    # ★★★ آیا کاربر جاری همان دارنده فعلی کارتابل است؟ ★★★
    is_current_handler = (
        assigned_to is not None
        and int(assigned_to) == int(u["id"])
    )

    return render_template(
        "workflow/note_view.html",
        note=note,
        document=document,
        events=events,
        current_handler=current_handler,       # ★ جدید
        is_current_handler=is_current_handler, # ★ جدید
        current_user=u,                        # ★ جدید
    )


# ============================================================
# ★ ثبت یادداشت جدید (فرم معمولی)
# ============================================================
@workflow_bp.route("/add/<int:document_id>", methods=["POST"])
@login_required
def add_note(document_id):
    u = _user()
    content = (request.form.get("content") or "").strip()

    if not content:
        flash("متن یادداشت الزامی است", "danger")
        return redirect(url_for("documents.view_document", doc_id=document_id))

    result = NoteService.submit_note(document_id, u["id"], content)

    if result["success"]:
        flash("✅ یادداشت ثبت شد", "success")
    else:
        for m in result.get("errors", {}).values():
            flash(m, "danger")

    return redirect(
        url_for("workflow.view_note", note_id=result.get("note_id"))
        if result.get("note_id")
        else url_for("documents.view_document", doc_id=document_id)
    )


# ============================================================
# ★ AJAX — ثبت یادداشت (از داشبورد)
# ============================================================
@workflow_bp.route("/note", methods=["POST"])
@login_required
def add_note_dashboard():
    """ثبت یادداشت از داشبورد (JSON) — روت قدیمی"""
    u = _user()

    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()

    document_id = data.get("document_id")
    content = (data.get("content") or "").strip()

    if not document_id:
        return jsonify({
            "success": False,
            "message": "شناسه سند ارسال نشده",
        }), 400

    if not content:
        return jsonify({
            "success": False,
            "message": "متن یادداشت الزامی است",
        }), 400

    try:
        document_id = int(document_id)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "شناسه سند نامعتبر است",
        }), 400

    result = NoteService.submit_note(
        document_id=document_id,
        user_id=u["id"],
        content=content,
    )

    if result.get("success"):
        return jsonify({
            "success": True,
            "note_id": result.get("note_id"),
            "message": "یادداشت با موفقیت ثبت شد",
        })

    errors = result.get("errors", {})
    message = next(iter(errors.values()), "خطا در ثبت یادداشت")
    return jsonify({
        "success": False,
        "message": message,
        "errors": errors,
    }), 400


# ============================================================
# ★ AJAX — ثبت یادداشت جدید
# ============================================================
@workflow_bp.route("/add-note-ajax", methods=["POST"])
@login_required
def add_note_ajax():
    """ثبت یادداشت جدید از طریق AJAX"""
    u = _user()

    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()

    document_id = data.get("document_id")
    content = (data.get("content") or "").strip()

    if not document_id:
        return jsonify({
            "success": False,
            "message": "شناسه سند ارسال نشده",
        }), 400

    if not content:
        return jsonify({
            "success": False,
            "message": "متن یادداشت الزامی است",
        }), 400

    try:
        document_id = int(document_id)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "شناسه سند نامعتبر است",
        }), 400

    result = NoteService.submit_note(
        document_id=document_id,
        user_id=u["id"],
        content=content,
    )

    if result.get("success"):
        return jsonify({
            "success": True,
            "note_id": result.get("note_id"),
            "message": "یادداشت با موفقیت ثبت شد",
        })

    errors = result.get("errors", {})
    message = next(iter(errors.values()), "خطا در ثبت یادداشت")
    return jsonify({
        "success": False,
        "message": message,
        "errors": errors,
    }), 400


# ============================================================
# ★ کامنت
# ============================================================
@workflow_bp.route("/note/<int:note_id>/comment", methods=["POST"])
@login_required
def add_comment(note_id):
    u = _user()
    content = (request.form.get("content") or "").strip()

    if not content:
        if _is_ajax():
            return jsonify({"success": False, "message": "متن کامنت الزامی است"}), 400
        flash("متن کامنت الزامی است", "danger")
        return redirect(url_for("workflow.view_note", note_id=note_id))

    result = NoteService.add_comment(note_id, u["id"], content)

    if _is_ajax():
        if result["success"]:
            return jsonify({"success": True, "message": "کامنت ثبت شد"})
        return jsonify({
            "success": False,
            "message": next(iter(result.get("errors", {}).values()), "خطا"),
        }), 400

    if result["success"]:
        flash("✅ کامنت ثبت شد", "success")
    else:
        for m in result.get("errors", {}).values():
            flash(m, "danger")

    return redirect(url_for("workflow.view_note", note_id=note_id))


# ============================================================
# ★ تایید
# ============================================================
@workflow_bp.route("/note/<int:note_id>/approve", methods=["POST"])
@login_required
def approve_note(note_id):
    u = _user()
    comment = (request.form.get("comment") or "").strip() or None
    next_id = request.form.get("next_assignee_id")
    if next_id:
        try:
            next_id = int(next_id)
        except (ValueError, TypeError):
            next_id = None

    # ★★★ کاربر جاری = دارنده فعلی کارتابل ★★★
    # (سرویس خودش با current_handler_id=u["id"] سرپرست را تعیین می‌کند)
    result = NoteService.approve_note(note_id, u["id"], comment, next_id)

    if result["success"]:
        if result.get("is_closed"):
            flash("✅ یادداشت خاتمه یافت", "success")
        else:
            flash(f"✅ ارسال شد به «{result.get('assigned_to', '')}»", "success")
    else:
        for m in result.get("errors", {}).values():
            flash(m, "danger")

    return redirect(request.form.get("next") or url_for("workflow.inbox"))


# ============================================================
# ★ خاتمه
# ============================================================
@workflow_bp.route("/note/<int:note_id>/finalize", methods=["POST"])
@login_required
def finalize_note(note_id):
    u = _user()
    comment = (request.form.get("comment") or "").strip() or None
    result = NoteService.approve_note(note_id, u["id"], comment, None)
    if result["success"]:
        flash("✅ یادداشت خاتمه یافت", "success")
    else:
        for m in result.get("errors", {}).values():
            flash(m, "danger")
    return redirect(request.form.get("next") or url_for("workflow.inbox"))


# ============================================================
# ★ رد
# ============================================================
@workflow_bp.route("/note/<int:note_id>/reject", methods=["POST"])
@login_required
def reject_note(note_id):
    u = _user()
    reason = (request.form.get("reason") or "").strip()
    result = NoteService.reject_note(note_id, u["id"], reason)
    if result["success"]:
        flash("❌ یادداشت رد شد", "warning")
    else:
        for m in result.get("errors", {}).values():
            flash(m, "danger")
    return redirect(request.form.get("next") or url_for("workflow.inbox"))


# ============================================================
# ★ برگشت
# ============================================================
@workflow_bp.route("/note/<int:note_id>/return", methods=["POST"])
@login_required
def return_note(note_id):
    u = _user()
    reason = (request.form.get("reason") or "").strip()
    result = NoteService.return_to_previous(note_id, u["id"], reason)
    if result["success"]:
        flash(f"↩️ به «{result.get('previous_step', '')}» برگشت", "info")
    else:
        for m in result.get("errors", {}).values():
            flash(m, "danger")
    return redirect(request.form.get("next") or url_for("workflow.inbox"))


# ============================================================
# ★★★ ارجاع — با کنترل نقش ★★★
# ============================================================
@workflow_bp.route("/note/<int:note_id>/forward", methods=["POST"])
@login_required
def forward_note(note_id):
    """ارجاع یادداشت — کنترل مجاز بودن در سرویس"""
    u = _user()
    to_user_id = request.form.get("to_user_id")
    message = (request.form.get("reason") or "").strip() or None

    if not to_user_id:
        flash("کاربر انتخاب نشده", "danger")
        return redirect(url_for("workflow.view_note", note_id=note_id))

    try:
        to_user_id = int(to_user_id)
    except (ValueError, TypeError):
        flash("شناسه کاربر نامعتبر است", "danger")
        return redirect(url_for("workflow.view_note", note_id=note_id))

    # ★ سرویس خودش چک می‌کنه که کاربر مقصد مجاز هست یا نه
    result = NoteService.forward_note(note_id, u["id"], to_user_id, message)

    if result["success"]:
        flash(f"✅ به «{result.get('assigned_to', '')}» ارجاع شد", "success")
    else:
        for m in result.get("errors", {}).values():
            flash(m, "danger")

    return redirect(request.form.get("next") or url_for("workflow.inbox"))


# ============================================================
# ★ بازگشایی
# ============================================================
@workflow_bp.route("/note/<int:note_id>/reopen", methods=["POST"])
@login_required
def reopen_note(note_id):
    u = _user()
    allowed = ("admin", "manager", "supervisor", "doc_controller")
    if u["role"] not in allowed:
        flash("دسترسی ندارید", "danger")
        return redirect(url_for("workflow.view_note", note_id=note_id))

    reason = (request.form.get("reason") or "").strip()
    target = request.form.get("target_step_id")
    if target:
        try:
            target = int(target)
        except (ValueError, TypeError):
            target = None

    # ★★★ کاربر جاری = دارنده فعلی کارتابل ★★★
    result = NoteService.reopen_note(note_id, u["id"], reason, target)
    if result["success"]:
        flash(f"🔓 بازگشایی شد → «{result.get('target_step', '')}»", "success")
    else:
        for m in result.get("errors", {}).values():
            flash(m, "danger")
    return redirect(url_for("workflow.view_note", note_id=note_id))


# ============================================================
# ★ AJAX — تعداد در انتظار
# ============================================================
@workflow_bp.route("/pending-count", methods=["GET"])
@login_required
def pending_count():
    return jsonify({
        "success": True,
        "count": NoteService.get_pending_count(_user()["id"])
    })


# ============================================================
# ★★★ AJAX — کاندیدهای مرحله بعد ★★★
# ============================================================
@workflow_bp.route("/note/<int:note_id>/candidates", methods=["GET"])
@login_required
def note_candidates(note_id):
    """
    لیست کاربران مرحله بعد
    ★ در سرویس، current_handler_id = note.assigned_to استفاده می‌شود
    """
    # ★ دیباگ موقت — در محیط production حذف کنید
    if current_app.debug:
        try:
            from database.init_db import get_note, get_user
            _n = get_note(note_id)
            if _n:
                _h = get_user(_n.get("assigned_to")) if _n.get("assigned_to") else None
                print(
                    f"🔍 note_candidates: note={note_id} | "
                    f"assigned_to={_n.get('assigned_to')} | "
                    f"handler={_h.get('full_name') if _h else '—'} | "
                    f"dept_id={_h.get('department_id') if _h else '—'}"
                )
        except Exception as e:
            print(f"⚠️ debug error: {e}")

    result = NoteService.get_next_step_candidates(note_id)

    if not result.get("success"):
        return jsonify({
            "success": False,
            "error": result.get("error", "خطا در دریافت کاندیدها"),
        }), 400

    # ★ دیباگ: نام کاندیدها را چاپ کن
    if current_app.debug:
        try:
            names = [c.get("full_name") for c in result.get("candidates", [])]
            print(f"🔍 candidates: {names}")
        except Exception:
            pass

    return jsonify(result)


# ============================================================
# ★★★ AJAX — کاربران مجاز برای ارجاع ★★★
# ============================================================
@workflow_bp.route("/users-for-forward", methods=["GET"])
@login_required
def users_for_forward():
    """لیست کاربران مجاز برای ارجاع — بر اساس نقش کاربر جاری"""
    u = _user()
    users = NoteService.get_forward_targets(user_id=u["id"])

    return jsonify({
        "success": True,
        "count": len(users),
        "users": users,
    })


# ============================================================
# ★ AJAX — مراحل برای بازگشایی
# ============================================================
@workflow_bp.route("/reopen-steps", methods=["GET"])
@login_required
def reopen_steps_list():
    from database.init_db import get_all_workflow_steps
    steps = get_all_workflow_steps(only_active=True)
    return jsonify({
        "success": True,
        "count": len(steps),
        "steps": [
            {
                "id": s["id"],
                "title": s["title"],
                "code": s["code"],
                "step_order": s["step_order"],
            }
            for s in steps
        ],
    })


# ============================================================
# ★ AJAX — تاریخچه سند
# ============================================================
@workflow_bp.route("/history/<int:document_id>", methods=["GET"])
@login_required
def document_history(document_id):
    """تاریخچه رخدادهای یک سند (JSON)"""
    events = NoteService.get_document_events(document_id)
    return jsonify({
        "success": True,
        "count": len(events),
        "history": events,
    })


# ============================================================
# ★ سوابق یادداشت‌های من
# ============================================================
@workflow_bp.route("/my-notes", methods=["GET"])
@login_required
def my_notes():
    """صفحه‌ی سوابق یادداشت‌های کاربر جاری"""
    u = _user()
    status_filter = request.args.get("status")

    if status_filter not in ("in_review", "approved", "rejected"):
        status_filter = None

    notes = NoteService.get_user_notes(
        user_id=u["id"],
        status_filter=status_filter,
    )

    stats = NoteService.get_user_notes_stats(u["id"])

    return render_template(
        "workflow/my_notes.html",
        notes=notes,
        stats=stats,
        current_filter=status_filter,
    )