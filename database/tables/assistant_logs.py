"""جدول assistant_logs — لاگ پرسش‌های دستیار هوشمند.

این جدول پیش‌تر در کد استفاده می‌شد (routes/ai/assistant.py) ولی هرگز
ساخته نمی‌شد؛ در نتیجه همه‌ی لاگ‌ها بی‌صدا دور ریخته می‌شدند و آمار
دستیار همیشه صفر بود.
"""

TABLE_NAME = "assistant_logs"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS assistant_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            intent TEXT,
            elapsed_ms INTEGER,
            status TEXT DEFAULT 'ok',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_assistant_logs_user
        ON assistant_logs(user_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_assistant_logs_intent
        ON assistant_logs(intent)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_assistant_logs_created
        ON assistant_logs(created_at)
    """,
]


def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
