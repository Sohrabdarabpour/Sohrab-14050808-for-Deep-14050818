from datetime import datetime
import jdatetime
from database.connection import get_connection


class DepartmentService:

    # ============================================================
    # HELPERS — تبدیل و نرمال‌سازی سال و ماه
    # ============================================================

    @staticmethod
    def _to_jalali_year(value):
        """تبدیل تاریخ (میلادی، شمسی، Excel serial) به سال شمسی"""
        if value is None:
            return None

        if isinstance(value, datetime):
            return jdatetime.datetime.fromgregorian(datetime=value).year

        value = str(value).strip()
        if not value:
            return None

        # ★ پشتیبانی از Excel serial
        try:
            numeric_value = float(value)
            if numeric_value.is_integer():
                from datetime import date, timedelta
                excel_base = date(1899, 12, 30)
                gregorian = excel_base + timedelta(days=int(numeric_value))
                return jdatetime.date.fromgregorian(date=gregorian).year
        except (ValueError, TypeError):
            pass

        value = value.replace("-", "/")
        try:
            parts = value.split("/")
            if len(parts) >= 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2].split(" ")[0])

                if year < 1700:
                    return year

                return jdatetime.date.fromgregorian(
                    year=year,
                    month=month,
                    day=day
                ).year
        except (ValueError, TypeError):
            return None

        return None

    @staticmethod
    def _to_jalali_month(value):
        """تبدیل تاریخ (میلادی، شمسی، Excel serial) به ماه شمسی (1-12)"""
        if value is None:
            return None

        if isinstance(value, datetime):
            return jdatetime.datetime.fromgregorian(datetime=value).month

        value = str(value).strip()
        if not value:
            return None

        # ★ پشتیبانی از Excel serial
        try:
            numeric_value = float(value)
            if numeric_value.is_integer():
                from datetime import date, timedelta
                excel_base = date(1899, 12, 30)
                gregorian = excel_base + timedelta(days=int(numeric_value))
                return jdatetime.date.fromgregorian(date=gregorian).month
        except (ValueError, TypeError):
            pass

        value = value.replace("-", "/")
        try:
            parts = value.split("/")
            if len(parts) >= 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2].split(" ")[0])

                if year < 1700:
                    return month

                return jdatetime.date.fromgregorian(
                    year=year,
                    month=month,
                    day=day
                ).month
        except (ValueError, TypeError):
            return None

        return None

    @staticmethod
    def get_year_range(year):
        """تبدیل سال شمسی به بازه میلادی [start, end)"""
        if year == "all" or year is None:
            return None

        try:
            year = int(year)
        except (ValueError, TypeError):
            return None

        start_gregorian = jdatetime.date(year, 1, 1).togregorian()
        end_gregorian = jdatetime.date(year + 1, 1, 1).togregorian()

        return (
            start_gregorian.strftime("%Y/%m/%d"),
            end_gregorian.strftime("%Y/%m/%d")
        )

    @staticmethod
    def get_month_range(year, month):
        """
        تبدیل سال و ماه شمسی به بازه میلادی [start, end)
        """
        if year == "all" or year is None:
            return None
        if month == "all" or month is None:
            return None

        try:
            year = int(year)
            month = int(month)
        except (ValueError, TypeError):
            return None

        if month < 1 or month > 12:
            return None

        start_jalali = jdatetime.date(year, month, 1)

        if month == 12:
            next_month_jalali = jdatetime.date(year + 1, 1, 1)
        else:
            next_month_jalali = jdatetime.date(year, month + 1, 1)

        start_gregorian = start_jalali.togregorian()
        end_gregorian = next_month_jalali.togregorian()

        return (
            start_gregorian.strftime("%Y/%m/%d"),
            end_gregorian.strftime("%Y/%m/%d")
        )

    @staticmethod
    def get_date_ranges(selected_year, selected_month, available_years=None):
        """
        ★ محاسبه لیست بازه‌های میلادی بر اساس سال و ماه
        """
        year_all = selected_year in (None, "", "all")
        month_all = selected_month in (None, "", "all")

        if year_all and month_all:
            return None

        if not year_all and month_all:
            year_range = DepartmentService.get_year_range(selected_year)
            return [year_range] if year_range else None

        if not year_all and not month_all:
            month_range = DepartmentService.get_month_range(
                selected_year, selected_month
            )
            return [month_range] if month_range else None

        if year_all and not month_all:
            try:
                month = int(selected_month)
            except (ValueError, TypeError):
                return None

            if month < 1 or month > 12:
                return None

            if not available_years:
                return None

            ranges = []
            for y in available_years:
                month_range = DepartmentService.get_month_range(y, month)
                if month_range:
                    ranges.append(month_range)

            return ranges if ranges else None

        return None

    @staticmethod
    def get_available_years(department_id):
        """★ لیست سال‌های شمسی که این دپارتمان سند داره"""
        connection = get_connection()
        try:
            rows = connection.execute("""
                SELECT DISTINCT date_received
                FROM documents
                WHERE department_id = ?
                  AND date_received IS NOT NULL
                  AND date_received != ''
            """, (department_id,)).fetchall()

            years = set()
            for row in rows:
                year = DepartmentService._to_jalali_year(row["date_received"])
                if year:
                    years.add(year)

            return sorted(years, reverse=True)

        finally:
            connection.close()

    @staticmethod
    def get_available_months(department_id, year=None):
        """★ لیست ماه‌های شمسی موجود"""
        connection = get_connection()
        try:
            if year and year != "all":
                year_range = DepartmentService.get_year_range(year)
                if year_range:
                    rows = connection.execute("""
                        SELECT DISTINCT date_received
                        FROM documents
                        WHERE department_id = ?
                          AND date_received IS NOT NULL
                          AND date_received != ''
                          AND date_received >= ?
                          AND date_received < ?
                    """, (department_id, year_range[0], year_range[1])).fetchall()
                else:
                    rows = []
            else:
                rows = connection.execute("""
                    SELECT DISTINCT date_received
                    FROM documents
                    WHERE department_id = ?
                      AND date_received IS NOT NULL
                      AND date_received != ''
                """, (department_id,)).fetchall()

            months = set()
            for row in rows:
                month = DepartmentService._to_jalali_month(row["date_received"])
                if month:
                    months.add(month)

            return sorted(months)

        finally:
            connection.close()

    @staticmethod
    def normalize_year(department_id, requested_year):
        """سال درخواستی رو اعتبارسنجی می‌کنه"""
        available_years = DepartmentService.get_available_years(department_id)

        if requested_year in (None, "", "all"):
            return "all", available_years

        try:
            selected_year = int(requested_year)
        except (ValueError, TypeError):
            return "all", available_years

        if selected_year not in available_years:
            return "all", available_years

        return selected_year, available_years

    @staticmethod
    def normalize_month(department_id, requested_month, selected_year=None):
        """ماه درخواستی رو اعتبارسنجی می‌کنه (با توجه به سال)"""
        available_months = DepartmentService.get_available_months(
            department_id,
            year=selected_year
        )

        if requested_month in (None, "", "all"):
            return "all", available_months

        try:
            selected_month = int(requested_month)
        except (ValueError, TypeError):
            return "all", available_months

        if selected_month not in available_months:
            return "all", available_months

        return selected_month, available_months

    # ============================================================
    # GET ALL DEPARTMENTS
    # ============================================================

    @staticmethod
    def get_all():
        connection = get_connection()
        try:
            departments = connection.execute("""
                SELECT
                    d.id,
                    d.title,
                    d.code,
                    d.sort_order,
                    d.is_active,
                    d.supervisor_id,
                    u.full_name AS supervisor_name,

                    (
                        SELECT COUNT(*)
                        FROM users members
                        WHERE members.department_id = d.id
                        AND members.is_active = 1
                    ) AS experts_count,

                    (
                        SELECT COUNT(*)
                        FROM documents docs
                        WHERE docs.department_id = d.id
                    ) AS documents_count,

                    (
                        SELECT COUNT(DISTINCT docs.user_id)
                        FROM documents docs
                        WHERE docs.department_id = d.id
                        AND docs.user_id IS NOT NULL
                    ) AS active_experts_count

                FROM departments d

                LEFT JOIN users u
                    ON u.id = d.supervisor_id

                ORDER BY
                    d.sort_order ASC,
                    d.id ASC
            """).fetchall()

            return [dict(department) for department in departments]

        finally:
            connection.close()

    # ============================================================
    # GET DEPARTMENT BY ID
    # ============================================================

    @staticmethod
    def get_by_id(department_id, date_ranges=None):
        connection = get_connection()
        try:
            if date_ranges:
                or_clauses = " OR ".join([
                    "(docs.date_received >= ? AND docs.date_received < ?)"
                    for _ in date_ranges
                ])
                docs_date_clause = f"AND ({or_clauses})"
                date_params = []
                for r in date_ranges:
                    date_params.extend([r[0], r[1]])
            else:
                docs_date_clause = ""
                date_params = []

            department = connection.execute(f"""
                SELECT
                    d.id,
                    d.title,
                    d.code,
                    d.sort_order,
                    d.is_active,
                    d.supervisor_id,
                    u.full_name AS supervisor_name,

                    (
                        SELECT COUNT(*)
                        FROM users members
                        WHERE members.department_id = d.id
                        AND members.is_active = 1
                    ) AS experts_count,

                    (
                        SELECT COUNT(*)
                        FROM documents docs
                        WHERE docs.department_id = d.id
                        {docs_date_clause}
                    ) AS documents_count,

                    (
                        SELECT COUNT(DISTINCT docs.user_id)
                        FROM documents docs
                        WHERE docs.department_id = d.id
                        AND docs.user_id IS NOT NULL
                        {docs_date_clause}
                    ) AS active_experts_count

                FROM departments d

                LEFT JOIN users u
                    ON u.id = d.supervisor_id

                WHERE d.id = ?
            """, date_params + date_params + [department_id]).fetchone()

            return dict(department) if department else None

        finally:
            connection.close()

    # ============================================================
    # GET SUPERVISORS
    # ============================================================

    @staticmethod
    def get_supervisors():
        connection = get_connection()
        try:
            supervisors = connection.execute("""
                SELECT
                    id,
                    full_name,
                    username,
                    role
                FROM users
                WHERE role IN ('admin', 'manager', 'supervisor')
                AND is_active = 1
                ORDER BY
                    CASE role
                        WHEN 'admin' THEN 1
                        WHEN 'manager' THEN 2
                        WHEN 'supervisor' THEN 3
                    END,
                    full_name COLLATE NOCASE ASC
            """).fetchall()

            return [dict(supervisor) for supervisor in supervisors]

        finally:
            connection.close()

    # ============================================================
    # CREATE DEPARTMENT
    # ============================================================

    @staticmethod
    def create(
        title,
        code,
        sort_order=0,
        supervisor_id=None,
        is_active=1
    ):
        connection = get_connection()

        try:
            if supervisor_id:
                supervisor = connection.execute("""
                    SELECT id
                    FROM users
                    WHERE id = ?
                    AND role IN ('admin', 'manager', 'supervisor')
                    AND is_active = 1
                """, (supervisor_id,)).fetchone()

                if not supervisor:
                    return False, "سرپرست انتخاب‌شده معتبر نیست"

            connection.execute("""
                INSERT INTO departments
                (title, code, sort_order, supervisor_id, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (
                title.strip(),
                code.strip() if code else None,
                sort_order,
                supervisor_id if supervisor_id else None,
                is_active
            ))

            connection.commit()
            return True, "دپارتمان با موفقیت ایجاد شد"

        except Exception as error:
            connection.rollback()

            if "UNIQUE constraint failed" in str(error):
                return False, "عنوان یا کد دپارتمان تکراری است"

            return False, "ایجاد دپارتمان انجام نشد"

        finally:
            connection.close()

    # ============================================================
    # UPDATE DEPARTMENT
    # ============================================================

    @staticmethod
    def update(
        department_id,
        title,
        code,
        sort_order=0,
        supervisor_id=None,
        is_active=1
    ):
        connection = get_connection()

        try:
            if supervisor_id:
                supervisor = connection.execute("""
                    SELECT id
                    FROM users
                    WHERE id = ?
                    AND role IN ('admin', 'manager', 'supervisor')
                    AND is_active = 1
                """, (supervisor_id,)).fetchone()

                if not supervisor:
                    return False, "سرپرست انتخاب‌شده معتبر نیست"

            department = connection.execute("""
                SELECT id FROM departments WHERE id = ?
            """, (department_id,)).fetchone()

            if not department:
                return False, "دپارتمان پیدا نشد"

            connection.execute("""
                UPDATE departments
                SET
                    title = ?,
                    code = ?,
                    sort_order = ?,
                    supervisor_id = ?,
                    is_active = ?
                WHERE id = ?
            """, (
                title.strip(),
                code.strip() if code else None,
                sort_order,
                supervisor_id if supervisor_id else None,
                is_active,
                department_id
            ))

            connection.commit()
            return True, "دپارتمان با موفقیت ویرایش شد"

        except Exception as error:
            connection.rollback()

            if "UNIQUE constraint failed" in str(error):
                return False, "عنوان یا کد دپارتمان تکراری است"

            return False, "ویرایش دپارتمان انجام نشد"

        finally:
            connection.close()

    # ============================================================
    # DELETE DEPARTMENT
    # ============================================================

    @staticmethod
    def delete(department_id):
        connection = get_connection()

        try:
            department = connection.execute("""
                SELECT id FROM departments WHERE id = ?
            """, (department_id,)).fetchone()

            if not department:
                return False, "دپارتمان پیدا نشد"

            users_count = connection.execute("""
                SELECT COUNT(*) AS count
                FROM users
                WHERE department_id = ?
            """, (department_id,)).fetchone()["count"]

            documents_count = connection.execute("""
                SELECT COUNT(*) AS count
                FROM documents
                WHERE department_id = ?
            """, (department_id,)).fetchone()["count"]

            if users_count > 0 or documents_count > 0:
                return False, "دپارتمان دارای کاربر یا سند است و قابل حذف نیست"

            connection.execute("""
                DELETE FROM departments WHERE id = ?
            """, (department_id,))

            connection.commit()
            return True, "دپارتمان حذف شد"

        except Exception:
            connection.rollback()
            return False, "حذف دپارتمان انجام نشد"

        finally:
            connection.close()

    # ============================================================
    # GET DEPARTMENT EXPERTS (با آمار وضعیت اسناد)
    # ============================================================

    @staticmethod
    def get_department_experts(department_id, date_ranges=None):
        connection = get_connection()

        try:
            if date_ranges:
                or_clauses = " OR ".join([
                    "(d.date_received >= ? AND d.date_received < ?)"
                    for _ in date_ranges
                ])
                year_clause = f"AND ({or_clauses})"
                date_params = []
                for r in date_ranges:
                    date_params.extend([r[0], r[1]])
            else:
                year_clause = ""
                date_params = []

            # --------------------------------------------------
            # ۱) لیست کاربران دپارتمان + تعداد اسناد
            # --------------------------------------------------
            members = connection.execute(f"""
                SELECT
                    u.id,
                    u.full_name,
                    u.username,
                    u.avatar,
                    u.gender,
                    u.role,
                    u.is_active,
                    (
                        SELECT COUNT(*)
                        FROM documents d
                        WHERE d.user_id = u.id
                          AND d.department_id = u.department_id
                          {year_clause}
                    ) AS documents_count
                FROM users u
                WHERE u.department_id = ?
                ORDER BY u.full_name COLLATE NOCASE ASC
            """, date_params + [department_id]).fetchall()

            if not members:
                return []

            member_ids = [row["id"] for row in members]
            placeholders = ",".join("?" * len(member_ids))

            # --------------------------------------------------
            # ۲) آمار وضعیت‌ها
            # --------------------------------------------------
            status_rows = connection.execute(f"""
                SELECT
                    d.user_id,
                    s.id    AS status_id,
                    s.title AS status_title,
                    s.code  AS status_code,
                    s.color AS status_color,
                    COUNT(d.id) AS count
                FROM documents d
                INNER JOIN document_statuses s
                    ON d.status_id = s.id
                WHERE d.department_id = ?
                  AND d.user_id IN ({placeholders})
                  {year_clause}
                GROUP BY
                    d.user_id,
                    s.id,
                    s.title,
                    s.code,
                    s.color
                ORDER BY s.id ASC
            """, [department_id] + member_ids + date_params).fetchall()

            # --------------------------------------------------
            # ۳) گروه‌بندی آمار وضعیت‌ها
            # --------------------------------------------------
            status_by_user = {}
            for row in status_rows:
                uid = row["user_id"]
                status_by_user.setdefault(uid, []).append({
                    "id":    row["status_id"],
                    "title": row["status_title"],
                    "code":  row["status_code"],
                    "color": row["status_color"],
                    "count": int(row["count"] or 0)
                })

            # --------------------------------------------------
            # ۴) لیست همه وضعیت‌ها
            # --------------------------------------------------
            all_statuses = connection.execute("""
                SELECT id, title, code, color
                FROM document_statuses
                ORDER BY id ASC
            """).fetchall()

            all_statuses_list = [dict(s) for s in all_statuses]

            # --------------------------------------------------
            # ۵) ساخت خروجی نهایی
            # --------------------------------------------------
            result = []
            for member in members:
                member_dict = dict(member)
                counts_map = {
                    s["code"]: s["count"]
                    for s in status_by_user.get(member["id"], [])
                }

                member_dict["status_counts"] = [
                    {
                        "id":    st["id"],
                        "title": st["title"],
                        "code":  st["code"],
                        "color": st["color"],
                        "count": counts_map.get(st["code"], 0)
                    }
                    for st in all_statuses_list
                ]

                member_dict["status_counts_nonzero"] = [
                    s for s in member_dict["status_counts"] if s["count"] > 0
                ]

                result.append(member_dict)

            return result

        finally:
            connection.close()

    # ============================================================
    # ★ EXPERT BREAKDOWN — تفکیک کارهای در دست بررسی کارشناس
    # ============================================================

    @staticmethod
    def get_expert_breakdown(expert_id, department_id, date_ranges=None):
        """
        ★ دریافت تفکیک کارهای «در دست بررسی» کارشناس

        ★ موقتاً از ساختار TEXT استفاده می‌کند
        ★ بعداً می‌توان به ساختار شناسه‌ای سوییچ کرد
        """
        connection = get_connection()

        try:
            # ۰) بررسی ساختار دیتابیس
            all_tables = [
                row["name"] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]

            doc_columns = [
                row["name"] for row in connection.execute(
                    "PRAGMA table_info(documents)"
                ).fetchall()
            ]

            has_groups_table = "document_groups" in all_tables
            has_subgroups_table = "document_subgroups" in all_tables

            has_group_col = "group_id" in doc_columns
            has_subgroup_col = "subgroup_id" in doc_columns

            has_group_text = "document_group" in doc_columns
            has_subgroup_text = "sub_group" in doc_columns

            # ۱) بازه تاریخ
            if date_ranges:
                or_clauses = " OR ".join([
                    "(d.date_received >= ? AND d.date_received < ?)"
                    for _ in date_ranges
                ])
                date_clause = f"AND ({or_clauses})"
                date_params = []
                for r in date_ranges:
                    date_params.extend([r[0], r[1]])
            else:
                date_clause = ""
                date_params = []

            # ۲) جمع کل (فقط کارهای در دست بررسی)
            total_row = connection.execute(f"""
                SELECT COUNT(*) AS count
                FROM documents d
                INNER JOIN document_statuses s
                    ON d.status_id = s.id
                WHERE d.user_id = ?
                AND d.department_id = ?
                AND s.code = 'in_progress'
                {date_clause}
            """, [expert_id, department_id] + date_params).fetchone()

            total_count = int(total_row["count"] or 0)

            # ============================================================
            # ★★★ موقتاً: همیشه از ساختار TEXT استفاده کن ★★★
            # ============================================================
            # if has_groups_table and has_group_col:
            #     return DepartmentService._get_breakdown_new_structure(
            #         connection=connection,
            #         expert_id=expert_id,
            #         department_id=department_id,
            #         date_clause=date_clause,
            #         date_params=date_params,
            #         total_count=total_count,
            #         has_subgroups_table=has_subgroups_table,
            #         has_subgroup_col=has_subgroup_col,
            #     )

            # ۴) ساختار TEXT
            return DepartmentService._get_breakdown_text_structure(
                connection=connection,
                expert_id=expert_id,
                department_id=department_id,
                date_clause=date_clause,
                date_params=date_params,
                total_count=total_count,
                has_group_text=has_group_text,
                has_subgroup_text=has_subgroup_text,
            )

        finally:
            connection.close()
        # ============================================================
        # ★ BREAKDOWN — ساختار جدید (با جدول)
        # ============================================================

    @staticmethod
    # def _get_breakdown_new_structure(
    #     connection, expert_id, department_id,
    #     date_clause, date_params, total_count,
    #     has_subgroups_table, has_subgroup_col,
    # ):
    #     """
    #     ★ ساختار جدید: با جدول document_groups و document_subgroups
    #     + جدول واسط subgroup_departments
    #     """

    #     # ۱) لیست گروه‌ها (فقط فعال‌ها)
    #     groups = connection.execute("""
    #         SELECT id, title, code, color
    #         FROM document_groups
    #         WHERE is_active = 1
    #         ORDER BY sort_order ASC, id ASC
    #     """).fetchall()
    #     groups_list = [dict(g) for g in groups]

    #     # ۲) لیست زیرگروه‌ها (فقط فعال‌ها) + گروه مربوطه
    #     subgroups_list = []
    #     if has_subgroups_table:
    #         try:
    #             subgroups = connection.execute("""
    #                 SELECT
    #                     sg.id,
    #                     sg.group_id,
    #                     sg.title,
    #                     sg.code,
    #                     sg.color,
    #                     sg.days_review
    #                 FROM document_subgroups sg
    #                 WHERE sg.is_active = 1
    #                 ORDER BY sg.sort_order ASC, sg.id ASC
    #             """).fetchall()
    #             subgroups_list = [dict(s) for s in subgroups]
    #         except Exception:
    #             subgroups_list = []

    #     # ۳) شمارش گروه‌ها (فقط کارهای در دست بررسی)
    #     group_counts_rows = connection.execute(f"""
    #         SELECT d.group_id AS gid, COUNT(d.id) AS count
    #         FROM documents d
    #         INNER JOIN document_statuses s
    #             ON d.status_id = s.id
    #         WHERE d.user_id = ?
    #           AND d.department_id = ?
    #           AND s.code = 'in_progress'
    #           {date_clause}
    #         GROUP BY d.group_id
    #     """, [expert_id, department_id] + date_params).fetchall()

    #     group_counts = {
    #         row["gid"]: int(row["count"] or 0)
    #         for row in group_counts_rows
    #     }

    #     # ۴) شمارش زیرگروه‌ها (فقط کارهای در دست بررسی)
    #     subgroup_counts = {}
    #     if has_subgroup_col:
    #         subgroup_counts_rows = connection.execute(f"""
    #             SELECT d.subgroup_id AS sgid, COUNT(d.id) AS count
    #             FROM documents d
    #             INNER JOIN document_statuses s
    #                 ON d.status_id = s.id
    #             WHERE d.user_id = ?
    #               AND d.department_id = ?
    #               AND s.code = 'in_progress'
    #               {date_clause}
    #             GROUP BY d.subgroup_id
    #         """, [expert_id, department_id] + date_params).fetchall()

    #         subgroup_counts = {
    #             row["sgid"]: int(row["count"] or 0)
    #             for row in subgroup_counts_rows
    #         }

    #     # ۵) ساخت خروجی
    #     result_groups = []
    #     for group in groups_list:
    #         g_id = group["id"]
    #         g_subs = [
    #             {
    #                 "id": s["id"],
    #                 "title": s["title"],
    #                 "code": s.get("code"),
    #                 "color": s.get("color"),
    #                 "days_review": s.get("days_review", 0),
    #                 "count": subgroup_counts.get(s["id"], 0)
    #             }
    #             for s in subgroups_list
    #             if s["group_id"] == g_id
    #         ]

    #         # ★ فقط زیرگروه‌هایی که در این گروه هستند
    #         result_groups.append({
    #             "id": g_id,
    #             "title": group["title"],
    #             "code": group.get("code"),
    #             "color": group.get("color"),
    #             "count": group_counts.get(g_id, 0),
    #             "subgroups": g_subs
    #         })

    #     ungrouped_count = group_counts.get(None, 0)

    #     return {
    #         "total": total_count,
    #         "groups": result_groups,
    #         "ungrouped": {
    #             "title": "بدون گروه",
    #             "count": ungrouped_count
    #         }
    #     }

    # ============================================================
    # ★ BREAKDOWN — ساختار TEXT (قدیمی)
    # ============================================================

    @staticmethod
    # def _get_breakdown_text_structure(
    #     connection, expert_id, department_id,
    #     date_clause, date_params, total_count,
    #     has_group_text, has_subgroup_text,
    # ):
    #     """★ ساختار فعلی: با document_group و sub_group (TEXT)"""

    #     if not has_group_text:
    #         return {
    #             "total": total_count,
    #             "groups": [],
    #             "ungrouped": {
    #                 "title": "بدون گروه",
    #                 "count": total_count
    #             }
    #         }

    #     # ۱) لیست گروه‌های موجود (فقط کارهای در دست بررسی)
    #     group_rows = connection.execute(f"""
    #         SELECT
    #             d.document_group AS group_title,
    #             COUNT(d.id) AS count
    #         FROM documents d
    #         INNER JOIN document_statuses s
    #             ON d.status_id = s.id
    #         WHERE d.user_id = ?
    #           AND d.department_id = ?
    #           AND s.code = 'in_progress'
    #           AND d.document_group IS NOT NULL
    #           AND d.document_group != ''
    #           {date_clause}
    #         GROUP BY d.document_group
    #         ORDER BY count DESC
    #     """, [expert_id, department_id] + date_params).fetchall()

    #     # ۲) لیست زیرگروه‌های موجود (فقط کارهای در دست بررسی)
    #     subgroup_map = {}
    #     if has_subgroup_text:
    #         subgroup_rows = connection.execute(f"""
    #             SELECT
    #                 d.document_group AS group_title,
    #                 d.sub_group AS subgroup_title,
    #                 COUNT(d.id) AS count
    #             FROM documents d
    #             INNER JOIN document_statuses s
    #                 ON d.status_id = s.id
    #             WHERE d.user_id = ?
    #               AND d.department_id = ?
    #               AND s.code = 'in_progress'
    #               AND d.document_group IS NOT NULL
    #               AND d.document_group != ''
    #               AND d.sub_group IS NOT NULL
    #               AND d.sub_group != ''
    #               {date_clause}
    #             GROUP BY d.document_group, d.sub_group
    #             ORDER BY count DESC
    #         """, [expert_id, department_id] + date_params).fetchall()

    #         for row in subgroup_rows:
    #             g = row["group_title"]
    #             subgroup_map.setdefault(g, []).append({
    #                 "id": row["subgroup_title"],
    #                 "title": row["subgroup_title"],
    #                 "count": int(row["count"] or 0)
    #             })

    #     # ۳) شمارش اسناد بدون گروه (فقط کارهای در دست بررسی)
    #     ungrouped_row = connection.execute(f"""
    #         SELECT COUNT(*) AS count
    #         FROM documents d
    #         INNER JOIN document_statuses s
    #             ON d.status_id = s.id
    #         WHERE d.user_id = ?
    #           AND d.department_id = ?
    #           AND s.code = 'in_progress'
    #           AND (d.document_group IS NULL OR d.document_group = '')
    #           {date_clause}
    #     """, [expert_id, department_id] + date_params).fetchone()

    #     ungrouped_count = int(ungrouped_row["count"] or 0)

    #     # ۴) ساخت خروجی گروه‌ها
    #     result_groups = []
    #     for idx, row in enumerate(group_rows):
    #         g_title = row["group_title"]
    #         result_groups.append({
    #             "id": idx + 1,
    #             "title": g_title,
    #             "count": int(row["count"] or 0),
    #             "subgroups": subgroup_map.get(g_title, [])
    #         })

    #     return {
    #         "total": total_count,
    #         "groups": result_groups,
    #         "ungrouped": {
    #             "title": "بدون گروه",
    #             "count": ungrouped_count
    #         }
    #     }



    # ============================================================
    # ★ EXPERT BREAKDOWN — تفکیک کارهای در دست بررسی کارشناس
    # ============================================================
    @staticmethod
    def get_expert_breakdown(expert_id, department_id, date_ranges=None):
        """
        ★ دریافت تفکیک کارهای «در دست بررسی» کارشناس
        ★ بر اساس شناسه گروه (group_id) و شناسه زیرگروه (subgroup_id)
        """
        connection = get_connection()

        try:
            # ---- بازه تاریخ ----
            if date_ranges:
                or_clauses = " OR ".join([
                    "(d.date_received >= ? AND d.date_received < ?)"
                    for _ in date_ranges
                ])
                date_clause = f"AND ({or_clauses})"
                date_params = []
                for r in date_ranges:
                    date_params.extend([r[0], r[1]])
            else:
                date_clause = ""
                date_params = []

            # ---- ۱) جمع کل (فقط کارهای در دست بررسی) ----
            total_row = connection.execute(f"""
                SELECT COUNT(*) AS count
                FROM documents d
                INNER JOIN document_statuses s
                    ON d.status_id = s.id
                WHERE d.user_id = ?
                  AND d.department_id = ?
                  AND s.code = 'in_progress'
                  {date_clause}
            """, [expert_id, department_id] + date_params).fetchone()

            total_count = int(total_row["count"] or 0)

            # ---- ۲) لیست همه گروه‌های فعال ----
            groups = connection.execute("""
                SELECT id, title, code, color, sort_order
                FROM document_groups
                WHERE is_active = 1
                ORDER BY sort_order ASC, id ASC
            """).fetchall()
            groups_list = [dict(g) for g in groups]

            # ---- ۳) شمارش اسناد بر اساس group_id ----
            group_counts_rows = connection.execute(f"""
                SELECT d.group_id AS gid, COUNT(d.id) AS count
                FROM documents d
                INNER JOIN document_statuses s
                    ON d.status_id = s.id
                WHERE d.user_id = ?
                  AND d.department_id = ?
                  AND s.code = 'in_progress'
                  AND d.group_id IS NOT NULL
                  {date_clause}
                GROUP BY d.group_id
            """, [expert_id, department_id] + date_params).fetchall()

            group_counts = {
                row["gid"]: int(row["count"] or 0)
                for row in group_counts_rows
            }

            # ---- ۴) شمارش اسناد بر اساس subgroup_id ----
            subgroup_counts_rows = connection.execute(f"""
                SELECT d.subgroup_id AS sgid, COUNT(d.id) AS count
                FROM documents d
                INNER JOIN document_statuses s
                    ON d.status_id = s.id
                WHERE d.user_id = ?
                  AND d.department_id = ?
                  AND s.code = 'in_progress'
                  AND d.subgroup_id IS NOT NULL
                  {date_clause}
                GROUP BY d.subgroup_id
            """, [expert_id, department_id] + date_params).fetchall()

            subgroup_counts = {
                row["sgid"]: int(row["count"] or 0)
                for row in subgroup_counts_rows
            }

            # ---- ۵) لیست همه زیرگروه‌های فعال ----
            subgroups_rows = connection.execute("""
                SELECT
                    sg.id,
                    sg.title,
                    sg.code,
                    sg.color,
                    sg.days_review,
                    sg.sort_order,
                    gs.group_id AS group_id
                FROM document_subgroups sg
                INNER JOIN group_subgroups gs
                    ON gs.subgroup_id = sg.id
                   AND gs.is_active = 1
                WHERE sg.is_active = 1
                ORDER BY sg.sort_order ASC, sg.id ASC
            """).fetchall()

            # ---- ۶) گروه‌بندی زیرگروه‌ها بر اساس group_id ----
            subgroups_by_group = {}
            for sg in subgroups_rows:
                g_id = sg["group_id"]
                subgroups_by_group.setdefault(g_id, []).append({
                    "id": sg["id"],
                    "title": sg["title"],
                    "code": sg["code"],
                    "color": sg["color"],
                    "days_review": sg["days_review"] or 0,
                    "count": subgroup_counts.get(sg["id"], 0),
                })

            # ---- ۷) ساخت خروجی نهایی ----
            result_groups = []
            for g in groups_list:
                g_id = g["id"]
                result_groups.append({
                    "id": g_id,
                    "title": g["title"],
                    "code": g["code"],
                    "color": g["color"],
                    "count": group_counts.get(g_id, 0),
                    "subgroups": subgroups_by_group.get(g_id, []),
                })

            # ---- ۸) شمارش اسناد بدون گروه ----
            ungrouped_row = connection.execute(f"""
                SELECT COUNT(*) AS count
                FROM documents d
                INNER JOIN document_statuses s
                    ON d.status_id = s.id
                WHERE d.user_id = ?
                  AND d.department_id = ?
                  AND s.code = 'in_progress'
                  AND (d.group_id IS NULL)
                  {date_clause}
            """, [expert_id, department_id] + date_params).fetchone()

            ungrouped_count = int(ungrouped_row["count"] or 0)

            return {
                "total": total_count,
                "groups": result_groups,
                "ungrouped": {
                    "title": "بدون گروه",
                    "count": ungrouped_count,
                },
            }

        finally:
            connection.close()