"""جدول document_assignments — ارجاع‌های سند (هسته‌ی کارتابل)."""

TABLE_NAME = "document_assignments"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            parent_id INTEGER,

            from_user_id INTEGER,
            to_user_id INTEGER,
            to_department_id INTEGER,

            assignee_role TEXT,
            action TEXT NOT NULL DEFAULT 'route',
            instruction TEXT,

            priority TEXT DEFAULT 'normal',
            due_date TEXT,
            due_days INTEGER,

            status TEXT NOT NULL DEFAULT 'pending',

            read_at TEXT,
            accepted_at TEXT,
            completed_at TEXT,
            returned_at TEXT,
            cancelled_at TEXT,
            cancel_reason TEXT,

            is_overdue INTEGER DEFAULT 0,
            overdue_days INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES document_assignments(id) ON DELETE CASCADE,
            FOREIGN KEY (from_user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (to_user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (to_department_id) REFERENCES departments(id) ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_assign_to_status
       ON document_assignments(to_user_id, status)""",
    """CREATE INDEX IF NOT EXISTS idx_assign_doc
       ON document_assignments(document_id)""",
    """CREATE INDEX IF NOT EXISTS idx_assign_parent
       ON document_assignments(parent_id)""",
    """CREATE INDEX IF NOT EXISTS idx_assign_due
       ON document_assignments(due_date, status)""",
    """CREATE INDEX IF NOT EXISTS idx_assign_overdue
       ON document_assignments(is_overdue)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)