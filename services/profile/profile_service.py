from database.connection import get_connection
from security.passwords import hash_password, verify_password


class ProfileService:

    # ============================================================
    # ★ خواندن پروفایل
    # ============================================================
    @staticmethod
    def get_profile(user_id):
        connection = get_connection()
        try:
            user = connection.execute(
                """
                SELECT
                    id,
                    username,
                    password,
                    full_name,
                    role,
                    email,
                    phone,
                    national_code,
                    position,
                    gender,
                    avatar,
                    is_active,
                    created_at,
                    updated_at,
                    last_login,
                    last_seen,
                    is_online
                FROM users
                WHERE id = ?
                LIMIT 1
                """,
                (user_id,)
            ).fetchone()
            return user
        finally:
            connection.close()

    # ============================================================
    # ★ بروزرسانی اطلاعات پروفایل
    # ============================================================
    @staticmethod
    def update_profile(
        user_id,
        full_name,
        email,
        phone,
        position,
        national_code=None,
        gender=None,                # ★ جدید
    ):
        connection = get_connection()
        try:
            # ★ دریافت آواتار فعلی و جنسیت قبلی
            current = connection.execute(
                "SELECT avatar, gender FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()

            if not current:
                return False

            current_avatar = current["avatar"] if current["avatar"] else "default.png"
            current_gender = current["gender"] if current["gender"] else "male"

            # ★ منطق هوشمند آواتار:
            #   - اگر آواتار فعلی پیش‌فرض است و جنسیت تغییر کرده → آواتار پیش‌فرض جدید
            default_avatars = {
                "default.png",
                "default-profile-male.png",
                "default-profile-female.png",
            }
            is_default_avatar = current_avatar in default_avatars

            new_avatar = current_avatar
            if gender and gender != current_gender and is_default_avatar:
                if gender == "female":
                    new_avatar = "default-profile-female.png"
                else:
                    new_avatar = "default-profile-male.png"

            connection.execute(
                """
                UPDATE users
                SET
                    full_name = ?,
                    email = ?,
                    phone = ?,
                    position = ?,
                    national_code = ?,
                    gender = ?,
                    avatar = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    full_name,
                    email,
                    phone,
                    position,
                    national_code,
                    gender or "male",
                    new_avatar,
                    user_id
                )
            )
            connection.commit()
            return True
        except Exception as e:
            print(f"Error update_profile: {e}")
            connection.rollback()
            return False
        finally:
            connection.close()

    # ============================================================
    # ★ بروزرسانی آواتار
    # ============================================================
    @staticmethod
    def update_avatar(user_id, avatar):
        connection = get_connection()
        try:
            connection.execute(
                """
                UPDATE users
                SET
                    avatar = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (avatar, user_id)
            )
            connection.commit()
            return True
        except Exception as e:
            print(f"Error update_avatar: {e}")
            connection.rollback()
            return False
        finally:
            connection.close()

    # ============================================================
    # ★ حذف آواتار (بازگشت به پیش‌فرض بر اساس جنسیت)
    # ============================================================
    @staticmethod
    def remove_avatar(user_id):
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT gender FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()

            gender = (row["gender"] if row and row["gender"] else "male")

            default_avatar = (
                "default-profile-female.png"
                if gender == "female"
                else "default-profile-male.png"
            )

            return ProfileService.update_avatar(user_id, default_avatar)
        finally:
            connection.close()

    # ============================================================
    # ★ تغییر رمز عبور
    # ============================================================
    @staticmethod
    def change_password(user_id, old_password, new_password):
        connection = get_connection()
        try:
            user = connection.execute(
                "SELECT password FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()

            if not user:
                return False

            stored_hash = user["password"]

            if not ProfileService._verify_password(stored_hash, old_password):
                return False

            new_hash = hash_password(new_password)

            connection.execute(
                """
                UPDATE users
                SET password = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_hash, user_id)
            )
            connection.commit()
            return True

        except Exception as e:
            print(f"Error change_password: {e}")
            connection.rollback()
            return False
        finally:
            connection.close()

    # ============================================================
    # ★ بررسی رمز با تشخیص نوع هش
    # ============================================================
    @staticmethod
    def _verify_password(stored_hash, raw_password):
        """بررسی رمز با پشتیبانی از هش‌های قدیمی (SHA-256)."""
        return verify_password(stored_hash, raw_password)

    # ============================================================
    # ★ بررسی تکراری نبودن ایمیل/تلفن
    # ============================================================
    @staticmethod
    def is_email_taken(user_id, email):
        if not email:
            return False
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT id FROM users WHERE email = ? AND id != ?",
                (email, user_id)
            ).fetchone()
            return row is not None
        finally:
            connection.close()

    @staticmethod
    def is_phone_taken(user_id, phone):
        if not phone:
            return False
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT id FROM users WHERE phone = ? AND id != ?",
                (phone, user_id)
            ).fetchone()
            return row is not None
        finally:
            connection.close()