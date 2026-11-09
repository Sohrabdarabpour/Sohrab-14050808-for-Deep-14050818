"""
روت‌های نوتیفیکیشن
"""
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)

from . import notification_bp
from services.workflow import NotificationService
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


# ============================================================
# ★ لیست کامل نوتیفیکیشن‌ها
# ============================================================
@notification_bp.route("/", methods=["GET"])
@login_required
def list_notifications():
    """صفحه لیست نوتیفیکیشن‌ها"""
    user_id = session.get("user_id")
    unread_only = request.args.get("unread") == "1"

    notifications = NotificationService.list_for_user(
        user_id=user_id,
        unread_only=unread_only,
        limit=100,
    )

    unread_count = NotificationService.get_unread_count(user_id)

    return render_template(
        "notifications/list.html",
        notifications=notifications,
        unread_only=unread_only,
        unread_count=unread_count,
    )


# ============================================================
# ★★★ لیست کارشناس‌ها (کارت‌ها) ★★★
# ============================================================
@notification_bp.route("/by-expert", methods=["GET"])
@login_required
def by_expert():
    """لیست کارشناس‌ها به‌صورت کارت"""
    user_id = session.get("user_id")

    experts = NotificationService.get_experts_with_notifications(
        user_id=user_id
    )

    total_unread = sum(e.get("unread", 0) for e in experts) if experts else 0

    return render_template(
        "notifications/by_expert.html",
        experts=experts,
        total_unread=total_unread,
    )


# ============================================================
# ★★★ یادداشت‌های یک کارشناس خاص ★★★
# ============================================================
@notification_bp.route("/expert/<int:expert_id>", methods=["GET"])
@login_required
def expert_notifications(expert_id):
    """صفحه یادداشت‌های یک کارشناس خاص"""
    user_id = session.get("user_id")

    data = NotificationService.get_expert_notifications(
        user_id=user_id,
        expert_id=expert_id,
    )

    if not data:
        flash("کارشناس یافت نشد", "danger")
        return redirect(url_for("notifications.by_expert"))

    return render_template(
        "notifications/expert_detail.html",
        expert=data["expert"],
        notes=data["notes"],
        stats=data["stats"],
    )


# ============================================================
# ★ AJAX — لیست برای dropdown (فقط نخوانده‌ها)
# ============================================================
@notification_bp.route("/dropdown", methods=["GET"])
@login_required
def dropdown():
    """لیست نوتیف‌های نخوانده برای dropdown هدر (JSON)"""
    user_id = session.get("user_id")

    notifications = NotificationService.list_for_user(
        user_id=user_id,
        unread_only=True,
        limit=15,
    )

    unread_count = NotificationService.get_unread_count(user_id)

    return jsonify({
        "success": True,
        "count": len(notifications),
        "unread_count": unread_count,
        "notifications": notifications,
    })


# ============================================================
# ★ AJAX — تعداد نخوانده
# ============================================================
@notification_bp.route("/unread-count", methods=["GET"])
@login_required
def unread_count():
    """تعداد نوتیف‌های نخوانده (برای badge زنگ)"""
    user_id = session.get("user_id")
    count = NotificationService.get_unread_count(user_id)

    return jsonify({
        "success": True,
        "count": count,
    })


# ============================================================
# ★★★ علامت خوانده‌شده (تکی) — یکپارچه ★★★
# ============================================================
@notification_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    """
    علامت‌گذاری نوتیفیکیشن به عنوان خوانده‌شده
    - برای AJAX: JSON برمی‌گرداند
    - برای فرم معمولی: redirect می‌کند
    """
    success = NotificationService.mark_read(notification_id)

    # ─── درخواست AJAX ───
    if (request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"):
        if success:
            return jsonify({"success": True})
        return jsonify({
            "success": False,
            "message": "خطا در علامت‌گذاری",
        }), 400

    # ─── درخواست فرم معمولی ───
    return redirect(url_for("notifications.list_notifications"))


# ============================================================
# ★★★ تبدیل به نخوانده — یکپارچه ★★★
# ============================================================
@notification_bp.route("/<int:notification_id>/unread", methods=["POST"])
@login_required
def mark_unread(notification_id):
    """
    برگرداندن نوتیفیکیشن به حالت نخوانده
    ★ کاربر می‌تواند نوتیفیکیشن خوانده‌شده را دوباره نخوانده کند
    """
    success = NotificationService.mark_unread(notification_id)

    # ─── درخواست AJAX ───
    if (request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"):
        if success:
            return jsonify({"success": True})
        return jsonify({
            "success": False,
            "message": "خطا در تبدیل به نخوانده",
        }), 400

    # ─── درخواست فرم معمولی ───
    return redirect(url_for("notifications.list_notifications"))


# ============================================================
# ★ علامت همه خوانده‌شده
# ============================================================
@notification_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    """علامت‌گذاری همه نوتیف‌ها"""
    user_id = session.get("user_id")
    NotificationService.mark_all_read(user_id)

    if (request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"):
        return jsonify({"success": True})

    flash("همه نوتیف‌ها خوانده شدند", "success")
    return redirect(url_for("notifications.list_notifications"))


# ============================================================
# ★ حذف نوتیف (تکی)
# ============================================================
@notification_bp.route("/<int:notification_id>/dismiss", methods=["POST"])
@login_required
def dismiss(notification_id):
    """حذف یک نوتیف"""
    NotificationService.dismiss(notification_id)

    if (request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"):
        return jsonify({"success": True})

    return redirect(url_for("notifications.list_notifications"))


# ============================================================
# ★ کلیک روی نوتیف
# ============================================================
@notification_bp.route("/<int:notification_id>/click", methods=["GET"])
@login_required
def click(notification_id):
    """کلیک روی نوتیف — علامت خوانده‌شده + ریدایرکت به لینک"""
    user_id = session.get("user_id")
    notifications = NotificationService.list_for_user(
        user_id=user_id, limit=200
    )

    target = None
    for n in notifications:
        if n["id"] == notification_id:
            target = n
            break

    if not target:
        flash("نوتیف یافت نشد", "danger")
        return redirect(url_for("notifications.list_notifications"))

    NotificationService.mark_read(notification_id)

    link = target.get("link") or ""

    if link and "/assistant" in link:
        link = ""

    if not link:
        note_id = target.get("note_id")
        document_id = target.get("document_id")

        if note_id:
            link = f"/workflow/note/{note_id}"
        elif document_id:
            link = f"/documents/view/{document_id}"
        else:
            link = url_for("notifications.list_notifications")

    return redirect(link)


# ============================================================
# ★★★ همه نوتیف‌های یک یادداشت را خوانده کن ★★★
# ============================================================
@notification_bp.route("/note/<int:note_id>/read-all", methods=["POST"])
@login_required
def read_all_for_note(note_id):
    """همه نوتیف‌های مربوط به یک یادداشت را خوانده کن"""
    user_id = session.get("user_id")
    NotificationService.mark_all_read_for_note(
        user_id=user_id,
        note_id=note_id,
    )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True})

    return redirect(url_for("notifications.list_notifications"))


# ============================================================
# ★★★ همه نوتیف‌های یک یادداشت را حذف کن ★★★
# ============================================================
@notification_bp.route("/note/<int:note_id>/dismiss-all", methods=["POST"])
@login_required
def dismiss_all_for_note(note_id):
    """همه نوتیف‌های یک یادداشت را حذف کن"""
    user_id = session.get("user_id")
    NotificationService.dismiss_all_for_note(
        user_id=user_id,
        note_id=note_id,
    )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True})

    return redirect(url_for("notifications.list_notifications"))


# ============================================================
# ★★★ همه نوتیف‌های یک کارشناس را خوانده کن ★★★
# ============================================================
@notification_bp.route("/expert/<int:expert_id>/read-all", methods=["POST"])
@login_required
def read_all_for_expert(expert_id):
    """همه نوتیف‌های یک کارشناس را خوانده کن"""
    user_id = session.get("user_id")
    NotificationService.mark_all_read_for_expert(
        user_id=user_id,
        expert_id=expert_id,
    )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True})

    return redirect(url_for("notifications.by_expert"))