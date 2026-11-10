"""تست ثبت سند با شماره‌گذاری اتمیک.

این فایل را بعد از تأیید حذف کنید.
"""

from database.connection import get_connection
from services.documents.package_service import (
    Stage, register_document, change_stage, get_package,
)


def main():
    print("=" * 60)
    print("تست ثبت سند")
    print("=" * 60)

    # کاربر 1 (admin) را به عنوان ثبت‌کننده استفاده می‌کنیم
    c = get_connection()
    user = c.execute("SELECT id, full_name FROM users WHERE id = 1").fetchone()
    if not user:
        user = c.execute("SELECT id, full_name FROM users LIMIT 1").fetchone()
    c.close()

    if not user:
        print("❌ هیچ کاربری در دیتابیس نیست")
        return

    user_id = user["id"]
    print(f"کاربر: {user['full_name']} (id={user_id})")

    # ---- ثبت سند ----
    result = register_document(
        subject="تست ثبت پکیج سند — اولین سند",
        registered_by=user_id,
        source_type="internal",
        priority="high",
        sender_name="واحد تست",
        description="این یک سند تست است",
    )
    print()
    print("نتیجه ثبت:", result)

    if not result["ok"]:
        return

    doc_id = result["document_id"]
    print(f"✅ سند #{doc_id} با کد {result['package_code']} ثبت شد")

    # ---- خواندن پکیج ----
    pkg = get_package(doc_id)
    print()
    print(f"کد پکیج: {pkg['package_code']}")
    print(f"موضوع: {pkg['subject']}")
    print(f"مرحله: {pkg['stage']}")
    print(f"ثبت‌کننده: {pkg['registered_by_name']}")

    # ---- ثبت سند دوم (بررسی شماره‌گذاری اتمیک) ----
    print()
    print("=" * 60)
    print("تست شماره‌گذاری اتمیک (سند دوم)")
    print("=" * 60)
    result2 = register_document(
        subject="تست ثبت پکیج سند — دومین سند",
        registered_by=user_id,
        source_type="contractor",
    )
    print(f"✅ سند دوم با کد: {result2['package_code']}")

    # ---- تغییر مرحله ----
    print()
    print("=" * 60)
    print("تست تغییر مرحله")
    print("=" * 60)
    r = change_stage(doc_id, Stage.ROUTED, actor_id=user_id,
                     reason="ارجاع به سرپرست")
    print(f"ثبت اول → routed: {r}")

    # ---- آرشیو مستقیم (باید رد شود) ----
    r = change_stage(doc_id, Stage.ARCHIVED, actor_id=user_id)
    print(f"routed → archived (باید رد شود): {r}")

    # ---- تایم‌لاین ----
    print()
    print("=" * 60)
    print("تایم‌لاین سند")
    print("=" * 60)
    from services.documents import event_service
    events = event_service.list_events(doc_id)
    for e in events:
        print(f"  - {e['event_type']}: {e['summary']}")


if __name__ == "__main__":
    main()