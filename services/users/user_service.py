"""
سرویس کاربران — مدیریت کامل کاربران
"""
from database import users
from database.connection import get_connection


# ============================================================
# ★ ثابت‌ها
# ============================================================
DEFAULT_AVATARS = {
    "default.png",
    "default-profile-male.png",
    "default-profile-female.png",
    "",
    None,
}

DEFAULT_AVATAR_MALE = "default-profile-male.png"
DEFAULT_AVATAR_FEMALE = "default-profile-female.png"


class UserService:
    """سرویس مدیریت کاربران"""

    # ============================================================
    # ★ کمکی — تعیین آواتار پیش‌فرض بر اساس جنسیت
    # ============================================================
    @staticmethod
    def _get_default_avatar(gender):
        """آواتار پیش‌فرض بر اساس جنسیت"""
        if gender == "female":
            return DEFAULT_AVATAR_FEMALE
        return DEFAULT_AVATAR_MALE

    @staticmethod
    def _is_default_avatar(avatar):
        """آیا آواتار فعلی پیش‌فرض است؟"""
        return avatar in DEFAULT_AVATARS

    @staticmethod
    def _resolve_avatar(avatar, gender, current_avatar=None, current_gender=None):
        """
        منطق هوشمند تعیین آواتار:
        1. اگر avatar جدید صریحاً داده شده → استفاده کن
        2. اگر جنسیت تغییر کرده و آواتار فعلی پیش‌فرض است → آواتار پیش‌فرض جدید
        3. در غیر این صورت → None (بدون تغییر)
        """
        # ★ حالت ۱: آواتار صریح
        if avatar:
            return avatar

        # ★ حالت ۲: جنسیت تغییر کرده و آواتار فعلی پیش‌فرض است
        if (
            gender is not None
            and current_gender is not None
            and gender != current_gender
            and UserService._is_default_avatar(current_avatar)
        ):
            return UserService._get_default_avatar(gender)

        # ★ حالت ۳: بدون تغییر
        return None

    # ============================================================
    # ★ ایجاد کاربر
    # ============================================================
    @staticmethod
    def create(
        username,
        password,
        full_name,
        role="expert",
        department_id=None,
        email=None,
        phone=None,
        national_code=None,
        position=None,
        gender=None,
        is_active=1,
        avatar=None,
    ):
        """ایجاد کاربر جدید"""
        # ★ تعیین جنسیت پیش‌فرض
        final_gender = gender or "male"

        # ★ تعیین آواتار پیش‌فرض
        if not avatar:
            avatar = UserService._get_default_avatar(final_gender)

        # ---- مرحله ۱: ایجاد پایه کاربر ----
        success = users.create_user(
            username=username,
            password=password,
            full_name=full_name,
            role=role,
            department_id=department_id,
        )

        if not success:
            return False

        # ---- مرحله ۲: به‌روزرسانی فیلدهای اضافی ----
        try:
            connection = get_connection()
            try:
                connection.execute(
                    """
                    UPDATE users
                    SET email = ?,
                        phone = ?,
                        national_code = ?,
                        position = ?,
                        gender = ?,
                        is_active = ?,
                        avatar = ?,
                        is_online = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE username = ?
                    """,
                    (
                        email,
                        phone,
                        national_code,
                        position,
                        final_gender,
                        1 if is_active else 0,
                        avatar,
                        username,
                    )
                )
                connection.commit()
            finally:
                connection.close()
        except Exception as e:
            print(f"⚠️ خطا در به‌روزرسانی فیلدهای اضافی: {e}")
            # ★ کاربر اصلی ساخته شده، پس موفقیت‌آمیز است

        return True

    # ============================================================
    # ★ احراز هویت
    # ============================================================
    @staticmethod
    def authenticate(username, password):
        return users.authenticate_user(
            username=username,
            password=password,
        )

    @staticmethod
    def verify_password(username, password):
        return UserService.authenticate(username, password)

    # ============================================================
    # ★ خواندن
    # ============================================================
    @staticmethod
    def get_by_id(user_id):
        user = users.get_user_by_id(user_id)
        if user and not isinstance(user, dict):
            return dict(user)
        return user

    @staticmethod
    def get_by_username(username):
        try:
            connection = get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,),
                )
                row = cursor.fetchone()
                if row and not isinstance(row, dict):
                    return dict(row)
                return row
            finally:
                connection.close()
        except Exception:
            return None

    @staticmethod
    def get_all():
        users_list = users.get_all_users()
        if users_list:
            return [
                dict(u) if not isinstance(u, dict) else u
                for u in users_list
            ]
        return users_list

    # ============================================================
    # ★ به‌روزرسانی
    # ============================================================
    @staticmethod
    def update(
        user_id,
        username=None,
        full_name=None,
        role=None,
        password=None,
        department_id=None,
        email=None,
        phone=None,
        national_code=None,
        position=None,
        gender=None,
        is_active=None,
        avatar=None,
    ):
        """به‌روزرسانی کاربر با منطق هوشمند آواتار"""
        connection = get_connection()

        try:
            # ---- بررسی تکراری نبودن username ----
            if username is not None:
                existing = connection.execute(
                    """
                    SELECT id FROM users
                    WHERE username = ? AND id != ?
                    """,
                    (username, user_id),
                ).fetchone()

                if existing:
                    return False

            # ---- دریافت اطلاعات فعلی کاربر ----
            current_row = connection.execute(
                "SELECT gender, avatar FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()

            if not current_row:
                return False

            if not isinstance(current_row, dict):
                current_user = dict(current_row)
            else:
                current_user = current_row

            current_gender = current_user.get("gender") or "male"
            current_avatar = current_user.get("avatar")

            # ---- ساخت داینامیک Query ----
            fields = []
            values = []

            if username is not None:
                fields.append("username = ?")
                values.append(username)

            if full_name is not None:
                fields.append("full_name = ?")
                values.append(full_name)

            if role is not None:
                fields.append("role = ?")
                values.append(role)

            if password:
                fields.append("password = ?")
                values.append(users.hash_password(password))

            if department_id is not None:
                fields.append("department_id = ?")
                values.append(department_id)

            if email is not None:
                fields.append("email = ?")
                values.append(email)

            if phone is not None:
                fields.append("phone = ?")
                values.append(phone)

            if national_code is not None:
                fields.append("national_code = ?")
                values.append(national_code)

            if position is not None:
                fields.append("position = ?")
                values.append(position)

            # ---- جنسیت ----
            if gender is not None:
                fields.append("gender = ?")
                values.append(gender)

            # ---- وضعیت فعال/غیرفعال ----
            if is_active is not None:
                fields.append("is_active = ?")
                values.append(1 if is_active else 0)

            # ---- ★ آواتار — منطق هوشمند ----
            new_avatar = UserService._resolve_avatar(
                avatar=avatar,
                gender=gender,
                current_avatar=current_avatar,
                current_gender=current_gender,
            )

            if new_avatar is not None:
                fields.append("avatar = ?")
                values.append(new_avatar)

            # ---- اگر هیچ فیلدی تغییر نکرده ----
            if not fields:
                return True

            fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(user_id)

            query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
            connection.execute(query, values)
            connection.commit()
            return True

        except Exception as e:
            connection.rollback()
            print(f"⚠️ خطا در به‌روزرسانی کاربر: {e}")
            return False

        finally:
            connection.close()

    # ============================================================
    # ★ تغییر نقش، حذف، رمز
    # ============================================================
    @staticmethod
    def update_role(user_id, role):
        return users.update_user_role(user_id, role)

    @staticmethod
    def delete(user_id):
        return users.delete_user(user_id)

    @staticmethod
    def change_password(user_id, new_password):
        return users.change_password(user_id, new_password)

    # ============================================================
    # ★ وضعیت آنلاین / آفلاین
    # ============================================================
    @staticmethod
    def update_last_seen(user_id):
        return users.update_last_seen(user_id)

    @staticmethod
    def update_last_login(user_id):
        try:
            if hasattr(users, "update_last_login"):
                return users.update_last_login(user_id)

            connection = get_connection()
            try:
                connection.execute(
                    """
                    UPDATE users
                    SET last_login = CURRENT_TIMESTAMP,
                        last_seen = CURRENT_TIMESTAMP,
                        is_online = 1
                    WHERE id = ?
                    """,
                    (user_id,),
                )
                connection.commit()
                return True
            finally:
                connection.close()
        except Exception:
            return False

    @staticmethod
    def set_offline(user_id):
        return users.set_user_offline(user_id)

    @staticmethod
    def set_online_status(user_id, is_online):
        try:
            connection = get_connection()
            try:
                connection.execute(
                    """
                    UPDATE users
                    SET is_online = ?,
                        last_seen = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (1 if is_online else 0, user_id),
                )
                connection.commit()
                return True
            finally:
                connection.close()
        except Exception:
            return False

    @staticmethod
    def is_online(user_id, threshold_minutes=5):
        return users.is_user_online(user_id, threshold_minutes)

    @staticmethod
    def get_online_users(threshold_minutes=5):
        return users.get_online_users(threshold_minutes)

    @staticmethod
    def cleanup_stale_users(threshold_minutes=5):
        return users.cleanup_stale_users(threshold_minutes)

    @staticmethod
    def get_last_login_and_seen(user_id):
        return users.get_last_login_and_seen(user_id)

    # ============================================================
    # ★ آواتار — متدهای اختصاصی
    # ============================================================
    @staticmethod
    def update_avatar(user_id, avatar_filename):
        """
        به‌روزرسانی آواتار کاربر
        (مثلاً بعد از آپلود فایل)
        """
        try:
            connection = get_connection()
            try:
                connection.execute(
                    """
                    UPDATE users
                    SET avatar = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (avatar_filename, user_id),
                )
                connection.commit()
                return True
            finally:
                connection.close()
        except Exception:
            return False

    @staticmethod
    def reset_avatar(user_id):
        """
        بازگرداندن آواتار به پیش‌فرض بر اساس جنسیت
        """
        try:
            connection = get_connection()
            try:
                # ★ خواندن جنسیت کاربر
                row = connection.execute(
                    "SELECT gender FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()

                if not row:
                    return False

                gender = dict(row).get("gender") or "male"
                default = UserService._get_default_avatar(gender)

                connection.execute(
                    """
                    UPDATE users
                    SET avatar = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (default, user_id),
                )
                connection.commit()
                return True
            finally:
                connection.close()
        except Exception:
            return False

    # ============================================================
    # ★ آپلود فایل آواتار
    # ============================================================
    @staticmethod
    def save_avatar_file(file_storage, user_id, upload_folder):
        """
        ذخیره فایل آواتار با نام یکتا
        Returns:
            str: نام فایل ذخیره‌شده یا None در صورت خطا
        """
        import os
        import time

        if not file_storage or not file_storage.filename:
            return None

        # ---- بررسی پسوند ----
        allowed_exts = {"png", "jpg", "jpeg", "gif", "webp"}
        filename = file_storage.filename
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext not in allowed_exts:
            return None

        # ---- ساخت نام یکتا ----
        timestamp = int(time.time())
        new_filename = f"user_{user_id}_{timestamp}.{ext}"

        # ---- مسیر ذخیره ----
        avatar_dir = os.path.join(upload_folder, "avatar")
        os.makedirs(avatar_dir, exist_ok=True)

        file_path = os.path.join(avatar_dir, new_filename)

        # ---- ذخیره ----
        try:
            file_storage.save(file_path)
            return new_filename
        except Exception as e:
            print(f"❌ خطا در ذخیره آواتار: {e}")
            return None