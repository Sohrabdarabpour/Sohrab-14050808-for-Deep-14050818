"""
Helper — چک دسترسی‌های گردش‌کار
"""
from flask import session
from database.init_db import (
    get_note,
    get_document,
    get_department_supervisor,
    get_workflow_step,
    get_next_workflow_step,
)


# ============================================================
# ★ توابع پایه
# ============================================================
def _uid():
    return session.get("user_id")


def _role():
    return session.get("role")


def is_workflow_admin():
    """آیا کاربر admin/manager است؟"""
    return _role() in ("admin", "manager")


def is_document_owner(document):
    """آیا کاربر جاری مالک سند است؟"""
    if not document:
        return False
    return document.get("user_id") == _uid()


def is_supervisor_of_department(department_id):
    """آیا کاربر جاری سرپرست این دپارتمان است؟"""
    if not department_id or not _uid():
        return False
    supervisor = get_department_supervisor(department_id)
    return bool(supervisor and supervisor["id"] == _uid())


# ============================================================
# ★ دسترسی به یادداشت‌ها
# ============================================================
def can_add_note(document_id):
    """آیا کاربر می‌تونه یادداشت جدید ثبت کنه؟"""
    if not _uid():
        return False
    document = get_document(document_id)
    return bool(document)


def can_view_note(note_id):
    """آیا کاربر می‌تونه این یادداشت رو ببینه؟"""
    if not _uid():
        return False

    if is_workflow_admin():
        return True

    note = get_note(note_id)
    if not note:
        return False

    # ★ مسئول فعلی
    if note.get("assigned_to") == _uid():
        return True

    # ★ نویسنده
    if note.get("user_id") == _uid():
        return True

    # ★ مالک سند
    document = get_document(note.get("document_id"))
    if is_document_owner(document):
        return True

    # ★ سرپرست دپارتمان
    if document:
        dept_id = document.get("department_id")
        if is_supervisor_of_department(dept_id):
            return True

    return False


# ============================================================
# ★ دسترسی به اقدامات
# ============================================================
def can_approve_note(note_id):
    """آیا کاربر می‌تونه تایید کنه؟"""
    if not _uid():
        return False

    if is_workflow_admin():
        return True

    note = get_note(note_id)
    if not note:
        return False

    if note.get("status") != "in_review":
        return False

    # ★ اگه به کاربر خاصی تخصیص داده شده
    if note.get("assigned_to"):
        return note["assigned_to"] == _uid()

    return False


def can_reject_note(note_id):
    return can_approve_note(note_id)


def can_edit_note(note_id):
    return can_approve_note(note_id)


def can_return_note(note_id):
    """برگشت فقط اگه مرحله فعلی اولین مرحله نباشه"""
    if not can_approve_note(note_id):
        return False

    note = get_note(note_id)
    if not note:
        return False

    step = get_workflow_step(note.get("current_step_id"))
    if not step:
        return False

    return step.get("step_order", 1) > 1


def can_finalize_note(note_id):
    """خاتمه فقط در آخرین مرحله"""
    if not can_approve_note(note_id):
        return False

    note = get_note(note_id)
    if not note:
        return False

    return not get_next_workflow_step(note.get("current_step_id"))


def is_final_step(note_id):
    """آیا مرحله فعلی آخرین مرحله است؟"""
    note = get_note(note_id)
    if not note:
        return False
    return not get_next_workflow_step(note.get("current_step_id"))


# ============================================================
# ★ بازگشایی
# ============================================================
def can_reopen_note(note_id):
    """بازگشایی فقط برای یادداشت‌های قفل‌شده"""
    if not _uid():
        return False

    if _role() not in ("admin", "manager", "supervisor", "doc_controller"):
        return False

    note = get_note(note_id)
    if not note:
        return False

    # ★ فقط یادداشت‌های غیر in_review
    return note.get("status") != "in_review"


# ============================================================
# ★ لیست اقدامات مجاز
# ============================================================
def get_note_actions_for_user(note_id):
    """لیست اقدامات مجاز کاربر روی یادداشت"""
    actions = []

    if can_approve_note(note_id):
        actions.append("approve")

    if can_reject_note(note_id):
        actions.append("reject")

    if can_edit_note(note_id):
        actions.append("edit")

    if can_return_note(note_id):
        actions.append("return")

    if can_finalize_note(note_id):
        actions.append("finalize")

    if can_reopen_note(note_id):
        actions.append("reopen")

    return actions