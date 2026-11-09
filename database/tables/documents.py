"""جدول documents — اسناد

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "documents"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_dfc TEXT,
            date_letter TEXT,
            automation_number TEXT,
            contractor_letter_number TEXT,
            subject TEXT,
            contract_number TEXT,
            project_name TEXT,
            contractor TEXT,
            area TEXT,
            date_received TEXT,
            date_referral TEXT,
            expert_name TEXT,
            unit TEXT,
            document_group TEXT,
            sub_group TEXT,
            deadline TEXT,
            request_complete_docs TEXT,
            complete_docs_by_contractor TEXT,
            doc_response_status TEXT,
            response_announce_date TEXT,
            final_send_date TEXT,
            final_letter_number TEXT,
            final_delay TEXT,
            colleague TEXT,
            Responsible_Party TEXT,
            user_id INTEGER,
            status_id INTEGER,
            area_id INTEGER,
            department_id INTEGER,
            group_id INTEGER,
            subgroup_id INTEGER,
            contractor_id INTEGER,
            project_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (status_id) REFERENCES document_statuses(id),
            FOREIGN KEY (area_id) REFERENCES areas(id),
            FOREIGN KEY (department_id) REFERENCES departments(id),
            FOREIGN KEY (group_id) REFERENCES document_groups(id),
            FOREIGN KEY (subgroup_id) REFERENCES document_subgroups(id)
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_documents_group_id
        ON documents(group_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_documents_subgroup_id
        ON documents(subgroup_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_documents_project_id
        ON documents(project_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_documents_contractor_id
        ON documents(contractor_id)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)


def migrate(cursor):
    """افزودن ستون‌های جدید به دیتابیس‌های قدیمی."""
    columns = cursor.execute("PRAGMA table_info(documents)").fetchall()
    column_names = [column["name"] for column in columns]

    if "status_id" not in column_names:
        cursor.execute("ALTER TABLE documents ADD COLUMN status_id INTEGER")
    if "area_id" not in column_names:
        cursor.execute("ALTER TABLE documents ADD COLUMN area_id INTEGER")
    if "department_id" not in column_names:
        cursor.execute("ALTER TABLE documents ADD COLUMN department_id INTEGER")
    if "group_id" not in column_names:
        cursor.execute("ALTER TABLE documents ADD COLUMN group_id INTEGER")
    if "subgroup_id" not in column_names:
        cursor.execute("ALTER TABLE documents ADD COLUMN subgroup_id INTEGER")
    if "contractor_id" not in column_names:
        cursor.execute("ALTER TABLE documents ADD COLUMN contractor_id INTEGER")
    if "project_id" not in column_names:
        cursor.execute("ALTER TABLE documents ADD COLUMN project_id INTEGER")
        cursor.execute("ALTER TABLE documents ADD COLUMN final_send_date TEXT")

    # ---- ★ مهلت پاسخ محاسبه‌شده بر اساس تقویم کاری ----
    if "sla_days" not in column_names:
        cursor.execute("ALTER TABLE documents ADD COLUMN sla_days INTEGER")
    if "sla_source" not in column_names:
        cursor.execute("ALTER TABLE documents ADD COLUMN sla_source TEXT")
    if "response_due_date" not in column_names:
        cursor.execute("ALTER TABLE documents ADD COLUMN response_due_date TEXT")
