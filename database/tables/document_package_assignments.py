"""ارجاع‌های سند (درخت ارجاع)."""

TABLE_NAME = "document_package_assignments"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_package_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL,
            parent_id INTEGER,

            from_user_id INTEGER,
            to_user_id INTEGER,
            to_department_id INTEGER,

            assignee_role TEXT DEFAULT 'expert',
            action TEXT NOT NULL DEFAULT 'route',
            instruction TEXT,
            is_primary INTEGER DEFAULT 0,

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

            FOREIGN KEY (package_id) REFERENCES document_packages(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES document_package_assignments(id) ON DELETE CASCADE,
            FOREIGN KEY (from_user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (to_user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (to_department_id) REFERENCES departments(id) ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_dpa_package
       ON document_package_assignments(package_id)""",
    """CREATE INDEX IF NOT EXISTS idx_dpa_to_user_status
       ON document_package_assignments(to_user_id, status)""",
    """CREATE INDEX IF NOT EXISTS idx_dpa_parent
       ON document_package_assignments(parent_id)""",
    """CREATE INDEX IF NOT EXISTS idx_dpa_primary
       ON document_package_assignments(package_id, is_primary)""",
    """CREATE INDEX IF NOT EXISTS idx_dpa_due
       ON document_package_assignments(due_date, status)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)