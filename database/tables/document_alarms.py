"""جدول document_alarms — هشدارهای زمان‌بندی‌شده (dedupe)."""

TABLE_NAME = "document_alarms"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            assignment_id INTEGER,
            target_user_id INTEGER,

            alarm_type TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'warning',
            due_at TEXT,

            status TEXT NOT NULL DEFAULT 'pending',
            dedupe_key TEXT UNIQUE NOT NULL,
            payload TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TEXT,
            acked_at TEXT,

            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """

INDEX_SQL = [
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_alarms_dedupe
       ON document_alarms(dedupe_key)""",
    """CREATE INDEX IF NOT EXISTS idx_alarms_pending
       ON document_alarms(status, due_at)""",
    """CREATE INDEX IF NOT EXISTS idx_alarms_doc
       ON document_alarms(document_id)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)