"""تایم‌لاین غیرقابل‌تغییر سند (append-only)."""

TABLE_NAME = "document_package_events"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_package_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL,
            actor_id INTEGER,
            event_type TEXT NOT NULL,
            summary TEXT,
            payload TEXT,
            assignment_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (package_id) REFERENCES document_packages(id) ON DELETE CASCADE,
            FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_dpe_package_created
       ON document_package_events(package_id, created_at)""",
    """CREATE INDEX IF NOT EXISTS idx_dpe_type
       ON document_package_events(event_type)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)