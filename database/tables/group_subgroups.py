"""جدول group_subgroups — اتصال گروه به زیرگروه

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "group_subgroups"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS group_subgroups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            subgroup_id INTEGER NOT NULL,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES document_groups(id)
                ON DELETE CASCADE,
            FOREIGN KEY (subgroup_id) REFERENCES document_subgroups(id)
                ON DELETE CASCADE,
            UNIQUE(group_id, subgroup_id)
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_group_subgroups_group
        ON group_subgroups(group_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_group_subgroups_subgroup
        ON group_subgroups(subgroup_id)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
