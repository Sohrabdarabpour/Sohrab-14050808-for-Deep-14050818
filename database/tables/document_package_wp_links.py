"""جدول document_package_wp_links — اتصال یک سند به یک یا چند پکیج کاری.

هر سند می‌تواند به چند WP متصل باشد.
اگر هیچ ردیفی برای یک سند نباشد، یعنی WP جدید باید ایجاد شود.
"""

TABLE_NAME = "document_package_wp_links"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_package_wp_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL,
            work_package_code TEXT NOT NULL,
            is_primary INTEGER DEFAULT 0,
            linked_by INTEGER,
            linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (package_id) REFERENCES document_packages(id) ON DELETE CASCADE,
            FOREIGN KEY (linked_by) REFERENCES users(id) ON DELETE SET NULL,
            UNIQUE(package_id, work_package_code)
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_dpwl_package
       ON document_package_wp_links(package_id)""",
    """CREATE INDEX IF NOT EXISTS idx_dpwl_wp
       ON document_package_wp_links(work_package_code)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)