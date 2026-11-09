"""
سرویس یادداشت — نسخه نهایی با منطقه زمانی ایران
هر یادداشت = یک رکورد
هر اقدام = یک رکورد در note_events

★ قوانین کلیدی:
   ۱. همه زمان‌ها به وقت ایران (Asia/Tehran) ثبت می‌شوند
   ۲. سرپرست مرحله بعد = سرپرست دپارتمانِ کاربری که یادداشت
      در کارتابلش قرار دارد (assigned_to)
   ۳. هیچ ملاک دیگری (نویسنده، دپارتمان سند، ...) در تعیین
      سرپرست در نظر گرفته نمی‌شود
"""
from database.init_db import (
    create_note, get_note, update_note,
    get_notes_for_user, get_notes_for_role,
    create_note_event, get_note_events, get_document_events,
    get_document, get_user,
    get_all_workflow_steps, get_workflow_step,
    get_workflow_step_by_code, get_next_workflow_step,
    get_department_supervisor, get_users_by_role,
)
from database.connection import get_connection
from helpers.date_helper import (
    DateHelper,
    now_tehran_str,
    now_tehran,
)
from .notification_service import NotificationService


# ════════════════════════════════════════════════════════════════
# ★ ثابت‌ها
# ════════════════════════════════════════════════════════════════
DEPT_DOC_CONTROL = "document_control"   # کد دپارتمان کنترل مستندات
ROLE_ADMIN_ROLES = ("admin", "manager")


class NoteService:
    """سرویس مدیریت یادداشت‌ها"""

    # ============================================================
    # ★ ثبت یادداشت جدید
    # ============================================================
    @staticmethod
    def submit_note(document_id, user_id, content):
        if not content or not content.strip():
            return {"success": False, "errors": {"content": "متن یادداشت الزامی است"}}

        document = get_document(document_id)
        if not document:
            return {"success": False, "errors": {"general": "سند یافت نشد"}}

        first_step = get_workflow_step_by_code("expert_submit")
        if not first_step:
            return {"success": False, "errors": {"general": "مرحله کارشناس تعریف نشده"}}

        next_step = get_next_workflow_step(first_step["id"])
        if not next_step:
            return {"success": False, "errors": {"general": "مرحله بعدی تعریف نشده"}}

        # ★★★ ثبت‌کننده یادداشت = دارنده فعلی کارتابل ★★★
        assignees = NoteService._find_step_assignees(
            next_step,
            document,
            current_handler_id=user_id,
        )
        if not assignees:
            return {"success": False,
                    "errors": {"general": f"مسئولی برای «{next_step['title']}» یافت نشد"}}

        primary = assignees[0]["id"]
        now_str = now_tehran_str()

        note_id = create_note(
            document_id=document_id,
            user_id=user_id,
            content=content.strip(),
            current_step_id=next_step["id"],
            assigned_to=primary,
            created_at=now_str,
            updated_at=now_str,
        )
        if not note_id:
            return {"success": False, "errors": {"general": "خطا در ذخیره"}}

        create_note_event(
            note_id=note_id,
            user_id=user_id,
            event_type="submit",
            from_step_id=first_step["id"],
            to_step_id=next_step["id"],
            to_user_id=primary,
            created_at=now_str,
        )

        for a in assignees:
            NotificationService.create(
                user_id=a["id"],
                title="🔔 یادداشت جدید در انتظار شما",
                message=f"یادداشت جدید روی سند «{document.get('subject', '')}»",
                link=f"/workflow/note/{note_id}",
                notification_type="info",
                document_id=document_id,
                note_id=note_id,
            )

        return {"success": True, "note_id": note_id}

    # ============================================================
    # ★ کامنت
    # ============================================================
    @staticmethod
    def add_comment(note_id, user_id, content):
        if not content or not content.strip():
            return {"success": False, "errors": {"content": "متن کامنت الزامی است"}}

        note = get_note(note_id)
        if not note:
            return {"success": False, "errors": {"general": "یادداشت یافت نشد"}}

        now_str = now_tehran_str()

        event_id = create_note_event(
            note_id=note_id,
            user_id=user_id,
            event_type="comment",
            message=content.strip(),
            from_step_id=note.get("current_step_id"),
            to_step_id=note.get("current_step_id"),
            created_at=now_str,
        )
        if not event_id:
            return {"success": False, "errors": {"general": "خطا در ذخیره"}}
        return {"success": True, "event_id": event_id}

    # ============================================================
    # ★ تایید → مرحله بعد یا خاتمه
    # ============================================================
    @staticmethod
    def approve_note(note_id, user_id, message=None, next_assignee_id=None):
        note = get_note(note_id)
        if not note:
            return {"success": False, "errors": {"general": "یادداشت یافت نشد"}}
        if note["status"] != "in_review":
            return {"success": False, "errors": {"general": "در وضعیت بررسی نیست"}}

        current_step = get_workflow_step(note["current_step_id"])
        if not current_step:
            return {"success": False, "errors": {"general": "مرحله فعلی یافت نشد"}}

        next_step = get_next_workflow_step(current_step["id"])
        document = get_document(note["document_id"])

        # ---- آخرین مرحله → خاتمه ----
        if not next_step:
            return NoteService._close_note(note, user_id, message)

        # ---- مسئول مرحله بعد ----
        if next_assignee_id:
            assignee = get_user(next_assignee_id)
            if not assignee:
                return {"success": False, "errors": {"general": "کاربر یافت نشد"}}
            assignees = [assignee]
        else:
            # ★★★ کاربر جاری = دارنده فعلی کارتابل ★★★
            assignees = NoteService._find_step_assignees(
                next_step,
                document,
                current_handler_id=user_id,
            )

        if not assignees:
            return {"success": False,
                    "errors": {"general": f"مسئولی برای «{next_step['title']}» یافت نشد"}}

        primary = assignees[0]["id"]
        now_str = now_tehran_str()

        update_note(
            note_id,
            current_step_id=next_step["id"],
            assigned_to=primary,
            updated_at=now_str,
        )

        create_note_event(
            note_id=note_id,
            user_id=user_id,
            event_type="approve",
            message=message,
            from_step_id=current_step["id"],
            to_step_id=next_step["id"],
            to_user_id=primary,
            created_at=now_str,
        )

        for a in assignees:
            NotificationService.create(
                user_id=a["id"],
                title="🔔 یادداشت جدید در انتظار شما",
                message=f"یادداشت روی سند «{document.get('subject', '')}»",
                link=f"/workflow/note/{note_id}",
                notification_type="info",
                document_id=note["document_id"],
                note_id=note_id,
            )

        return {
            "success": True,
            "next_step": next_step["title"],
            "assigned_to": assignees[0].get("full_name", ""),
        }

    # ============================================================
    # ★ خاتمه
    # ============================================================
    @staticmethod
    def _close_note(note, user_id, message=None):
        closed_at_tehran = now_tehran_str()

        update_note(
            note_id=note["id"],
            status="approved",
            current_step_id=None,
            assigned_to=None,
            closed_at=closed_at_tehran,
            updated_at=closed_at_tehran,
        )

        create_note_event(
            note_id=note["id"],
            user_id=user_id,
            event_type="close",
            message=message,
            from_step_id=note.get("current_step_id"),
            to_step_id=None,
            created_at=closed_at_tehran,
        )

        NotificationService.create(
            user_id=note["user_id"],
            title="✅ یادداشت شما تایید و خاتمه یافت",
            message=f"یادداشت روی سند «{note.get('document_subject', '')}» تایید شد",
            link=f"/workflow/note/{note['id']}",
            notification_type="success",
            document_id=note["document_id"],
            note_id=note["id"],
        )

        return {"success": True, "is_closed": True}

    # ============================================================
    # ★ رد
    # ============================================================
    @staticmethod
    def reject_note(note_id, user_id, reason):
        note = get_note(note_id)
        if not note:
            return {"success": False, "errors": {"general": "یادداشت یافت نشد"}}
        if note["status"] != "in_review":
            return {"success": False, "errors": {"general": "در وضعیت بررسی نیست"}}
        if not reason or not reason.strip():
            return {"success": False, "errors": {"reason": "دلیل رد الزامی است"}}

        current_step = get_workflow_step(note["current_step_id"])
        now_str = now_tehran_str()

        update_note(
            note_id,
            status="rejected",
            current_step_id=None,
            assigned_to=note["user_id"],
            updated_at=now_str,
        )

        create_note_event(
            note_id=note_id,
            user_id=user_id,
            event_type="reject",
            message=reason.strip(),
            from_step_id=current_step["id"] if current_step else None,
            to_step_id=None,
            to_user_id=note["user_id"],
            created_at=now_str,
        )

        NotificationService.create(
            user_id=note["user_id"],
            title="❌ یادداشت شما رد شد",
            message=f"دلیل: {reason}",
            link=f"/workflow/note/{note_id}",
            notification_type="danger",
            document_id=note["document_id"],
            note_id=note_id,
        )
        return {"success": True}

    # ============================================================
    # ★ برگشت — اگه آخرین اقدام ارجاع بود، برگرد به فرستنده
    # ============================================================
    @staticmethod
    def return_to_previous(note_id, user_id, reason):
        note = get_note(note_id)
        if not note:
            return {"success": False, "errors": {"general": "یادداشت یافت نشد"}}
        if note["status"] != "in_review":
            return {"success": False, "errors": {"general": "در وضعیت بررسی نیست"}}
        if not reason or not reason.strip():
            return {"success": False, "errors": {"reason": "دلیل برگشت الزامی است"}}

        current_step = get_workflow_step(note["current_step_id"])
        if not current_step:
            return {"success": False, "errors": {"general": "مرحله فعلی یافت نشد"}}

        now_str = now_tehran_str()

        # ════════════════════════════════════════════════════════
        # ★ چک: آیا آخرین اقدام «ارجاع» بوده؟
        # ════════════════════════════════════════════════════════
        last_forward = NoteService._get_last_forward_event(note_id)

        if last_forward:
            from_user_id = last_forward.get("user_id")
            from_user = get_user(from_user_id) if from_user_id else None

            if from_user:
                update_note(
                    note_id,
                    assigned_to=from_user_id,
                    updated_at=now_str,
                )

                create_note_event(
                    note_id=note_id,
                    user_id=user_id,
                    event_type="return",
                    message=reason.strip(),
                    from_step_id=current_step["id"],
                    to_step_id=current_step["id"],
                    to_user_id=from_user_id,
                    created_at=now_str,
                )

                NotificationService.create(
                    user_id=from_user_id,
                    title="↩️ یادداشت برگشتی به شما",
                    message=(
                        f"«{note.get('user_full_name', 'کاربر')}» "
                        f"یادداشت رو برگشت داد\nدلیل: {reason}"
                    ),
                    link=f"/workflow/note/{note_id}",
                    notification_type="warning",
                    document_id=note["document_id"],
                    note_id=note_id,
                )

                return {
                    "success": True,
                    "previous_step": "ارجاع‌دهنده",
                    "returned_to": from_user.get("full_name", "کاربر"),
                }

        # ════════════════════════════════════════════════════════
        # ★ برگشت به مرحله قبل
        # ════════════════════════════════════════════════════════
        all_steps = get_all_workflow_steps(only_active=True)
        previous_step = None
        for s in all_steps:
            if s["step_order"] < current_step["step_order"]:
                if previous_step is None or s["step_order"] > previous_step["step_order"]:
                    previous_step = s

        if not previous_step:
            return {"success": False, "errors": {"general": "مرحله قبلی وجود ندارد"}}

        document = get_document(note["document_id"])

        # ★★★ کاربر جاری = دارنده فعلی کارتابل ★★★
        assignees = NoteService._find_step_assignees(
            previous_step,
            document,
            current_handler_id=user_id,
        )
        if not assignees:
            return {"success": False,
                    "errors": {"general": f"مسئولی برای «{previous_step['title']}» یافت نشد"}}

        primary = assignees[0]["id"]

        update_note(
            note_id,
            current_step_id=previous_step["id"],
            assigned_to=primary,
            updated_at=now_str,
        )

        create_note_event(
            note_id=note_id,
            user_id=user_id,
            event_type="return",
            message=reason.strip(),
            from_step_id=current_step["id"],
            to_step_id=previous_step["id"],
            to_user_id=primary,
            created_at=now_str,
        )

        for a in assignees:
            NotificationService.create(
                user_id=a["id"],
                title="↩️ یادداشت برگشتی",
                message=f"دلیل: {reason}",
                link=f"/workflow/note/{note_id}",
                notification_type="warning",
                document_id=note["document_id"],
                note_id=note_id,
            )

        return {"success": True, "previous_step": previous_step["title"]}

    # ============================================================
    # ★ ارجاع
    # ============================================================
    @staticmethod
    def forward_note(note_id, user_id, to_user_id, message=None):
        note = get_note(note_id)
        if not note:
            return {"success": False, "errors": {"general": "یادداشت یافت نشد"}}
        if note["status"] != "in_review":
            return {"success": False, "errors": {"general": "در وضعیت بررسی نیست"}}

        target = get_user(to_user_id)
        if not target:
            return {"success": False, "errors": {"general": "کاربر یافت نشد"}}

        if int(to_user_id) == int(user_id):
            return {
                "success": False,
                "errors": {"general": "نمی‌توانید به خودتان ارجاع دهید"},
            }

        allowed = NoteService.get_forward_targets(user_id)
        allowed_ids = {int(u["id"]) for u in allowed}

        if int(to_user_id) not in allowed_ids:
            return {
                "success": False,
                "errors": {"general": "شما مجاز به ارجاع به این کاربر نیستید"},
            }

        now_str = now_tehran_str()

        update_note(
            note_id,
            assigned_to=to_user_id,
            updated_at=now_str,
        )

        create_note_event(
            note_id=note_id,
            user_id=user_id,
            event_type="forward",
            message=message,
            from_step_id=note.get("current_step_id"),
            to_step_id=note.get("current_step_id"),
            to_user_id=to_user_id,
            created_at=now_str,
        )

        NotificationService.create(
            user_id=to_user_id,
            title="📩 یادداشت برای شما ارجاع شد",
            message=f"از طرف {note.get('user_full_name', 'کاربر')}",
            link=f"/workflow/note/{note_id}",
            notification_type="info",
            document_id=note["document_id"],
            note_id=note_id,
        )

        return {"success": True, "assigned_to": target.get("full_name", "")}

    # ============================================================
    # ★ بازگشایی
    # ============================================================
    @staticmethod
    def reopen_note(note_id, user_id, reason, target_step_id=None):
        note = get_note(note_id)
        if not note:
            return {"success": False, "errors": {"general": "یادداشت یافت نشد"}}
        if note["status"] == "in_review":
            return {"success": False, "errors": {"general": "این یادداشت هنوز در بررسی است"}}
        if not reason or not reason.strip():
            return {"success": False, "errors": {"reason": "دلیل بازگشایی الزامی است"}}

        document = get_document(note["document_id"])
        if not document:
            return {"success": False, "errors": {"general": "سند یافت نشد"}}

        target_step = None
        if target_step_id:
            target_step = get_workflow_step(target_step_id)
        if not target_step:
            target_step = get_workflow_step_by_code("supervisor_review")
        if not target_step:
            target_step = get_workflow_step_by_code("expert_submit")
        if not target_step:
            return {"success": False, "errors": {"general": "مرحله هدف تعریف نشده"}}

        # ★★★ کاربر جاری = دارنده فعلی کارتابل ★★★
        assignees = NoteService._find_step_assignees(
            target_step,
            document,
            current_handler_id=user_id,
        )
        if not assignees and target_step.get("code") == "expert_submit":
            author = get_user(note["user_id"])
            if author:
                assignees = [author]
        if not assignees:
            return {"success": False,
                    "errors": {"general": f"مسئولی برای «{target_step['title']}» یافت نشد"}}

        primary = assignees[0]["id"]
        now_str = now_tehran_str()

        update_note(
            note_id=note_id,
            status="in_review",
            current_step_id=target_step["id"],
            assigned_to=primary,
            closed_at=None,
            updated_at=now_str,
        )

        create_note_event(
            note_id=note_id,
            user_id=user_id,
            event_type="reopen",
            message=reason.strip(),
            from_step_id=None,
            to_step_id=target_step["id"],
            to_user_id=primary,
            created_at=now_str,
        )

        for a in assignees:
            NotificationService.create(
                user_id=a["id"],
                title="🔓 یادداشت بازگشایی شد",
                message=f"دلیل: {reason}",
                link=f"/workflow/note/{note_id}",
                notification_type="warning",
                document_id=note["document_id"],
                note_id=note_id,
            )

        return {
            "success": True,
            "target_step": target_step["title"],
            "assigned_to": assignees[0].get("full_name", ""),
        }

    # ============================================================
    # ★ کارتابل
    # ============================================================
    @staticmethod
    def get_inbox(user_id, role_code=None):
        if role_code:
            notes = get_notes_for_role(role_code, status="in_review")
        else:
            notes = get_notes_for_user(user_id, status="in_review")
        return [NoteService._enrich(n) for n in notes]

    # ============================================================
    # ★ تاریخچه
    # ============================================================
    @staticmethod
    def get_events(note_id):
        return [NoteService._enrich_event(e) for e in get_note_events(note_id)]

    @staticmethod
    def get_document_events(document_id):
        return [
            NoteService._enrich_event(e)
            for e in get_document_events(document_id)
        ]

    # ============================================================
    # ★ آمار
    # ============================================================
    @staticmethod
    def get_pending_count(user_id):
        return len(get_notes_for_user(user_id, status="in_review"))

    # ============================================================
    # ★ کاندیدهای مرحله بعد
    # ============================================================
    @staticmethod
    def get_next_step_candidates(note_id):
        note = get_note(note_id)
        if not note:
            return {"success": False, "error": "یادداشت یافت نشد"}

        document = get_document(note["document_id"])
        if not document:
            return {"success": False, "error": "سند یافت نشد"}

        current_step = get_workflow_step(note["current_step_id"])
        if not current_step:
            return {"success": False, "error": "مرحله فعلی یافت نشد"}

        next_step = get_next_workflow_step(current_step["id"])
        if not next_step:
            return {
                "success": True,
                "is_final": True,
                "next_step": None,
                "candidates": [],
            }

        # ★★★ دارنده فعلی کارتابل = assigned_to ★★★
        current_handler_id = note.get("assigned_to")

        # ★★★ پاس دادن current_handler_id ★★★
        candidates = NoteService._find_step_assignees(
            next_step,
            document,
            current_handler_id=current_handler_id,
        )

        return {
            "success": True,
            "is_final": False,
            "next_step": {
                "id": next_step["id"],
                "title": next_step["title"],
                "code": next_step["code"],
                "role_code": next_step.get("assigned_role"),
            },
            "candidates": [
                {
                    "id": c["id"],
                    "full_name": c.get("full_name", "کاربر"),
                    "username": c.get("username", "—"),
                    "avatar": c.get("avatar"),
                }
                for c in candidates
            ],
        }

    # ============================================================
    # ★ سوابق یادداشت‌های کاربر
    # ============================================================
    @staticmethod
    def get_user_notes(user_id, status_filter=None):
        if not user_id:
            return []

        connection = get_connection()
        try:
            sql = """
                SELECT n.*,
                       u.full_name AS user_full_name,
                       u.avatar AS user_avatar,
                       ws.title AS step_title,
                       ws.code AS step_code,
                       au.full_name AS assigned_to_name,
                       d.subject AS document_subject,
                       d.code_dfc AS document_code,
                       d.department_id AS document_department
                FROM document_notes n
                LEFT JOIN users u ON u.id = n.user_id
                LEFT JOIN workflow_steps ws ON ws.id = n.current_step_id
                LEFT JOIN users au ON au.id = n.assigned_to
                LEFT JOIN documents d ON d.id = n.document_id
                WHERE n.user_id = ?
            """
            params = [user_id]

            if status_filter:
                sql += " AND n.status = ?"
                params.append(status_filter)

            sql += " ORDER BY n.created_at DESC"
            rows = connection.execute(sql, params).fetchall()

            return [NoteService._enrich(dict(r)) for r in rows]
        finally:
            connection.close()

    @staticmethod
    def get_user_notes_stats(user_id):
        if not user_id:
            return {"total": 0, "in_review": 0, "approved": 0, "rejected": 0}

        connection = get_connection()
        try:
            sql = """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'in_review' THEN 1 ELSE 0 END) AS in_review,
                    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected
                FROM document_notes
                WHERE user_id = ?
            """
            row = connection.execute(sql, (user_id,)).fetchone()
            if not row:
                return {"total": 0, "in_review": 0, "approved": 0, "rejected": 0}
            return {
                "total": row["total"] or 0,
                "in_review": row["in_review"] or 0,
                "approved": row["approved"] or 0,
                "rejected": row["rejected"] or 0,
            }
        finally:
            connection.close()

    # ════════════════════════════════════════════════════════════
    # ★ لیست کاربران مجاز برای ارجاع
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def get_forward_targets(user_id):
        """
        لیست کاربرانی که کاربر جاری می‌تونه بهشون ارجاع بده.

        قوانین:
        ─────────────────────────────────────────────────
        admin / manager        → همه کاربران فعال
        expert                 → فقط سرپرست دپارتمان خودش
        supervisor (عادی)      → سرپرست کنترل مستندات + اعضای دپارتمان خودش
        supervisor (کنترل م.)  → اعضای کنترل مستندات + همه سرپرست‌های دیگه
        ─────────────────────────────────────────────────
        """
        if not user_id:
            return []

        current_user = get_user(user_id)
        if not current_user:
            return []

        role = current_user.get("role")
        dept_id = current_user.get("department_id")

        # ═══ admin / manager → همه ═══
        if role in ROLE_ADMIN_ROLES:
            return NoteService._get_all_active_users(exclude_user_id=user_id)

        # ═══ کارشناس → فقط سرپرست دپارتمانش ═══
        if role == "expert":
            if not dept_id:
                return []

            supervisor = NoteService._get_department_supervisor_by_dept(dept_id)
            if not supervisor:
                return []

            if int(supervisor["id"]) == int(user_id):
                return []

            return [supervisor]

        # ═══ سرپرست ═══
        if role == "supervisor":
            if not dept_id:
                return []

            # ─── سرپرست کنترل مستندات ───
            if NoteService._is_doc_control_supervisor(user_id):
                targets = []

                members = NoteService._get_department_members_by_id(
                    dept_id, exclude_user_id=user_id
                )
                targets.extend(members)

                other_supervisors = NoteService._get_all_other_supervisors(
                    exclude_user_id=user_id
                )
                targets.extend(other_supervisors)

                return targets

            # ─── سرپرست دپارتمان عادی ───
            targets = []

            doc_control_supervisor = NoteService._get_doc_control_supervisor()
            if (doc_control_supervisor
                    and int(doc_control_supervisor["id"]) != int(user_id)):
                targets.append(doc_control_supervisor)

            own_members = NoteService._get_department_members_by_id(
                dept_id, exclude_user_id=user_id
            )
            targets.extend(own_members)

            return targets

        # ═══ سایر نقش‌ها → اعضای دپارتمان خودش ═══
        if dept_id:
            return NoteService._get_department_members_by_id(
                dept_id, exclude_user_id=user_id
            )

        return []

    # ════════════════════════════════════════════════════════════
    # ★ کوئری‌های کمکی ارجاع
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def _get_all_active_users(exclude_user_id=None):
        """همه کاربران فعال"""
        connection = get_connection()
        try:
            query = """
                SELECT id, full_name, username, avatar, role, department_id
                FROM users
                WHERE is_active = 1
            """
            params = []
            if exclude_user_id:
                query += " AND id != ?"
                params.append(exclude_user_id)
            query += " ORDER BY full_name ASC"
            rows = connection.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            connection.close()

    @staticmethod
    def _get_department_supervisor_by_dept(dept_id):
        """سرپرست یک دپارتمان — از departments.supervisor_id"""
        if not dept_id:
            return None
        connection = get_connection()
        try:
            row = connection.execute("""
                SELECT u.id, u.full_name, u.username, u.avatar,
                       u.role, u.department_id
                FROM departments d
                JOIN users u ON u.id = d.supervisor_id
                WHERE d.id = ? AND u.is_active = 1
                LIMIT 1
            """, (dept_id,)).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    @staticmethod
    def _get_department_members_by_id(dept_id, exclude_user_id=None):
        """اعضای یک دپارتمان (بر اساس id)"""
        if not dept_id:
            return []
        connection = get_connection()
        try:
            query = """
                SELECT id, full_name, username, avatar, role, department_id
                FROM users
                WHERE department_id = ? AND is_active = 1
            """
            params = [dept_id]
            if exclude_user_id:
                query += " AND id != ?"
                params.append(exclude_user_id)
            query += " ORDER BY full_name ASC"
            rows = connection.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            connection.close()

    @staticmethod
    def _is_doc_control_supervisor(user_id):
        """آیا کاربر سرپرست دپارتمان کنترل مستندات است؟"""
        if not user_id:
            return False
        connection = get_connection()
        try:
            row = connection.execute("""
                SELECT id FROM departments
                WHERE code = ? AND supervisor_id = ? AND is_active = 1
                LIMIT 1
            """, (DEPT_DOC_CONTROL, user_id)).fetchone()
            return bool(row)
        finally:
            connection.close()

    @staticmethod
    def _get_doc_control_supervisor():
        """سرپرست دپارتمان کنترل مستندات (بدون توجه به id)"""
        connection = get_connection()
        try:
            row = connection.execute("""
                SELECT u.id, u.full_name, u.username, u.avatar,
                       u.role, u.department_id
                FROM departments d
                JOIN users u ON u.id = d.supervisor_id
                WHERE d.code = ? AND d.is_active = 1
                LIMIT 1
            """, (DEPT_DOC_CONTROL,)).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    @staticmethod
    def _get_all_other_supervisors(exclude_user_id=None):
        """همه سرپرست‌های دیگه (از departments)"""
        connection = get_connection()
        try:
            query = """
                SELECT DISTINCT u.id, u.full_name, u.username, u.avatar,
                                u.role, u.department_id
                FROM departments d
                JOIN users u ON u.id = d.supervisor_id
                WHERE d.is_active = 1 AND u.is_active = 1
            """
            params = []
            if exclude_user_id:
                query += " AND u.id != ?"
                params.append(exclude_user_id)
            query += " ORDER BY u.full_name ASC"
            rows = connection.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            connection.close()

    # ════════════════════════════════════════════════════════════
    # ★★★ مسئولین مرحله — نسخه نهایی ★★★
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def _find_step_assignees(step, document, current_handler_id=None):
        """
        تعیین مسئولین یک مرحله از workflow

        Args:
            step: مرحله workflow
            document: دیکشنری سند (فقط برای project_id)
            current_handler_id: ★ آیدی کاربری که در حال حاضر یادداشت
                                  در کارتابلش قرار دارد (assigned_to)

        ★★★ قانون کلیدی برای مرحله supervisor ★★★
        ──────────────────────────────────────────────
        سرپرستی که نمایش داده می‌شود، سرپرستِ دپارتمانِ
        "کاربری است که در حال حاضر یادداشت در کارتابلش است".

        هیچ ملاک دیگری (نویسنده یادداشت، دپارتمان سند، ...)
        در نظر گرفته نمی‌شود.
        """
        role = step.get("assigned_role")
        if not role:
            return []

        # ═══════════════════════════════════════════════════════════
        # ★★★ سرپرست → فقط سرپرست دپارتمان دارنده فعلی کارتابل ★★★
        # ═══════════════════════════════════════════════════════════
        if role == "supervisor":
            if not current_handler_id:
                return []

            handler = get_user(current_handler_id)
            if not handler:
                return []

            dept_id = handler.get("department_id")
            if not dept_id:
                return []

            # ★★★ فقط سرپرست همان دپارتمان ★★★
            sup = get_department_supervisor(dept_id)
            return [sup] if sup else []

        # ═══════════════════════════════════════════════════════════
        # ★★★ کنترل مستندات → فقط سرپرست کنترل مستندات ★★★
        # ═══════════════════════════════════════════════════════════
        if role == "doc_controller":
            sup = NoteService._get_doc_control_supervisor()
            if sup:
                return [sup]

            members = NoteService._get_department_members(DEPT_DOC_CONTROL)
            if members:
                return members

            return []

        # ═══════════════════════════════════════════════════════════
        # ★★★ سایر نقش‌ها → اعضای پروژه یا کاربران آن نقش ★★★
        # ═══════════════════════════════════════════════════════════
        project_id = document.get("project_id") if document else None
        if project_id:
            connection = get_connection()
            try:
                rows = connection.execute("""
                    SELECT u.id, u.full_name, u.username, u.avatar
                    FROM project_members pm
                    JOIN users u ON u.id = pm.user_id
                    JOIN project_roles pr ON pr.id = pm.role_id
                    WHERE pm.project_id = ? AND pr.code = ?
                      AND pm.is_active = 1 AND u.is_active = 1
                    ORDER BY pm.assigned_at ASC
                """, (project_id, role)).fetchall()
                if rows:
                    return [dict(r) for r in rows]
            finally:
                connection.close()

        return get_users_by_role(role)

    @staticmethod
    def _get_department_members(dept_code):
        """اعضای دپارتمان بر اساس کد"""
        connection = get_connection()
        try:
            dept = connection.execute("""
                SELECT id FROM departments
                WHERE code = ? AND is_active = 1
                LIMIT 1
            """, (dept_code,)).fetchone()
            if not dept:
                return []
            rows = connection.execute("""
                SELECT id, full_name, username, avatar
                FROM users
                WHERE department_id = ? AND is_active = 1
                ORDER BY full_name ASC
            """, (dept["id"],)).fetchall()
            return [dict(r) for r in rows]
        finally:
            connection.close()

    # ════════════════════════════════════════════════════════════
    # ★ Enrich — با پارس امن زمان‌های DB
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def _enrich(note):
        """★ نسخه اصلاح‌شده با parse_db_datetime"""
        if not note:
            return note
        if not isinstance(note, dict):
            note = dict(note)

        for field in ("created_at", "updated_at", "closed_at"):
            v = note.get(field)
            if v:
                parsed = DateHelper.parse_db_datetime(v)
                if parsed:
                    note[f"{field}_jalali"] = DateHelper.format_jalali_datetime(
                        parsed, show_time=True
                    )
                else:
                    note[f"{field}_jalali"] = ""
            else:
                note[f"{field}_jalali"] = ""

        return note

    @staticmethod
    def _enrich_event(event):
        """★ نسخه اصلاح‌شده با parse_db_datetime"""
        if not event:
            return event
        if not isinstance(event, dict):
            event = dict(event)

        v = event.get("created_at")
        if v:
            parsed = DateHelper.parse_db_datetime(v)
            if parsed:
                event["created_at_jalali"] = DateHelper.format_jalali_datetime(
                    parsed, show_time=True
                )
            else:
                event["created_at_jalali"] = ""
        else:
            event["created_at_jalali"] = ""

        return event

    # ============================================================
    # ★ کمکی — آخرین رخداد ارجاع روی یادداشت
    # ============================================================
    @staticmethod
    def _get_last_forward_event(note_id):
        """
        آخرین رخداد از نوع forward روی این یادداشت رو برمی‌گردونه.
        فقط اگه آخرین رخداد (بدون در نظر گرفتن comment) ارجاع بوده.

        Returns:
            dict یا None
        """
        if not note_id:
            return None

        connection = get_connection()
        try:
            row = connection.execute("""
                SELECT e.*
                FROM note_events e
                WHERE e.note_id = ?
                  AND e.event_type != 'comment'
                ORDER BY e.created_at DESC, e.id DESC
                LIMIT 1
            """, (note_id,)).fetchone()

            if not row:
                return None

            event = dict(row)

            # ★ فقط اگه آخرین اقدام «ارجاع» بوده
            if event.get("event_type") == "forward":
                return event

            return None
        finally:
            connection.close()