from database.connection import get_connection


class DocumentGroupService:
    """
    سرویس گروه‌های سند با ساختار Many-to-Many

    ★ ویژگی‌ها:
    - هر گروه می‌تونه چند زیرگروه داشته باشه
    - هر زیرگروه می‌تونه در چند گروه باشه (از طریق واسط)
    - ترتیب زیرگروه‌ها در هر گروه مستقل قابل تنظیمه
    - گروه‌ها خودشون دپارتمان مستقیم ندارن (از زیرگروه‌ها ارث می‌برن)
    """

    # ============================================================
    # GET ALL — لیست گروه‌ها
    # ============================================================
    @staticmethod
    def get_all(active_only=False, search=None, department_id=None,
                with_subgroups=False):
        """
        دریافت لیست همه گروه‌ها

        پارامترها:
            active_only    : فقط فعال‌ها
            search         : جستجو در title یا code
            department_id  : فیلتر بر اساس دپارتمان
            with_subgroups : آیا زیرگروه‌ها هم لود بشن؟
        """
        connection = get_connection()
        try:
            query = """
                SELECT
                    g.id,
                    g.title,
                    g.code,
                    g.color,
                    g.description,
                    g.sort_order,
                    g.is_active,
                    g.created_at,
                    (
                        SELECT COUNT(*)
                        FROM group_subgroups gs
                        WHERE gs.group_id = g.id
                    ) AS subgroups_count
                FROM document_groups g
                WHERE 1=1
            """
            params = []

            if active_only:
                query += " AND g.is_active = 1"

            if search:
                query += " AND (g.title LIKE ? OR g.code LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])

            if department_id:
                query += """
                    AND g.id IN (
                        SELECT DISTINCT gs.group_id
                        FROM group_subgroups gs
                        INNER JOIN subgroup_departments sd
                            ON sd.subgroup_id = gs.subgroup_id
                        WHERE sd.department_id = ?
                    )
                """
                params.append(department_id)

            query += " ORDER BY g.sort_order ASC, g.title ASC"

            rows = connection.execute(query, params).fetchall()
            groups = [dict(r) for r in rows]

            if with_subgroups:
                for g in groups:
                    g["subgroups"] = (
                        DocumentGroupService._get_subgroups_of_group(
                            connection, g["id"]
                        )
                    )

            return groups
        finally:
            connection.close()

    # ============================================================
    # GET BY ID
    # ============================================================
    @staticmethod
    def get_by_id(group_id):
        """دریافت یک گروه با تمام اطلاعات مرتبط"""
        connection = get_connection()
        try:
            row = connection.execute("""
                SELECT
                    g.id,
                    g.title,
                    g.code,
                    g.color,
                    g.description,
                    g.sort_order,
                    g.is_active,
                    g.created_at,
                    (
                        SELECT COUNT(*)
                        FROM group_subgroups gs
                        WHERE gs.group_id = g.id
                    ) AS subgroups_count
                FROM document_groups g
                WHERE g.id = ?
            """, (group_id,)).fetchone()

            if not row:
                return None

            result = dict(row)
            result["subgroups"] = DocumentGroupService._get_subgroups_of_group(
                connection, group_id
            )
            result["subgroup_ids"] = [sg["id"] for sg in result["subgroups"]]

            return result
        finally:
            connection.close()

    # ============================================================
    # GET BY CODE
    # ============================================================
    @staticmethod
    def get_by_code(code):
        """دریافت گروه با کد"""
        connection = get_connection()
        try:
            row = connection.execute("""
                SELECT id, title, code
                FROM document_groups
                WHERE code = ?
            """, (code,)).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    # ============================================================
    # HELPER: زیرگروه‌های یک گروه
    # ============================================================
    @staticmethod
    def _get_subgroups_of_group(connection, group_id):
        """
        دریافت لیست زیرگروه‌های یک گروه با ترتیب اختصاصی
        + لیست دپارتمان‌های متولی هر زیرگروه (M:N)
        """
        rows = connection.execute("""
            SELECT
                sg.id,
                sg.title,
                sg.code,
                sg.color,
                sg.days_review,
                sg.description,
                sg.is_active,
                gs.sort_order AS link_sort_order,
                gs.is_active AS link_is_active
            FROM document_subgroups sg
            INNER JOIN group_subgroups gs ON gs.subgroup_id = sg.id
            WHERE gs.group_id = ?
            ORDER BY gs.sort_order ASC, sg.title ASC
        """, (group_id,)).fetchall()

        result = []
        for row in rows:
            item = dict(row)

            # ★ دپارتمان‌های متولی این زیرگروه (M:N — بدون primary)
            departments = connection.execute("""
                SELECT d.id, d.title, d.code
                FROM departments d
                INNER JOIN subgroup_departments sd
                    ON sd.department_id = d.id
                WHERE sd.subgroup_id = ?
                ORDER BY d.title ASC
            """, (item["id"],)).fetchall()

            item["departments"] = [dict(d) for d in departments]

            # ★ برای سازگاری با کدهای قدیمی: اولین دپارتمان
            if departments:
                item["department_title"] = departments[0]["title"]
                item["department_id"] = departments[0]["id"]
            else:
                item["department_title"] = None
                item["department_id"] = None

            result.append(item)

        return result

    # ============================================================
    # GET SUBGROUPS (public)
    # ============================================================
    @staticmethod
    def get_subgroups(group_id, active_only=True):
        """دریافت لیست زیرگروه‌های یک گروه (اطلاعات کامل)"""
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
                    gs.sort_order AS link_sort_order,
                    gs.is_active AS link_is_active,
                    (
                        SELECT COUNT(*)
                        FROM documents d
                        WHERE d.subgroup_id = sg.id
                    ) AS documents_count
                FROM document_subgroups sg
                INNER JOIN group_subgroups gs ON gs.subgroup_id = sg.id
                WHERE gs.group_id = ?
            """
            params = [group_id]

            if active_only:
                query += " AND sg.is_active = 1 AND gs.is_active = 1"

            query += " ORDER BY gs.sort_order ASC, sg.title ASC"

            rows = connection.execute(query, params).fetchall()
            subgroups = [dict(r) for r in rows]

            # ★ پر کردن دپارتمان‌های هر زیرگروه (M:N — بدون primary)
            for sg in subgroups:
                departments = connection.execute("""
                    SELECT d.id, d.title, d.code
                    FROM departments d
                    INNER JOIN subgroup_departments sd
                        ON sd.department_id = d.id
                    WHERE sd.subgroup_id = ?
                    ORDER BY d.title ASC
                """, (sg["id"],)).fetchall()

                sg["departments"] = [dict(d) for d in departments]

                if departments:
                    sg["department_title"] = departments[0]["title"]
                    sg["department_id"] = departments[0]["id"]
                else:
                    sg["department_title"] = None
                    sg["department_id"] = None

            return subgroups
        finally:
            connection.close()

    # ============================================================
    # GET FOR SELECT
    # ============================================================
    @staticmethod
    def get_for_select(active_only=True):
        """لیست گروه‌ها برای select box → [(id, title), ...]"""
        groups = DocumentGroupService.get_all(active_only=active_only)
        return [(g["id"], g["title"]) for g in groups]

    # ============================================================
    # GET ALL SIMPLE (برای checkbox list)
    # ============================================================
    @staticmethod
    def get_all_simple(active_only=True):
        """لیست ساده گروه‌ها برای checkbox list"""
        connection = get_connection()
        try:
            query = """
                SELECT id, title, code, color, is_active
                FROM document_groups
                WHERE 1=1
            """
            params = []

            if active_only:
                query += " AND is_active = 1"

            query += " ORDER BY sort_order ASC, title ASC"

            rows = connection.execute(query, params).fetchall()
            return [dict(r) for r in rows]
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
        description=None,
        sort_order=0,
        is_active=1,
        subgroup_ids=None,
        subgroup_sort_orders=None,
    ):
        """
        ایجاد گروه جدید
        خروجی: (success: bool, message: str, group_id: int or None)
        """
        connection = get_connection()
        try:
            if not title or not title.strip():
                return False, "عنوان گروه الزامی است", None

            title = title.strip()
            code = code.strip() if code else None

            # چک تکراری
            existing = connection.execute(
                "SELECT id FROM document_groups WHERE title = ?",
                (title,)
            ).fetchone()
            if existing:
                return False, "گروهی با این عنوان قبلاً وجود دارد", None

            if code:
                existing_code = connection.execute(
                    "SELECT id FROM document_groups WHERE code = ?",
                    (code,)
                ).fetchone()
                if existing_code:
                    return False, "گروهی با این کد قبلاً وجود دارد", None

            cursor = connection.execute("""
                INSERT INTO document_groups
                (title, code, color, description, sort_order, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                title,
                code,
                color.strip() if color else "#3D8499",
                description.strip() if description else None,
                sort_order or 0,
                1 if is_active else 0,
            ))

            group_id = cursor.lastrowid

            # Sync زیرگروه‌ها
            if subgroup_ids:
                DocumentGroupService._sync_subgroups(
                    connection,
                    group_id,
                    subgroup_ids,
                    subgroup_sort_orders,
                )

            connection.commit()
            return True, "گروه با موفقیت ایجاد شد", group_id

        except Exception as e:
            connection.rollback()
            return False, f"خطا در ایجاد گروه: {str(e)}", None
        finally:
            connection.close()

    # ============================================================
    # UPDATE
    # ============================================================
    @staticmethod
    def update(
        group_id,
        title,
        code=None,
        color=None,
        description=None,
        sort_order=0,
        is_active=1,
        subgroup_ids=None,
        subgroup_sort_orders=None,
    ):
        """ویرایش گروه — ارتباطات M:N جایگزین میشن"""
        connection = get_connection()
        try:
            group = connection.execute(
                "SELECT id FROM document_groups WHERE id = ?",
                (group_id,)
            ).fetchone()
            if not group:
                return False, "گروه پیدا نشد"

            if not title or not title.strip():
                return False, "عنوان گروه الزامی است"

            title = title.strip()
            code = code.strip() if code else None

            existing = connection.execute(
                "SELECT id FROM document_groups WHERE title = ? AND id != ?",
                (title, group_id)
            ).fetchone()
            if existing:
                return False, "گروهی با این عنوان قبلاً وجود دارد"

            if code:
                existing_code = connection.execute(
                    "SELECT id FROM document_groups WHERE code = ? AND id != ?",
                    (code, group_id)
                ).fetchone()
                if existing_code:
                    return False, "گروهی با این کد قبلاً وجود دارد"

            connection.execute("""
                UPDATE document_groups
                SET title = ?,
                    code = ?,
                    color = ?,
                    description = ?,
                    sort_order = ?,
                    is_active = ?
                WHERE id = ?
            """, (
                title,
                code,
                color.strip() if color else "#3D8499",
                description.strip() if description else None,
                sort_order or 0,
                1 if is_active else 0,
                group_id,
            ))

            DocumentGroupService._sync_subgroups(
                connection,
                group_id,
                subgroup_ids or [],
                subgroup_sort_orders,
            )

            connection.commit()
            return True, "گروه با موفقیت ویرایش شد"

        except Exception as e:
            connection.rollback()
            return False, f"خطا در ویرایش گروه: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # HELPER: Sync زیرگروه‌ها
    # ============================================================
    @staticmethod
    def _sync_subgroups(connection, group_id, subgroup_ids,
                        subgroup_sort_orders=None):
        """همگام‌سازی زیرگروه‌های یک گروه"""
        subgroup_sort_orders = subgroup_sort_orders or {}

        # حذف زیرگروه‌هایی که در لیست جدید نیستن
        if subgroup_ids:
            placeholders = ",".join("?" * len(subgroup_ids))
            connection.execute(f"""
                DELETE FROM group_subgroups
                WHERE group_id = ? AND subgroup_id NOT IN ({placeholders})
            """, (group_id, *subgroup_ids))
        else:
            connection.execute(
                "DELETE FROM group_subgroups WHERE group_id = ?",
                (group_id,)
            )

        # افزودن/آپدیت زیرگروه‌ها
        for sgid in subgroup_ids:
            exists = connection.execute("""
                SELECT id FROM group_subgroups
                WHERE group_id = ? AND subgroup_id = ?
            """, (group_id, sgid)).fetchone()

            if not exists:
                connection.execute("""
                    INSERT INTO group_subgroups
                    (group_id, subgroup_id, sort_order, is_active)
                    VALUES (?, ?, ?, 1)
                """, (group_id, sgid, subgroup_sort_orders.get(sgid, 0)))
            elif sgid in subgroup_sort_orders:
                connection.execute("""
                    UPDATE group_subgroups
                    SET sort_order = ?
                    WHERE group_id = ? AND subgroup_id = ?
                """, (subgroup_sort_orders[sgid], group_id, sgid))

    # ============================================================
    # ADD SUBGROUPS
    # ============================================================
    @staticmethod
    def add_subgroups(group_id, subgroup_ids):
        """افزودن زیرگروه‌های جدید به گروه (بدون حذف قبلی‌ها)"""
        connection = get_connection()
        try:
            for sgid in subgroup_ids:
                connection.execute("""
                    INSERT OR IGNORE INTO group_subgroups
                    (group_id, subgroup_id, sort_order, is_active)
                    VALUES (?, ?, 0, 1)
                """, (group_id, sgid))
            connection.commit()
            return True, "زیرگروه‌ها اضافه شدند"
        except Exception as e:
            connection.rollback()
            return False, f"خطا: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # REMOVE SUBGROUP
    # ============================================================
    @staticmethod
    def remove_subgroup(group_id, subgroup_id):
        """حذف یک زیرگروه از گروه"""
        connection = get_connection()
        try:
            connection.execute("""
                DELETE FROM group_subgroups
                WHERE group_id = ? AND subgroup_id = ?
            """, (group_id, subgroup_id))
            connection.commit()
            return True, "زیرگروه حذف شد"
        except Exception as e:
            connection.rollback()
            return False, f"خطا: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # DELETE
    # ============================================================
    @staticmethod
    def delete(group_id):
        """حذف گروه"""
        connection = get_connection()
        try:
            group = connection.execute(
                "SELECT id, title FROM document_groups WHERE id = ?",
                (group_id,)
            ).fetchone()
            if not group:
                return False, "گروه پیدا نشد"

            # چک اسناد
            docs_count = connection.execute("""
                SELECT COUNT(*) AS count
                FROM documents
                WHERE group_id = ?
            """, (group_id,)).fetchone()["count"]

            if docs_count > 0:
                return False, (
                    f"این گروه دارای {docs_count} سند است "
                    "و قابل حذف نیست. ابتدا اسناد را منتقل کنید."
                )

            # حذف ارتباطات
            connection.execute(
                "DELETE FROM group_subgroups WHERE group_id = ?",
                (group_id,)
            )

            # حذف گروه
            connection.execute(
                "DELETE FROM document_groups WHERE id = ?",
                (group_id,)
            )

            connection.commit()
            return True, "گروه با موفقیت حذف شد"

        except Exception as e:
            connection.rollback()
            return False, f"خطا در حذف گروه: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # TOGGLE ACTIVE
    # ============================================================
    @staticmethod
    def toggle_active(group_id):
        """تغییر وضعیت فعال/غیرفعال"""
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT is_active FROM document_groups WHERE id = ?",
                (group_id,)
            ).fetchone()
            if not row:
                return False, "گروه پیدا نشد"

            new_status = 0 if row["is_active"] else 1
            connection.execute(
                "UPDATE document_groups SET is_active = ? WHERE id = ?",
                (new_status, group_id)
            )
            connection.commit()
            return True, "وضعیت گروه تغییر کرد"
        except Exception as e:
            connection.rollback()
            return False, f"خطا: {str(e)}"
        finally:
            connection.close()

    # ============================================================
    # STATS
    # ============================================================
    @staticmethod
    def get_stats():
        """آمار کلی گروه‌ها"""
        connection = get_connection()
        try:
            row = connection.execute("""
                SELECT
                    COUNT(*) AS total_groups,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END)
                        AS active_groups,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END)
                        AS inactive_groups
                FROM document_groups
            """).fetchone()

            subgroups_row = connection.execute("""
                SELECT COUNT(*) AS total_subgroups
                FROM document_subgroups
            """).fetchone()

            links_row = connection.execute("""
                SELECT COUNT(*) AS total_links
                FROM group_subgroups
            """).fetchone()

            return {
                "total_groups": row["total_groups"] or 0,
                "active_groups": row["active_groups"] or 0,
                "inactive_groups": row["inactive_groups"] or 0,
                "total_subgroups": subgroups_row["total_subgroups"] or 0,
                "total_links": links_row["total_links"] or 0,
            }
        finally:
            connection.close()