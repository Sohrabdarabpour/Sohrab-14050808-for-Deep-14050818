"""جدول calendar_holidays — تعطیلات تقویم کاری.

تاریخ‌ها میلادی ذخیره می‌شوند (مثل بقیهٔ پروژه) و برای نمایش/فیلتر،
معادل شمسی و سال شمسی هم نگه داشته می‌شود.
"""

TABLE_NAME = "calendar_holidays"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS calendar_holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            holiday_date TEXT NOT NULL UNIQUE,   -- میلادی YYYY/MM/DD
            jalali_date TEXT NOT NULL,           -- شمسی YYYY/MM/DD (نمایش)
            jalali_year INTEGER NOT NULL,        -- برای فیلتر سال
            title TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'official',  -- official | company | other
            reason TEXT,                          -- علت تعطیلی
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_holidays_year
        ON calendar_holidays(jalali_year)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_holidays_active
        ON calendar_holidays(is_active, holiday_date)
    """,
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)


def migrate(cursor):
    """افزودن ستون علت به دیتابیس‌های قدیمی."""
    columns = [
        column["name"]
        for column in cursor.execute("PRAGMA table_info(calendar_holidays)").fetchall()
    ]
    if "reason" not in columns:
        cursor.execute("ALTER TABLE calendar_holidays ADD COLUMN reason TEXT")
