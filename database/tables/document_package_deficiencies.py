"""درخواست‌های رفع نقص (نواقص مدارک)."""

TABLE_NAME = "document_package_deficiencies"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_package_deficiencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL,
            assignment_id INTEGER,
            mode TEXT NOT NULL DEFAULT 'written',
            reference_no TEXT,
            request_date TEXT,
            due_date TEXT,
            items TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            requested_by INTEGER,
            fulfilled_at TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (package_id) REFERENCES document_packages(id) ON DELETE CASCADE,
            FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE SET NULL
        )
    """

CREATE_ITEMS_SQL = """
        CREATE TABLE IF NOT EXISTS document_package_deficiency_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            is_received INTEGER DEFAULT 0,
            received_at TEXT,
            note TEXT,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (request_id) REFERENCES document_package_deficiencies(id) ON DELETE CASCADE
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_dpd_package
       ON document_package_deficiencies(package_id)""",
    """CREATE INDEX IF NOT EXISTS idx_dpd_status
       ON document_package_deficiencies(status)""",
    """CREATE INDEX IF NOT EXISTS idx_dpdi_request
       ON document_package_deficiency_items(request_id)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    cursor.execute(CREATE_ITEMS_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)