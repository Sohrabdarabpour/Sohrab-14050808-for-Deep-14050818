"""جدول assistant_feedback — بازخورد 👍/👎 کاربران به پاسخ دستیار.

مانند assistant_logs، این جدول در کد استفاده می‌شد ولی ساخته نمی‌شد و
ثبت بازخورد همیشه بی‌صدا شکست می‌خورد (در حالی که به کاربر «ثبت شد»
نمایش داده می‌شد).
"""

TABLE_NAME = "assistant_feedback"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS assistant_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            answer TEXT,
            rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_assistant_feedback_user
        ON assistant_feedback(user_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_assistant_feedback_rating
        ON assistant_feedback(rating)
    """,
]


def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
