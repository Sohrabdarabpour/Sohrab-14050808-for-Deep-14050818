"""جدول projects — پروژه‌ها

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "projects"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE,
            project_number TEXT,
            description TEXT,
            contractor_id INTEGER,
            contract_type_id INTEGER,
            area_id INTEGER,
            created_by INTEGER,
            contract_number TEXT,
            contract_amount REAL,
            contract_number_foreign TEXT,
            contract_amount_foreign REAL,
            currency TEXT DEFAULT 'USD',
            contract_start_date TEXT,
            contract_end_date TEXT,
            start_date TEXT,
            planned_end_date TEXT,
            actual_end_date TEXT,
            duration_days INTEGER,
            status TEXT DEFAULT 'active',
            priority TEXT DEFAULT 'medium',
            progress_percent INTEGER DEFAULT 0,
            physical_progress INTEGER DEFAULT 0,
            time_progress INTEGER DEFAULT 0,
            financial_progress INTEGER DEFAULT 0,
            financial_progress_rial INTEGER DEFAULT 0,
            financial_progress_foreign INTEGER DEFAULT 0,
            budget REAL,
            total_paid REAL DEFAULT 0,
            total_amendments_amount REAL DEFAULT 0,
            location TEXT,
            province TEXT,
            city TEXT,
            latitude REAL,
            longitude REAL,
            tags TEXT,
            notes TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contractor_id) REFERENCES contractors(id)
                ON DELETE SET NULL,
            FOREIGN KEY (contract_type_id) REFERENCES contract_types(id)
                ON DELETE SET NULL,
            FOREIGN KEY (area_id) REFERENCES areas(id)
                ON DELETE SET NULL,
            FOREIGN KEY (created_by) REFERENCES users(id)
                ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_projects_name
        ON projects(name)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_projects_code
        ON projects(code)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_projects_contractor
        ON projects(contractor_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_projects_contract_type
        ON projects(contract_type_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_projects_area
        ON projects(area_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_projects_status
        ON projects(status)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_projects_is_active
        ON projects(is_active)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
