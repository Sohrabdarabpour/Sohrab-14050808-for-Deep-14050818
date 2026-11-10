"""جدول document_watchers — افراد در جریان (CC)."""

TABLE_NAME = "document_watchers"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_watchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reason TEXT,
            added_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(document_id, user_id),
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_watch_user
       ON document_watchers(user_id)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)