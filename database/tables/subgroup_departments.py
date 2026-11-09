"""جدول subgroup_departments — اتصال زیرگروه به دپارتمان

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "subgroup_departments"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS subgroup_departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subgroup_id INTEGER NOT NULL,
            department_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subgroup_id) REFERENCES document_subgroups(id)
                ON DELETE CASCADE,
            FOREIGN KEY (department_id) REFERENCES departments(id)
                ON DELETE CASCADE,
            UNIQUE(subgroup_id, department_id)
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_subgroup_dept_subgroup
        ON subgroup_departments(subgroup_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_subgroup_dept_department
        ON subgroup_departments(department_id)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
