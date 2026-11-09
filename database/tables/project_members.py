"""جدول project_members — اعضای پروژه

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "project_members"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS project_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            responsibility TEXT,
            notes TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_by INTEGER,
            removed_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
                ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE,
            FOREIGN KEY (role_id) REFERENCES project_roles(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (assigned_by) REFERENCES users(id)
                ON DELETE SET NULL,
            UNIQUE(project_id, user_id, role_id)
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_pm_project
        ON project_members(project_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_pm_user
        ON project_members(user_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_pm_role
        ON project_members(role_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_pm_active
        ON project_members(is_active)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
