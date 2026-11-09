from database.connection import get_connection


class DocumentSubgroupService:
    """
    سرویس زیرگروه‌های سند با ساختار Many-to-Many

    ★ ویژگی‌ها:
    - هر زیرگروه می‌تونه در چند گروه باشه
    - هر زیرگروه می‌تونه چند دپارتمان متولی داشته باشه (بدون primary)
    - عنوان و کد زیرگروه در کل سیستم یکتاست
    - ترتیب نمایش در هر گروه مستقل قابل تنظیمه
    """

    # ============================================================
    # GET ALL — لیست زیرگروه‌ها
    # ============================================================
    @staticmethod
    def get_all(group_id=None, active_only=False, search=None,
                department_id=None, with_relations=True):
        """
        دریافت لیست زیرگروه‌ها

        پارامترها:
            group_id       : فیلتر بر اساس گروه (از طریق واسط)
            department_id  : فیلتر بر اساس دپارتمان (از طریق واسط)
            active_only    : فقط فعال‌ها
            search         : جستجو در title یا code
            with_relations : آیا گروه‌ها و دپارتمان‌ها لود بشن؟

        خروجی: لیست دیکشنری‌ها
        """
        connection = get_connection()
        try:
            query = """
                SELECT
                    sg.id,
                    sg.title,
                    sg.code,
                    sg.color,
                    sg.days_review,
                    sg.description,
                    sg.sort_order,
                    sg.is_active,
                    sg.created_at,
                    (
                        SELECT COUNT(*)
                        FROM documents d
                        WHERE d.subgroup_id = sg.id
                    ) AS documents_count,
                    (
                        SELECT COUNT(*)
                        FROM group_subgroups gs
                        WHERE gs.subgroup_id = sg.id
                    ) AS groups_count,
                    (
                        SELECT COUNT(*)
                        FROM subgroup_departments sd
                        WHERE sd.subgroup_id = sg.id
                    ) AS departments_count
                FROM document_subgroups sg
                WHERE 1=1
            """
            params = []

            # ★ فیلتر گروه
            if group_id:
                query += """
                    AND sg.id IN (
                        SELECT subgroup_id
                        FROM group_subgroups
                        WHERE group_id = ?
                    )
                """
                params.append(group_id)

            # ★ فیلتر دپارتمان
            if department_id:
                query += """
                    AND sg.id IN (
                        SELECT subgroup_id
                        FROM subgroup_departments
                        WHERE department_id = ?
                    )
                """
                params.append(department_id)

            if active_only:
                query += " AND sg.is_active = 1"

            if search:
                query += " AND (sg.title LIKE ? OR sg.code LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])

            query += " ORDER BY sg.sort_order ASC, sg.title ASC"

            rows = connection.execute(query, params).fetchall()
            subgroups = [dict(r) for r in rows]

            # ★ پر کردن روابط
            if with_relations:
                for sg in subgroups:
                    sg["groups"] = (
                        DocumentSubgroupService._get_groups_of_subgroup(
                            connection, sg["id"]
                        )
                    )
                    sg["departments"] = (
                        DocumentSubgroupService._get_departments_of_subgroup(
                            connection, sg["id"]
                        )
                    )
                    # ★ سازگاری با کدهای قدیمی
                    sg["group_id"] = (
                        sg["groups"][0]["id"] if sg["groups"] else None
                    )
                    sg["group_title"] = (
                        sg["groups"][0]["title"] if sg["groups"] else None
                    )
                    sg["department_id"] = (
                        sg["departments"][0]["id"]
                        if sg["departments"] else None
                    )
                    sg["department_title"] = (
                        sg["departments"][0]["title"]
                        if sg["departments"] else None
                    )

            return subgroups
        finally:
            connection.close()

    # ============================================================
    # GET BY ID
    # ============================================================
    @staticmethod
    def get_by_id(subgroup_id):
        """دریافت یک زیرگروه با تمام اطلاعات مرتبط"""
        connection = get_connection()
        try:
            row = connection.execute("""
                SELECT
                    sg.id,
                    sg.title,
                    sg.code,
                    sg.color,
                    sg.days_review,
                    sg.description,
                    sg.sort_order,
                    sg.is_active,
                    sg.created_at,
                    (
                        SELECT COUNT(*)
                        FROM documents d
                        WHERE d.subgroup_id = sg.id
                    ) AS documents_count
                FROM document_subgroups sg
                WHERE sg.id = ?
            """, (subgroup_id,)).fetchone()

            if not row:
                return None

            result = dict(row)

            # ★ گروه‌ها
            result["groups"] = DocumentSubgroupService._get_groups_of_subgroup(
                connection, subgroup_id
            )
            result["group_ids"] = [g["id"] for g in result["groups"]]

            # ★ دپارتمان‌ها
            result["departments"] = (
                DocumentSubgroupService._get_departments_of_subgroup(
                    connection, subgroup_id
                )
            )
            result["department_ids"] = [
                d["id"] for d in result["departments"]
            ]

            # ★ سازگاری با کدهای قدیمی
            result["group_id"] = (
                result["group_ids"][0] if result["group_ids"] else None
            )
            result["group_title"] = (
                result["groups"][0]["title"] if result["groups"] else None
            )
            result["department_id"] = (
                result["department_ids"][0]
                if result["department_ids"] else None
            )
            result["department_title"] = (
                result["departments"][0]["title"]
                if result["departments"] else None
            )

            return result
        finally:
            connection.close()

    # ============================================================
    # HELPER: گروه‌های یک زیرگروه
    # ============================================================
    @staticmethod
    def _get_groups_of_subgroup(connection, subgroup_id):
        """دریافت لیست گروه‌های یک زیرگروه"""
        rows = connection.execute("""
            SELECT
                g.id,
                g.title,
                g.code,
                g.color,
                gs.sort_order AS link_sort_order,
                gs.is_active AS link_is_active
            FROM document_groups g
            INNER JOIN group_subgroups gs ON gs.group_id = g.id
            WHERE gs.subgroup_id = ?
            ORDER BY gs.sort_order ASC, g.title ASC
        """, (subgroup_id,)).fetchall()
        return [dict(r) for r in rows]

    # ============================================================
    # HELPER: دپارتمان‌های یک زیرگروه
    # ============================================================
    @staticmethod
    def _get_departments_of_subgroup(connection, subgroup_id):
        """
        دریافت لیست دپارتمان‌های یک زیرگروه
        ★ بدون is_primary — همه یکسان
        """
        rows = connection.execute("""
            SELECT
                d.id,
                d.title,
                d.code
            FROM departments d
            INNER JOIN subgroup_departments sd ON sd.department_id = d.id
            WHERE sd.subgroup_id = ?
            ORDER BY d.title ASC
        """, (subgroup_id,)).fetchall()
        return [dict(r) for r in rows]

    # ============================================================
    # GET GROUPS OF SUBGROUP (public)
    # ============================================================
    @staticmethod
    def get_groups(subgroup_id):
        """دریافت لیست گروه‌های یک زیرگروه"""
        connection = get_connection()
        try:
            return DocumentSubgroupService._get_groups_of_subgroup(
                connection, subgroup_id
            )
        finally:
            connection.close()

    # ============================================================
    # GET DEPARTMENTS OF SUBGROUP (public)
    # ============================================================
    @staticmethod
    def get_departments(subgroup_id):
        """دریافت لیست دپارتمان‌های یک زیرگروه"""
        connection = get_connection()
        try:
            return DocumentSubgroupService._get_departments_of_subgroup(
                connection, subgroup_id
            )
        finally:
            connection.close()

    # ============================================================
    # CREATE
    # ============================================================
    @staticmethod
    def create(
        title,
        code=None,
        color=None,
        days_review=0,
        description=None,
        sort_order=0,
        is_active=1,
        group_ids=None,
        department_ids=None,
        group_sort_orders=None,
    ):
        """
        ایجاد زیرگروه جدید

        ★ بدون primary_department_id

        خروجی: (success: bool, message: str, subgroup_id: int or None)
        """
        connection = get_connection()
        try:
            if not title or not title.strip():
                return False, "عنوان زیرگروه الزامی است", None

            title = title.strip()
            code = code.strip() if code else None

            # ★ چک تکراری بودن title (در کل سیستم)
            existing = connection.execute(
                "SELECT id FROM document_subgroups WHERE title = ?",
                (title,)
            ).fetchone()
            if existing:
                return False, "زیرگروهی با این عنوان قبلاً وجود دارد", None

            # ★ چک تکراری بودن code
            if code:
                existing_code = connection.execute(
                    "SELECT id FROM document_subgroups WHERE code = ?",
                    (code,)
                ).fetchone()
                if existing_code:
                    return False, "زیرگروهی با این کد قبلاً وجود دارد", None

            # ★ درج زیرگروه
            cursor = connection.execute("""
                INSERT INTO document_subgroups
                (title, code, color, days_review, description,
                 sort_order, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                code,
                color.strip() if color else "#3D8499",
                days_review or 0,
                description.strip() if description else None,
                sort_order or 0,
                1 if is_active else 0,
            ))

            subgroup_id = cursor.lastrowid

            # ★ Sync گروه‌ها
            if group_ids:
                DocumentSubgroupService._sync_groups(
                    connection,
                    subgroup_id,
                    group_ids,
                    group_sort_orders,
                )

            # ★ Sync دپارتمان‌ها (بدون primary)
            if department_ids:
                DocumentSubgroupService._sync_departments(
                    connection,
                    subgroup_id,
                    department_ids,
                )

            connection.commit()
            return True, "زیرگروه با موفقیت ایجاد شد", subgroup_id

        except Exception as e:
            connection.rollback()
            return False, f"خطا در ایجاد زیرگروه: {str(e)}", None
        finally:
            connection.close()

    # ============================================================
    # UPDATE
    # ============================================================
    @staticmethod
    def update(
        subgroup_id,
        title,
        code=None,
        color=None,
        days_review=0,
        description=None,
        sort_order=0,
        is_active=1,
        group_ids=None,
        department_ids=None,
        group_sort_orders=None,
    ):
        """
        ویرایش زیرگروه — روابط M:N با sync جایگزین میشن

        ★ بدون primary_department_id
        """
        connection = get_connection()
        try:
            # ★ چک وجود زیرگروه
            subgroup = connection.execute(
                "SELECT id FROM document_subgroups WHERE id = ?",
                (subgroup_id,)
            ).fetchone()
            if not subgroup:
                return False, "زیرگروه پیدا نشد"

            if not title or not title.strip():
                return False, "عنوان زیرگروه الزامی است"

            title = title.strip()
            code = code.strip() if code else None

            # ★ چک تکراری بودن title
            existing = connection.execute(
                "SELECT id FROM document_subgroups "
                "WHERE title = ? AND id != ?",
                (title, subgroup_id)
            ).fetchone()
            if existing:
                return False, "زیرگروهی با این عنوان قبلاً وجود دارد"

            # ★ چک تکراری بودن code
            if code:
                existing_code = connection.execute(
                    "SELECT id FROM document_subgroups "
                    "WHERE code = ? AND id != ?",
                    (code, subgroup_id)
                ).fetchone()
                if existing_code:
                    return False, "زیرگروهی با این کد قبلاً وجود دارد"

            # ★ به‌روزرسانی زیرگروه
            connection.execute("""
                UPDATE document_subgroups
                SET title = ?,
                    code = ?,
                    color = ?,
                    days_review = ?,
                    description = ?,
                    sort_order = ?,
                    is_active = ?
                WHERE id = ?
            """, (
                title,
                code,
                color.strip() if color else "#3D8499",
                days_review or 0,
                description.strip() if description else None,
                sort_order or 0,
                1 if is_active else 0,
                subgroup_id,
            ))

            # ★ Sync گروه‌ها
            DocumentSubgroupService._sync_groups(
                connection,
                subgroup_id,
                group_ids or [],
                group_sort_orders,
            )

            # ★ Sync دپارتمان‌ها (بدون primary)
            DocumentSubgroupService._sync_departments(
                connection,
                subgroup_id,
                department_ids or [],
            )

            connection.commit()
            return True, "زیرگروه با موفقیت ویرایش شد"

        except Exception as e:
            connection.rollback()
            return False, f"خطا در ویرایش زیرگروه: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # HELPER: Sync گروه‌ها
    # ============================================================
    @staticmethod
    def _sync_groups(connection, subgroup_id, group_ids,
                     group_sort_orders=None):
        """همگام‌سازی گروه‌های یک زیرگروه"""
        group_sort_orders = group_sort_orders or {}

        # ★ حذف گروه‌هایی که در لیست جدید نیستن
        if group_ids:
            placeholders = ",".join("?" * len(group_ids))
            connection.execute(f"""
                DELETE FROM group_subgroups
                WHERE subgroup_id = ?
                  AND group_id NOT IN ({placeholders})
            """, (subgroup_id, *group_ids))
        else:
            connection.execute(
                "DELETE FROM group_subgroups WHERE subgroup_id = ?",
                (subgroup_id,)
            )

        # ★ افزودن/آپدیت
        for gid in group_ids:
            exists = connection.execute("""
                SELECT id FROM group_subgroups
                WHERE subgroup_id = ? AND group_id = ?
            """, (subgroup_id, gid)).fetchone()

            if not exists:
                connection.execute("""
                    INSERT INTO group_subgroups
                    (subgroup_id, group_id, sort_order, is_active)
                    VALUES (?, ?, ?, 1)
                """, (
                    subgroup_id,
                    gid,
                    group_sort_orders.get(gid, 0),
                ))
            elif gid in group_sort_orders:
                connection.execute("""
                    UPDATE group_subgroups
                    SET sort_order = ?
                    WHERE subgroup_id = ? AND group_id = ?
                """, (
                    group_sort_orders[gid],
                    subgroup_id,
                    gid,
                ))

    # ============================================================
    # HELPER: Sync دپارتمان‌ها
    # ============================================================
    @staticmethod
    def _sync_departments(connection, subgroup_id, department_ids):
        """
        همگام‌سازی دپارتمان‌های یک زیرگروه
        ★ بدون is_primary — همه دپارتمان‌ها یکسان
        """
        department_ids = list(department_ids or [])

        # ★ حذف دپارتمان‌هایی که در لیست جدید نیستن
        if department_ids:
            placeholders = ",".join("?" * len(department_ids))
            connection.execute(f"""
                DELETE FROM subgroup_departments
                WHERE subgroup_id = ?
                  AND department_id NOT IN ({placeholders})
            """, (subgroup_id, *department_ids))
        else:
            connection.execute(
                "DELETE FROM subgroup_departments WHERE subgroup_id = ?",
                (subgroup_id,)
            )

        # ★ افزودن دپارتمان‌های جدید
        for did in department_ids:
            connection.execute("""
                INSERT OR IGNORE INTO subgroup_departments
                (subgroup_id, department_id)
                VALUES (?, ?)
            """, (subgroup_id, did))

    # ============================================================
    # ADD GROUPS (افزودن گروه به زیرگروه موجود)
    # ============================================================
    @staticmethod
    def add_groups(subgroup_id, group_ids):
        """افزودن گروه‌های جدید به زیرگروه (بدون حذف قبلی‌ها)"""
        connection = get_connection()
        try:
            for gid in group_ids:
                connection.execute("""
                    INSERT OR IGNORE INTO group_subgroups
                    (subgroup_id, group_id, sort_order, is_active)
                    VALUES (?, ?, 0, 1)
                """, (subgroup_id, gid))
            connection.commit()
            return True, "گروه‌ها اضافه شدند"
        except Exception as e:
            connection.rollback()
            return False, f"خطا: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # REMOVE GROUP
    # ============================================================
    @staticmethod
    def remove_group(subgroup_id, group_id):
        """حذف یک گروه از زیرگروه"""
        connection = get_connection()
        try:
            connection.execute("""
                DELETE FROM group_subgroups
                WHERE subgroup_id = ? AND group_id = ?
            """, (subgroup_id, group_id))
            connection.commit()
            return True, "گروه حذف شد"
        except Exception as e:
            connection.rollback()
            return False, f"خطا: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # ADD DEPARTMENT (افزودن دپارتمان به زیرگروه موجود)
    # ============================================================
    @staticmethod
    def add_department(subgroup_id, department_id):
        """افزودن دپارتمان جدید به زیرگروه (بدون حذف قبلی‌ها)"""
        connection = get_connection()
        try:
            connection.execute("""
                INSERT OR IGNORE INTO subgroup_departments
                (subgroup_id, department_id)
                VALUES (?, ?)
            """, (subgroup_id, department_id))
            connection.commit()
            return True, "دپارتمان اضافه شد"
        except Exception as e:
            connection.rollback()
            return False, f"خطا: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # REMOVE DEPARTMENT
    # ============================================================
    @staticmethod
    def remove_department(subgroup_id, department_id):
        """حذف یک دپارتمان از زیرگروه"""
        connection = get_connection()
        try:
            connection.execute("""
                DELETE FROM subgroup_departments
                WHERE subgroup_id = ? AND department_id = ?
            """, (subgroup_id, department_id))
            connection.commit()
            return True, "دپارتمان حذف شد"
        except Exception as e:
            connection.rollback()
            return False, f"خطا: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # DELETE
    # ============================================================
    @staticmethod
    def delete(subgroup_id):
        """حذف زیرگروه"""
        connection = get_connection()
        try:
            subgroup = connection.execute(
                "SELECT id, title FROM document_subgroups WHERE id = ?",
                (subgroup_id,)
            ).fetchone()
            if not subgroup:
                return False, "زیرگروه پیدا نشد"

            # ★ چک اسناد
            docs_count = connection.execute("""
                SELECT COUNT(*) AS count
                FROM documents
                WHERE subgroup_id = ?
            """, (subgroup_id,)).fetchone()["count"]

            if docs_count > 0:
                return False, (
                    f"این زیرگروه دارای {docs_count} سند است "
                    "و قابل حذف نیست."
                )

            # ★ حذف ارتباطات
            connection.execute(
                "DELETE FROM group_subgroups WHERE subgroup_id = ?",
                (subgroup_id,)
            )
            connection.execute(
                "DELETE FROM subgroup_departments WHERE subgroup_id = ?",
                (subgroup_id,)
            )

            # ★ حذف زیرگروه
            connection.execute(
                "DELETE FROM document_subgroups WHERE id = ?",
                (subgroup_id,)
            )

            connection.commit()
            return True, "زیرگروه با موفقیت حذف شد"

        except Exception as e:
            connection.rollback()
            return False, f"خطا در حذف زیرگروه: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # TOGGLE ACTIVE
    # ============================================================
    @staticmethod
    def toggle_active(subgroup_id):
        """تغییر وضعیت فعال/غیرفعال زیرگروه"""
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT is_active FROM document_subgroups WHERE id = ?",
                (subgroup_id,)
            ).fetchone()
            if not row:
                return False, "زیرگروه پیدا نشد"

            new_status = 0 if row["is_active"] else 1
            connection.execute(
                "UPDATE document_subgroups SET is_active = ? WHERE id = ?",
                (new_status, subgroup_id)
            )
            connection.commit()
            return True, "وضعیت زیرگروه تغییر کرد"
        except Exception as e:
            connection.rollback()
            return False, f"خطا: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # GET FOR SELECT
    # ============================================================
    @staticmethod
    def get_for_select(group_id=None, active_only=True,
                       department_id=None):
        """لیست زیرگروه‌ها برای select box → [(id, title), ...]"""
        subgroups = DocumentSubgroupService.get_all(
            group_id=group_id,
            active_only=active_only,
            department_id=department_id,
            with_relations=False,
        )
        return [(sg["id"], sg["title"]) for sg in subgroups]

    # ============================================================
    # GET ALL SIMPLE (برای checkbox list)
    # ============================================================
    @staticmethod
    def get_all_simple(active_only=True, group_id=None):
        """لیست ساده زیرگروه‌ها برای checkbox list"""
        connection = get_connection()
        try:
            query = """
                SELECT id, title, code, color, is_active
                FROM document_subgroups
                WHERE 1=1
            """
            params = []

            if group_id:
                query += """
                    AND id IN (
                        SELECT subgroup_id FROM group_subgroups
                        WHERE group_id = ?
                    )
                """
                params.append(group_id)

            if active_only:
                query += " AND is_active = 1"

            query += " ORDER BY sort_order ASC, title ASC"

            rows = connection.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            connection.close()

    # ============================================================
    # GET BY GROUP
    # ============================================================
    @staticmethod
    def get_by_group(group_id, active_only=True):
        """دریافت همه زیرگروه‌های یک گروه"""
        return DocumentSubgroupService.get_all(
            group_id=group_id,
            active_only=active_only,
        )

    # ============================================================
    # GET BY DEPARTMENT
    # ============================================================
    @staticmethod
    def get_by_department(department_id, active_only=True):
        """دریافت همه زیرگروه‌های یک دپارتمان"""
        return DocumentSubgroupService.get_all(
            department_id=department_id,
            active_only=active_only,
        )

    # ============================================================
    # STATS
    # ============================================================
    @staticmethod
    def get_stats():
        """آمار کلی زیرگروه‌ها"""
        connection = get_connection()
        try:
            row = connection.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END)
                        AS active,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END)
                        AS inactive
                FROM document_subgroups
            """).fetchone()

            return {
                "total": row["total"] or 0,
                "active": row["active"] or 0,
                "inactive": row["inactive"] or 0,
            }
        finally:
            connection.close()