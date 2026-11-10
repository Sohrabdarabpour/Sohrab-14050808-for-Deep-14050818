"""سرویس تکمیل مدارک (document_completion_requests).

قابلیت‌ها:
- ثبت درخواست تکمیل مدارک (کتبی یا شفاهی)
- افزودن چک‌لیست مدارک
- علامت‌گذاری مدارک دریافت‌شده
- محاسبه درصد تکمیل
"""

from database.connection import get_connection
from services.documents import event_service


# ============================================================
# ★ ثبت درخواست تکمیل مدارک
# ============================================================
def create_completion_request(
    document_id: int,
    requested_by: int,
    *,
    mode: str = "written",  # written | verbal
    contractor_id: int | None = None,
    request_date: str | None = None,
    due_date: str | None = None,
    note: str | None = None,
    items: list[str] | None = None,
) -> dict:
    """ثبت درخواست تکمیل مدارک + چک‌لیست اولیه."""
    if not document_id:
        return {"ok": False, "error": "شناسه سند الزامی است"}

    connection = get_connection()
    try:
        # ثبت درخواست
        cursor = connection.execute("""
            INSERT INTO document_completion_requests
            (document_id, requested_by, contractor_id,
             mode, request_date, due_date, status, note)
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
        """, (
            document_id, requested_by, contractor_id,
            mode, request_date, due_date, note,
        ))
        request_id = cursor.lastrowid

        # ثبت آیتم‌های چک‌لیست
        if items:
            for i, title in enumerate(items):
                if not title or not title.strip():
                    continue
                connection.execute("""
                    INSERT INTO document_completion_items
                    (request_id, title, sort_order)
                    VALUES (?, ?, ?)
                """, (request_id, title.strip(), i))

        connection.commit()
    except Exception as exc:
        connection.rollback()
        return {"ok": False, "error": f"خطا در ثبت: {exc}"}
    finally:
        connection.close()

    # ثبت رویداد
    try:
        event_service.log_event(
            document_id=document_id,
            actor_id=requested_by,
            event_type=event_service.EventType.COMPLETION_REQUESTED,
            summary=f"درخواست تکمیل مدارک ({mode})",
            payload={
                "request_id": request_id,
                "items_count": len(items) if items else 0,
            },
        )
    except Exception:
        pass

    return {"ok": True, "request_id": request_id}


# ============================================================
# ★ علامت‌گذاری دریافت یک مدرک
# ============================================================
def mark_item_received(
    item_id: int, received: bool, actor_id: int
) -> dict:
    connection = get_connection()
    try:
        item = connection.execute("""
            SELECT i.*, r.document_id
            FROM document_completion_items i
            JOIN document_completion_requests r ON r.id = i.request_id
            WHERE i.id = ?
        """, (item_id,)).fetchone()

        if not item:
            return {"ok": False, "error": "آیتم پیدا نشد"}

        from helpers.date_helper import now_tehran_str
        now = now_tehran_str() if received else None

        connection.execute("""
            UPDATE document_completion_items
            SET is_received = ?, received_at = ?
            WHERE id = ?
        """, (1 if received else 0, now, item_id))
        connection.commit()

        # بررسی وضعیت کل درخواست
        _update_request_status(item["request_id"], connection)

        # رویداد
        try:
            event_service.log_event(
                document_id=item["document_id"],
                actor_id=actor_id,
                event_type=event_service.EventType.COMPLETION_FULFILLED if received else "completion_item_unchecked",
                summary=f"مدرک «{item['title']}» {'دریافت شد' if received else 'لغو شد'}",
                payload={"item_id": item_id, "received": received},
            )
        except Exception:
            pass

        return {"ok": True}
    finally:
        connection.close()


# ============================================================
# ★ به‌روزرسانی وضعیت درخواست (open/partial/fulfilled)
# ============================================================
def _update_request_status(request_id: int, connection):
    row = connection.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN is_received = 1 THEN 1 ELSE 0 END) AS received
        FROM document_completion_items
        WHERE request_id = ?
    """, (request_id,)).fetchone()

    total = row["total"] or 0
    received = row["received"] or 0

    if total == 0:
        return
    if received == 0:
        status = "open"
    elif received == total:
        status = "fulfilled"
    else:
        status = "partial"

    from helpers.date_helper import now_tehran_str
    fulfilled_at = now_tehran_str() if status == "fulfilled" else None

    connection.execute("""
        UPDATE document_completion_requests
        SET status = ?, fulfilled_at = ?
        WHERE id = ?
    """, (status, fulfilled_at, request_id))


# ============================================================
# ★ لیست درخواست‌های تکمیل مدارک یک سند
# ============================================================
def list_requests(document_id: int) -> list[dict]:
    connection = get_connection()
    try:
        requests = connection.execute("""
            SELECT r.*, u.full_name AS requested_by_name
            FROM document_completion_requests r
            LEFT JOIN users u ON u.id = r.requested_by
            WHERE r.document_id = ?
            ORDER BY r.created_at DESC, r.id DESC
        """, (document_id,)).fetchall()

        result = []
        for req in requests:
            req_dict = dict(req)
            items = connection.execute("""
                SELECT * FROM document_completion_items
                WHERE request_id = ?
                ORDER BY sort_order, id
            """, (req["id"],)).fetchall()
            req_dict["items"] = [dict(i) for i in items]
            
            # محاسبه درصد
            total = len(items)
            received = sum(1 for i in items if i["is_received"])
            req_dict["total_items"] = total
            req_dict["received_items"] = received
            req_dict["progress"] = round((received / total * 100) if total else 0)
            
            result.append(req_dict)
        return result
    finally:
        connection.close()