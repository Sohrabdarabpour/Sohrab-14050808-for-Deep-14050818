"""جدول اصلی پکیج سند (مستقل از documents).

هر سند یک DFC_CODE یکتا دارد.
همه‌ی اسناد یک موضوع، یک WORK_PACKAGE_CODE مشترک دارند.
"""

TABLE_NAME = "document_packages"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- ★ کدها
            dfc_code TEXT UNIQUE NOT NULL,
            work_package_code TEXT NOT NULL,
            package_year INTEGER NOT NULL,
            dfc_sequence INTEGER,

            -- ★ اطلاعات سند
            subject TEXT NOT NULL,
            description TEXT,
            date_letter TEXT,
            date_received TEXT,
            sender_ref_no TEXT,
            sender_ref_date TEXT,
            contract_number TEXT,
            sender_name TEXT,
            sender_type TEXT DEFAULT 'other',
            source_type TEXT DEFAULT 'other',
            direction TEXT DEFAULT 'incoming',
            contractor_id INTEGER,
            project_id INTEGER,
            automation_number TEXT,

            -- ★ ارسال به مدیریت
            date_sent_to_management TEXT,
            date_returned_from_management TEXT,
            management_date_on_letter TEXT,
            management_instruction TEXT,
            management_instruction TEXT,
            management_action TEXT,

            -- ★ دستور مدیریت و ارجاع
            group_id INTEGER,
            subgroup_id INTEGER,
            priority TEXT DEFAULT 'normal',
            confidentiality TEXT DEFAULT 'internal',
            supervisor_ids TEXT,
            direct_expert_ids TEXT,

            -- ★ گردش کار
            stage TEXT NOT NULL DEFAULT 'registered',
            current_supervisor_id INTEGER,
            current_expert_id INTEGER,

            -- ★ SLA
            sla_days INTEGER,
            sla_source TEXT,
            sla_start_date TEXT,
            sla_effective_days INTEGER,
            response_due_date TEXT,
            is_overdue INTEGER DEFAULT 0,
            overdue_days INTEGER DEFAULT 0,

            -- ★ رفرنس
            reference_no TEXT,
            response_to_id INTEGER,
            parent_package_id INTEGER,
            work_package_subject TEXT,

            -- ★ نتیجه نهایی
            final_response TEXT,
            final_result TEXT,
            final_result_notes TEXT,
            response_letter_number TEXT,
            response_letter_date TEXT,
            date_sent_response TEXT,

            -- ★ تأییدات
            supervisor_approved_by INTEGER,
            supervisor_approved_at TEXT,
            management_approved_by INTEGER,
            management_approved_at TEXT,

            -- ★ متادیتا و آرشیو
            registered_by INTEGER,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_by INTEGER,
            closed_at TEXT,
            archived_by INTEGER,
            archived_at TEXT,
            archive_reason TEXT,
            reopen_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tags TEXT,
            notes TEXT,

            FOREIGN KEY (response_to_id) REFERENCES document_packages(id) ON DELETE SET NULL,
            FOREIGN KEY (parent_package_id) REFERENCES document_packages(id) ON DELETE SET NULL,
            FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE SET NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
            FOREIGN KEY (group_id) REFERENCES document_groups(id) ON DELETE SET NULL,
            FOREIGN KEY (subgroup_id) REFERENCES document_subgroups(id) ON DELETE SET NULL,
            FOREIGN KEY (registered_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (current_supervisor_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (current_expert_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (supervisor_approved_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (management_approved_by) REFERENCES users(id) ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_dp_dfc_code
       ON document_packages(dfc_code)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_work_package
       ON document_packages(work_package_code)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_year
       ON document_packages(package_year)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_stage
       ON document_packages(stage)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_contractor
       ON document_packages(contractor_id)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_project
       ON document_packages(project_id)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_contract_number
       ON document_packages(contract_number)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_sender_ref
       ON document_packages(sender_ref_no)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_automation
       ON document_packages(automation_number)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_reference
       ON document_packages(reference_no)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_due_date
       ON document_packages(response_due_date)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_overdue
       ON document_packages(is_overdue)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_registered_by
       ON document_packages(registered_by)""",
    """CREATE INDEX IF NOT EXISTS idx_dp_management_action
       ON document_packages(management_action)""",
    
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)