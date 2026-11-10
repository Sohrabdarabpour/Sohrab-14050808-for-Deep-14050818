"""سرویس پیشنهاد پکیج برای نامه‌های ورودی جدید.

سه مکانیزم:
1. جستجوی دقیق بر اساس شماره نامه فرستنده (sender_ref_no)
2. جستجوی هوشمند بر اساس پیمانکار / پروژه / کلمات کلیدی موضوع
3. پیشنهاد بر اساس آخرین اسناد مشابه
"""

from database.connection import get_connection


# ============================================================
# ★ ۱. جستجوی دقیق بر اساس شماره نامه
# ============================================================
def find_by_sender_ref_no(ref_no: str) -> list[dict]:
    """اگر نامه‌ای با همین شماره قبلاً ثبت شده باشد، پکیجش را برگردان."""
    if not ref_no or not ref_no.strip():
        return []

    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT id, package_code, subject, stage,
                   sender_name, sender_ref_no, date_received
            FROM documents
            WHERE sender_ref_no = ?
            ORDER BY id DESC
            LIMIT 5
        """, (ref_no.strip(),)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


# ============================================================
# ★ ۲. پیشنهاد هوشمند (بر اساس پیمانکار، پروژه، موضوع)
# ============================================================
def suggest_packages(
    *,
    subject: str | None = None,
    contractor_id: int | None = None,
    project_id: int | None = None,
    sender_name: str | None = None,
    group_id: int | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    پیشنهاد پکیج‌های مشابه بر اساس امتیازدهی.

    امتیاز:
    - شماره پروژه یکسان: +۱۰
    - پیمانکار یکسان: +۵
    - گروه یکسان: +۲
    - کلمات مشترک در موضوع: +۱ برای هر کلمه
    """
    connection = get_connection()
    try:
        # فیلترهای سخت (اگر داده شده)
        where = []
        params = []

        if project_id:
            where.append("project_id = ?")
            params.append(project_id)

        if contractor_id:
            where.append("contractor_id = ?")
            params.append(contractor_id)

        # اگر هیچ فیلتر سختی نبود، حداقل بر اساس کلمات کلیدی جستجو کن
        if not where and not subject:
            # آخرین ۱۰ سند
            rows = connection.execute("""
                SELECT id, package_code, subject, stage,
                       sender_name, contractor_id, project_id,
                       group_id, date_received
                FROM documents
                WHERE stage NOT IN ('archived', 'cancelled')
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

        where_sql = " AND ".join(where) if where else "1=1"

        # استخراج کلمات کلیدی موضوع
        keywords = []
        if subject:
            # کلمات طولانی‌تر از ۳ حرف
            keywords = [w.strip() for w in subject.split() if len(w.strip()) > 3][:5]

        # جستجو با فیلترهای سخت + کلمات کلیدی
        if keywords:
            keyword_clauses = " OR ".join(["subject LIKE ?"] * len(keywords))
            keyword_params = [f"%{kw}%" for kw in keywords]
            sql = f"""
                SELECT id, package_code, subject, stage,
                       sender_name, contractor_id, project_id,
                       group_id, date_received
                FROM documents
                WHERE stage NOT IN ('archived', 'cancelled')
                  AND ({where_sql})
                  AND ({keyword_clauses})
                ORDER BY
                  CASE WHEN contractor_id = ? THEN 0 ELSE 1 END,
                  CASE WHEN project_id = ? THEN 0 ELSE 1 END,
                  id DESC
                LIMIT ?
            """
            full_params = params + keyword_params + [
                contractor_id or -1,
                project_id or -1,
                limit,
            ]
            rows = connection.execute(sql, full_params).fetchall()
        else:
            sql = f"""
                SELECT id, package_code, subject, stage,
                       sender_name, contractor_id, project_id,
                       group_id, date_received
                FROM documents
                WHERE stage NOT IN ('archived', 'cancelled')
                  AND ({where_sql})
                ORDER BY id DESC
                LIMIT ?
            """
            rows = connection.execute(sql, params + [limit]).fetchall()

        return [dict(r) for r in rows]
    finally:
        connection.close()


# ============================================================
# ★ ۳. پیشنهاد پیوست به یک پکیج موجود
# ============================================================
def suggest_attach_target(document_id: int) -> dict | None:
    """اگر نامه به یک پکیج موجود مرتبط است، اطلاعات آن را برگردان."""
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT id, package_code, subject, stage,
                   sender_name, sender_ref_no
            FROM documents
            WHERE id = ?
        """, (document_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()