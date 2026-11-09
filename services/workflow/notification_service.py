"""
سرویس نوتیفیکیشن — ایجاد و مدیریت نوتیفیکیشن‌ها
"""
from database.init_db import (
    create_notification,
    get_user_notifications,
    get_unread_notifications_count,
    mark_notification_read,
    mark_notification_unread,      # ★ جدید
    mark_all_notifications_read,
    dismiss_notification,
    get_user,
    get_document,
)
from helpers.date_helper import DateHelper


class NotificationService:
    """سرویس نوتیفیکیشن"""

    # ============================================================
    # ★ ایجاد
    # ============================================================
    @staticmethod
    def create(
        user_id,
        title,
        message=None,
        link=None,
        notification_type="info",
        document_id=None,
        note_id=None,
    ):
        """ایجاد نوتیفیکیشن"""
        if not user_id:
            return None

        # ★ جلوگیری از ذخیره لینک به صفحه دستیار
        if link and "/assistant" in link:
            link = None

        # ★ ساخت لینک خودکار
        if not link and note_id:
            link = f"/workflow/note/{note_id}"
        elif not link and document_id:
            link = f"/documents/view/{document_id}"

        return create_notification(
            user_id=user_id,
            title=title,
            message=message,
            link=link,
            notification_type=notification_type,
            document_id=document_id,
            note_id=note_id,
        )

    # ============================================================
    # ★ خواندن
    # ============================================================
    @staticmethod
    def list_for_user(user_id, unread_only=False, limit=50):
        if not user_id:
            return []
        notifications = get_user_notifications(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit,
        )
        return [
            NotificationService._enrich_notification_dates(n)
            for n in notifications
        ]

    @staticmethod
    def get_unread_count(user_id):
        if not user_id:
            return 0
        return get_unread_notifications_count(user_id)

    # ============================================================
    # ★ علامت‌گذاری
    # ============================================================
    @staticmethod
    def mark_read(notification_id):
        return mark_notification_read(notification_id)

    # ★★★ متد جدید: تبدیل به نخوانده ★★★
    @staticmethod
    def mark_unread(notification_id):
        """برگرداندن نوتیفیکیشن به حالت نخوانده"""
        return mark_notification_unread(notification_id)

    @staticmethod
    def mark_all_read(user_id):
        if not user_id:
            return False
        return mark_all_notifications_read(user_id)

    @staticmethod
    def dismiss(notification_id):
        return dismiss_notification(notification_id)

    # ============================================================
    # ★ کمکی — تبدیل تاریخ
    # ============================================================
    @staticmethod
    def _enrich_notification_dates(notif):
        if not notif:
            return notif
        if not isinstance(notif, dict):
            try:
                notif = dict(notif)
            except (TypeError, ValueError):
                return notif

        created = notif.get("created_at")
        if created:
            notif["created_at_jalali"] = DateHelper.format_jalali_datetime(
                created, show_time=True
            )
        else:
            notif["created_at_jalali"] = ""
        return notif

    # ============================================================
    # ★★★ گروه‌بندی بر اساس کارشناس ★★★
    # ============================================================
    @staticmethod
    def get_experts_with_notifications(user_id):
        """لیست کارشناس‌هایی که روی یادداشت‌هاشون فعالیت شده"""
        if not user_id:
            return []

        from database.connection import get_connection
        conn = get_connection()
        try:
            sql = """
                SELECT
                    u.id              AS expert_id,
                    u.full_name       AS expert_name,
                    u.username        AS expert_username,
                    u.avatar          AS expert_avatar,
                    COUNT(n.id)       AS total_count,
                    SUM(CASE WHEN n.is_read = 0 THEN 1 ELSE 0 END) AS unread_count,
                    MAX(n.created_at) AS latest_at
                FROM notifications n
                INNER JOIN document_notes nt ON nt.id = n.note_id
                INNER JOIN users u ON u.id = nt.user_id
                WHERE n.user_id = ?
                  AND n.note_id IS NOT NULL
                  AND n.is_dismissed = 0
                GROUP BY u.id
                ORDER BY latest_at DESC
            """
            rows = conn.execute(sql, (user_id,)).fetchall()

            experts = []
            for row in rows:
                r = dict(row)

                latest_title_row = conn.execute(
                    """
                    SELECT n.title
                    FROM notifications n
                    INNER JOIN document_notes nt ON nt.id = n.note_id
                    WHERE n.user_id = ?
                      AND nt.user_id = ?
                      AND n.note_id IS NOT NULL
                      AND n.is_dismissed = 0
                    ORDER BY n.created_at DESC
                    LIMIT 1
                    """,
                    (user_id, r["expert_id"]),
                ).fetchone()

                latest_title = (
                    latest_title_row["title"] if latest_title_row else ""
                )

                type_rows = conn.execute(
                    """
                    SELECT n.notification_type, COUNT(*) AS cnt
                    FROM notifications n
                    INNER JOIN document_notes nt ON nt.id = n.note_id
                    WHERE n.user_id = ?
                      AND nt.user_id = ?
                      AND n.note_id IS NOT NULL
                      AND n.is_dismissed = 0
                    GROUP BY n.notification_type
                    """,
                    (user_id, r["expert_id"]),
                ).fetchall()

                types = {t["notification_type"]: t["cnt"] for t in type_rows}

                experts.append({
                    "expert": {
                        "id": r["expert_id"],
                        "full_name": r["expert_name"] or "کاربر",
                        "username": r["expert_username"] or "",
                        "avatar": r["expert_avatar"],
                    },
                    "total": r["total_count"],
                    "unread": r["unread_count"] or 0,
                    "latest_at": DateHelper.format_jalali_datetime(
                        r["latest_at"], show_time=True
                    ) if r["latest_at"] else "",
                    "latest_title": latest_title,
                    "types": types,
                })

            return experts
        finally:
            conn.close()

    # ============================================================
    # ★★★ نوتیف‌های یک کارشناس خاص ★★★
    # ============================================================
    @staticmethod
    def get_expert_notifications(user_id, expert_id):
        """
        نوتیف‌های مربوط به یادداشت‌های یک کارشناس — گروه‌بندی بر اساس یادداشت
        """
        if not user_id or not expert_id:
            return None

        expert = get_user(expert_id)
        if not expert:
            return None

        from database.connection import get_connection
        conn = get_connection()
        try:
            # ★ توجه: document_notes جدید فقط status داره، action_type نداره
            sql = """
                SELECT n.*,
                       d.subject AS document_subject,
                       d.code_dfc AS document_code,
                       nt.status AS note_status,
                       nt.created_at AS note_created_at,
                       nt.updated_at AS note_updated_at
                FROM notifications n
                INNER JOIN document_notes nt ON nt.id = n.note_id
                LEFT JOIN documents d ON d.id = n.document_id
                WHERE n.user_id = ?
                  AND nt.user_id = ?
                  AND n.note_id IS NOT NULL
                  AND n.is_dismissed = 0
                ORDER BY n.created_at DESC
                LIMIT 500
            """
            rows = conn.execute(sql, (user_id, expert_id)).fetchall()

            notes_map = {}
            for row in rows:
                n = dict(row)
                n = NotificationService._enrich_notification_dates(n)

                note_id = n.get("note_id")
                if not note_id:
                    continue

                if note_id not in notes_map:
                    notes_map[note_id] = {
                        "note_id": note_id,
                        "document_id": n.get("document_id"),
                        "document_subject": n.get("document_subject") or "بدون موضوع",
                        "document_code": n.get("document_code") or "",
                        "note_status": n.get("note_status") or "in_review",
                        "note_created_at": n.get("note_created_at") or "",
                        "note_updated_at": n.get("note_updated_at") or "",
                        "latest_status": "in_review",
                        "latest_title": n.get("title") or "",
                        "latest_message": n.get("message") or "",
                        "latest_at": n.get("created_at_jalali") or "",
                        "latest_at_raw": n.get("created_at") or "",
                        "notification_id": n.get("id"),
                        "unread_count": 0,
                        "notifications": [],
                    }

                notes_map[note_id]["notifications"].append(n)

            # ★ وضعیت نهایی از خود status یادداشت
            for note_id, data in notes_map.items():
                latest = data["notifications"][0]

                data["latest_status"] = NotificationService._resolve_final_status(
                    note_status=data.get("note_status"),
                    latest_notif=latest,
                )
                data["latest_title"] = latest.get("title") or ""
                data["latest_message"] = latest.get("message") or ""
                data["latest_at"] = latest.get("created_at_jalali") or ""
                data["latest_at_raw"] = latest.get("created_at") or ""
                data["notification_id"] = latest.get("id")
                data["unread_count"] = sum(
                    1 for x in data["notifications"] if not x.get("is_read")
                )

            notes_list = sorted(
                notes_map.values(),
                key=lambda x: x.get("latest_at_raw") or "",
                reverse=True,
            )

            total = len(notes_list)
            unread = sum(1 for n in notes_list if n["unread_count"] > 0)

            stats = {
                "total": total,
                "unread": unread,
                "read": total - unread,
            }

            return {
                "expert": {
                    "id": expert.get("id"),
                    "full_name": expert.get("full_name") or "کاربر",
                    "username": expert.get("username") or "",
                    "avatar": expert.get("avatar"),
                },
                "notes": notes_list,
                "stats": stats,
            }
        finally:
            conn.close()

    # ============================================================
    # ★ کمکی — تعیین وضعیت نهایی
    # ============================================================
    @staticmethod
    def _resolve_final_status(note_status, latest_notif):
        """
        تعیین وضعیت نهایی از روی status یادداشت
        (ساختار جدید — فقط in_review / approved / rejected)
        """
        ns = (note_status or "").strip().lower()

        status_map = {
            "in_review": "in_review",
            "approved": "approved",
            "rejected": "rejected",
            "closed": "approved",
        }

        if ns in status_map:
            return status_map[ns]

        # ★ fallback — از عنوان نوتیف
        return NotificationService._detect_status(latest_notif)

    @staticmethod
    def _detect_status(notif):
        """تشخیص وضعیت از نوتیف"""
        if not notif:
            return "in_review"

        title = (notif.get("title") or "").strip()
        ntype = (notif.get("notification_type") or "").strip()

        if "تایید نهایی" in title or "تأیید نهایی" in title:
            return "approved"
        if "تایید" in title or "تأیید" in title:
            return "approved"
        if "رد" in title:
            return "rejected"
        if "برگشت" in title or "برگشتی" in title:
            return "in_review"
        if "در انتظار" in title or "جدید" in title:
            return "in_review"

        if ntype == "success":
            return "approved"
        if ntype == "danger":
            return "rejected"
        if ntype == "warning":
            return "in_review"

        return "info"

    # ============================================================
    # ★★★ عملیات گروهی — بر اساس یادداشت ★★★
    # ============================================================
    @staticmethod
    def mark_all_read_for_note(user_id, note_id):
        """همه نوتیف‌های یک یادداشت را خوانده کن"""
        if not user_id or not note_id:
            return False

        from database.connection import get_connection
        conn = get_connection()
        try:
            conn.execute("""
                UPDATE notifications
                SET is_read = 1,
                    read_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                  AND note_id = ?
                  AND is_read = 0
                  AND is_dismissed = 0
            """, (user_id, note_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"❌ خطا در read-all note: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def dismiss_all_for_note(user_id, note_id):
        """همه نوتیف‌های یک یادداشت را حذف کن"""
        if not user_id or not note_id:
            return False

        from database.connection import get_connection
        conn = get_connection()
        try:
            conn.execute("""
                UPDATE notifications
                SET is_dismissed = 1,
                    is_read = 1,
                    read_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                  AND note_id = ?
                  AND is_dismissed = 0
            """, (user_id, note_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"❌ خطا در dismiss-all note: {e}")
            return False
        finally:
            conn.close()

    # ============================================================
    # ★★★ عملیات گروهی — بر اساس کارشناس ★★★
    # ============================================================
    @staticmethod
    def mark_all_read_for_expert(user_id, expert_id):
        """همه نوتیف‌های یک کارشناس را خوانده کن"""
        if not user_id or not expert_id:
            return False

        from database.connection import get_connection
        conn = get_connection()
        try:
            conn.execute("""
                UPDATE notifications
                SET is_read = 1,
                    read_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                  AND is_read = 0
                  AND is_dismissed = 0
                  AND note_id IN (
                      SELECT id FROM document_notes WHERE user_id = ?
                  )
            """, (user_id, expert_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"❌ خطا در read-all expert: {e}")
            return False
        finally:
            conn.close()

    # ============================================================
    # ★ قالب‌های آماده
    # ============================================================
    @staticmethod
    def notify_note_pending(user_id, note_id, document_id, from_user_id, step_title):
        """یادداشت جدید در انتظار شما"""
        doc = get_document(document_id) or {}
        from_user = get_user(from_user_id) or {}
        from_name = from_user.get("full_name", "کاربر")
        doc_subject = doc.get("subject") or "بدون موضوع"

        return NotificationService.create(
            user_id=user_id,
            title="🔔 یادداشت جدید در انتظار شما",
            message=f"{from_name} روی سند «{doc_subject}» یادداشت ثبت کرد — مرحله: {step_title}",
            link=f"/workflow/note/{note_id}",
            notification_type="info",
            document_id=document_id,
            note_id=note_id,
        )

    @staticmethod
    def notify_note_approved(user_id, note_id, document_id, by_user_id, is_final=False):
        """یادداشت تایید شد"""
        doc = get_document(document_id) or {}
        by_user = get_user(by_user_id) or {}
        by_name = by_user.get("full_name", "کاربر")
        doc_subject = doc.get("subject") or "بدون موضوع"

        if is_final:
            title = "✅ یادداشت شما تایید نهایی شد"
            message = f"{by_name} یادداشت شما روی سند «{doc_subject}» را تایید نهایی کرد"
        else:
            title = "✅ یادداشت شما تایید شد"
            message = f"{by_name} یادداشت شما روی سند «{doc_subject}» را تایید کرد"

        return NotificationService.create(
            user_id=user_id,
            title=title,
            message=message,
            link=f"/workflow/note/{note_id}",
            notification_type="success",
            document_id=document_id,
            note_id=note_id,
        )

    @staticmethod
    def notify_note_rejected(user_id, note_id, document_id, by_user_id, reason=None):
        """یادداشت رد شد"""
        doc = get_document(document_id) or {}
        by_user = get_user(by_user_id) or {}
        by_name = by_user.get("full_name", "کاربر")
        doc_subject = doc.get("subject") or "بدون موضوع"

        message = f"{by_name} یادداشت شما روی سند «{doc_subject}» را رد کرد"
        if reason:
            message += f"\nدلیل: {reason}"

        return NotificationService.create(
            user_id=user_id,
            title="❌ یادداشت شما رد شد",
            message=message,
            link=f"/workflow/note/{note_id}",
            notification_type="danger",
            document_id=document_id,
            note_id=note_id,
        )

    @staticmethod
    def notify_note_edited(user_id, note_id, document_id, by_user_id):
        """یادداشت ویرایش شد"""
        doc = get_document(document_id) or {}
        by_user = get_user(by_user_id) or {}
        by_name = by_user.get("full_name", "کاربر")
        doc_subject = doc.get("subject") or "بدون موضوع"

        return NotificationService.create(
            user_id=user_id,
            title="✏️ یادداشت شما ویرایش شد",
            message=f"{by_name} یادداشت شما روی سند «{doc_subject}» را ویرایش کرد",
            link=f"/workflow/note/{note_id}",
            notification_type="info",
            document_id=document_id,
            note_id=note_id,
        )

    @staticmethod
    def notify_note_returned(user_id, note_id, document_id, by_user_id, from_step_title, reason=None):
        """یادداشت برگشت داده شد"""
        doc = get_document(document_id) or {}
        by_user = get_user(by_user_id) or {}
        by_name = by_user.get("full_name", "کاربر")
        doc_subject = doc.get("subject") or "بدون موضوع"

        message = f"{by_name} یادداشت سند «{doc_subject}» را از مرحله «{from_step_title}» برگشت داد"
        if reason:
            message += f"\nدلیل: {reason}"

        return NotificationService.create(
            user_id=user_id,
            title="↩️ یادداشت برگشتی",
            message=message,
            link=f"/workflow/note/{note_id}",
            notification_type="warning",
            document_id=document_id,
            note_id=note_id,
        )