"""سرویس نواقص مدارک (document_package_deficiencies)."""

import json

from database.connection import get_connection
from helpers.date_helper import now_tehran_str

from . import wp_event_service


# ============================================================
# ★ ثبت درخواست
# ============================================================
def create_deficiency(
    *,
    package_id: int,
    requested_by: int,
    mode: str = "written",
    reference_no: str | None = None,
    request_date: str | None = None,
    due_date: str | None = None,
    note: str | None = None,
    items: list[str] | None = None,
) -> dict:
    """ثبت درخواست رفع نقص + چک‌لیست."""
    if not package_id:
        return {"ok": False, "error": "شناسه سند الزامی است"}

    connection = get_connection()
    try:
        # بررسی وجود سند
        pkg = connection.execute(
            "SELECT id, dfc_code FROM document_packages WHERE id = ?",
            (package_id,),
        ).fetchone()
        if not pkg:
            return {"ok": False, "error": "سند پیدا نشد"}

        items_json = None
        if items:
            try:
                items_json = json.dumps(items, ensure_ascii=False)
            except Exception:
                items_json = None

        cursor = connection.execute("""
            INSERT INTO document_package_deficiencies
            (package_id, mode, reference_no, request_date, due_date,
             items, status, requested_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?)
        """, (
            package_id, mode, reference_no, request_date, due_date,
            items_json, requested_by, note,
        ))
        request_id = cursor.lastrowid

        # ثبت آیتم‌ها
        if items:
            for i, title in enumerate(items):
                if not title or not title.strip():
                    continue
                connection.execute("""
                    INSERT INTO document_package_deficiency_items
                    (request_id, title, sort_order)
                    VALUES (?, ?, ?)
                """, (request_id, title.strip(), i))

        connection.commit()
    except Exception as exc:
        connection.rollback()
        return {"ok": False, "error": f"خطا: {exc}"}
    finally:
        connection.close()

    # رویداد
    try:
        wp_event_service.log_event(
            package_id=package_id,
            actor_id=requested_by,
            event_type=wp_event_service.EventType.DEFICIENCY_REQUESTED,
            summary=f"درخواست رفع نقص ({mode})",
            payload={
                "request_id": request_id,
                "mode": mode,
                "items_count": len(items) if items else 0,
            },
        )
    except Exception:
        pass

    return {"ok": True, "request_id": request_id}


# ============================================================
# ★ علامت‌گذاری دریافت یک مدرک
# ============================================================
def mark_item_received(item_id: int, received: bool,
                       actor_id: int) -> dict:
    connection = get_connection()
    try:
        item = connection.execute("""
            SELECT i.*, r.package_id
            FROM document_package_deficiency_items i
            JOIN document_package_deficiencies r ON r.id = i.request_id
            WHERE i.id = ?
        """, (item_id,)).fetchone()
        if not item:
            return {"ok": False, "error": "آیتم پیدا نشد"}

        now = now_tehran_str() if received else None
        connection.execute("""
            UPDATE document_package_deficiency_items
            SET is_received = ?, received_at = ?
            WHERE id = ?
        """, (1 if received else 0, now, item_id))

        # به‌روزرسانی وضعیت درخواست
        _update_status(item["request_id"], connection)
        connection.commit()
    finally:
        connection.close()

    try:
        wp_event_service.log_event(
            package_id=item["package_id"],
            actor_id=actor_id,
            event_type=(
                wp_event_service.EventType.DEFICIENCY_FULFILLED
                if received else "deficiency_item_unchecked"
            ),
            summary=f"مدرک «{item['title']}» {'دریافت شد' if received else 'لغو شد'}",
            payload={"item_id": item_id, "received": received},
        )
    except Exception:
        pass

    return {"ok": True}


def _update_status(request_id: int, connection):
    row = connection.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN is_received = 1 THEN 1 ELSE 0 END) AS received
        FROM document_package_deficiency_items
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

    fulfilled_at = now_tehran_str() if status == "fulfilled" else None
    connection.execute("""
        UPDATE document_package_deficiencies
        SET status = ?, fulfilled_at = ?
        WHERE id = ?
    """, (status, fulfilled_at, request_id))


# ============================================================
# ★ لیست درخواست‌ها
# ============================================================
def list_deficiencies(package_id: int) -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT r.*, u.full_name AS requested_by_name
            FROM document_package_deficiencies r
            LEFT JOIN users u ON u.id = r.requested_by
            WHERE r.package_id = ?
            ORDER BY r.created_at DESC, r.id DESC
        """, (package_id,)).fetchall()

        result = []
        for req in rows:
            req_dict = dict(req)
            items = connection.execute("""
                SELECT * FROM document_package_deficiency_items
                WHERE request_id = ?
                ORDER BY sort_order, id
            """, (req["id"],)).fetchall()
            req_dict["items"] = [dict(i) for i in items]

            total = len(items)
            received = sum(1 for i in items if i["is_received"])
            req_dict["total_items"] = total
            req_dict["received_items"] = received
            req_dict["progress"] = round((received / total * 100) if total else 0)
            result.append(req_dict)
        return result
    finally:
        connection.close()