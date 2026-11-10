"""جدول document_counters — شمارنده‌ی اتمیک شماره‌گذاری پکیج."""

TABLE_NAME = "document_counters"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_counters (
            year INTEGER PRIMARY KEY,
            last_value INTEGER NOT NULL DEFAULT 0
        )
    """

INDEX_SQL = []


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)