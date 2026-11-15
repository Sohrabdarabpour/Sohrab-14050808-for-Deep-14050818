"""جدول document_package_references — رفرنس‌های چندگانه‌ی یک سند.

هر سند می‌تواند به چند نامه/سند قبلی اشاره کند.
هر رفرنس به‌طور جداگانه ذخیره می‌شود.
"""

TABLE_NAME = "document_package_references"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_package_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL,
            reference_no TEXT NOT NULL,
            description TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (package_id) REFERENCES document_packages(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_dpr_package
       ON document_package_references(package_id)""",
    """CREATE INDEX IF NOT EXISTS idx_dpr_ref
       ON document_package_references(reference_no)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)