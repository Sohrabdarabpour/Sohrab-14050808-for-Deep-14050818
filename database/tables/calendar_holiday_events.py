"""جدول calendar_holiday_events — تاریخچهٔ تغییرات تعطیلات.

هر تعطیل/غیرتعطیل کردن یک ردیف اینجا ثبت می‌شود تا علت و زمان تغییر
قابل پیگیری باشد.
"""

TABLE_NAME = "calendar_holiday_events"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS calendar_holiday_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            holiday_date TEXT NOT NULL,     -- میلادی YYYY/MM/DD
            jalali_date TEXT NOT NULL,      -- شمسی (نمایش)
            action TEXT NOT NULL,           -- added | removed
            reason TEXT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_holiday_events_date
        ON calendar_holiday_events(holiday_date)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_holiday_events_created
        ON calendar_holiday_events(created_at)
    """,
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
