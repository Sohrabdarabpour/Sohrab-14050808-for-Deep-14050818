"""جدول document_references — نامه‌ها، رفرنس‌ها و ارتباطات سند."""

TABLE_NAME = "document_references"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            assignment_id INTEGER,

            ref_type TEXT NOT NULL,
            direction TEXT NOT NULL DEFAULT 'in',
            is_official INTEGER DEFAULT 1,
            channel TEXT,

            ref_no TEXT,
            ref_date TEXT,

            party_type TEXT,
            contractor_id INTEGER,
            department_id INTEGER,
            person_name TEXT,

            subject TEXT,
            summary TEXT,
            outcome TEXT,

            response_to_id INTEGER,

            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (response_to_id) REFERENCES document_references(id) ON DELETE SET NULL,
            FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_refs_doc
       ON document_references(document_id)""",
    """CREATE INDEX IF NOT EXISTS idx_refs_type
       ON document_references(ref_type)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)