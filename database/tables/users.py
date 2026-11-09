"""جدول users — کاربران

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "users"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'expert',
            email TEXT,
            phone TEXT,
            national_code TEXT,
            position TEXT,
            gender TEXT DEFAULT 'male',
            department_id INTEGER,
            avatar TEXT DEFAULT 'default.png',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            last_seen TIMESTAMP,
            is_online INTEGER DEFAULT 0,
            FOREIGN KEY(department_id) REFERENCES departments(id)
        )
    """

INDEX_SQL = []

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
