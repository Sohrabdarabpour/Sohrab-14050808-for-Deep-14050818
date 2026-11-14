"""جدول شمارنده‌های اتمیک برای DFC و WP."""

TABLE_NAME = "document_package_counters"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_package_counters (
            kind TEXT NOT NULL,
            year INTEGER NOT NULL,
            last_value INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (kind, year)
        )
    """

INDEX_SQL = []


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)