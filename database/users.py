from datetime import datetime, timedelta

from security.passwords import (
    hash_password,
    needs_rehash,
    verify_password,
)

from .connection import get_connection

# ------------------------------------------------------------------
# ★ هش رمز عبور
# ------------------------------------------------------------------
# رمزهای جدید با scrypt (نمک‌دار) ذخیره می‌شوند.رمزهای قدیمی SHA-256
# هنوز پذیرفته و در اولین ورود موفق به‌صورت خودکار ارتقا داده می‌شوند.
# تابع hash_password از security.passwords برای سازگاری دوباره صادر می‌شود.

#: هش ساختگی برای یکسان‌سازی زمان پاسخ وقتی نام کاربری وجود ندارد
_DUMMY_HASH = None


def _burn_time_for_missing_user(password):
    """جلوگیری از افشای وجود/عدم‌وجود نام کاربری از طریق زمان پاسخ."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("sspe-timing-equalizer")
    verify_password(_DUMMY_HASH, password)


# ============================================================
# ★ CREATE USER (با پشتیبانی از department_id)
# ============================================================
def create_user(username, password, full_name, role="expert", department_id=None):
    connection = get_connection()
    try:
        # اگه department_id صفر یا None بود، None ذخیره کن
        if department_id in (0, "0", ""):
            department_id = None

        connection.execute(
            """
            INSERT INTO users (username, password, full_name, role, department_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                username,
                hash_password(password),
                full_name,
                role,
                department_id
            )
        )
        connection.commit()
        return True
    except Exception as e:
        print(f"Error create_user: {e}")
        return False
    finally:
        connection.close()


def authenticate_user(username, password):
    """بررسی نام کاربری/رمز و به‌روزرسانی وضعیت ورود.

    ★ اگر رمز ذخیره‌شده با روش قدیمی (SHA-256 بدون نمک) باشد، پس از
      ورود موفق به‌طور خودکار با scrypt بازنویسی می‌شود.
    """
    connection = get_connection()
    try:
        user = connection.execute(
            """
            SELECT * FROM users
            WHERE username = ? AND is_active = 1
            """,
            (username,)
        ).fetchone()

        if not user:
            _burn_time_for_missing_user(password)
            return None

        if not verify_password(user["password"], password):
            return None

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if needs_rehash(user["password"]):
            connection.execute(
                """
                UPDATE users
                SET password = ?, last_login = ?, last_seen = ?, is_online = 1
                WHERE id = ?
                """,
                (hash_password(password), now, now, user["id"])
            )
        else:
            connection.execute(
                """
                UPDATE users
                SET last_login = ?, last_seen = ?, is_online = 1
                WHERE id = ?
                """,
                (now, now, user["id"])
            )

        connection.commit()

        # ردیف تازه را برگردان تا هش ارتقایافته در پاسخ دیده شود
        return connection.execute(
            "SELECT * FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
    except Exception as e:
        print(f"Error authenticate_user: {e}")
        return None
    finally:
        connection.close()


def get_user_by_id(user_id):
    connection = get_connection()
    user = connection.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    connection.close()
    return user


def get_all_users():
    connection = get_connection()
    users = connection.execute(
        "SELECT * FROM users ORDER BY id DESC"
    ).fetchall()
    connection.close()
    return users


def update_user_role(user_id, role):
    connection = get_connection()
    cursor = connection.execute(
        "UPDATE users SET role = ? WHERE id = ?",
        (role, user_id)
    )
    connection.commit()
    success = cursor.rowcount > 0
    connection.close()
    return success


def delete_user(user_id):
    connection = get_connection()
    cursor = connection.execute(
        "DELETE FROM users WHERE id = ?",
        (user_id,)
    )
    connection.commit()
    success = cursor.rowcount > 0
    connection.close()
    return success


def change_password(user_id, new_password):
    connection = get_connection()
    cursor = connection.execute(
        "UPDATE users SET password = ? WHERE id = ?",
        (hash_password(new_password), user_id)
    )
    connection.commit()
    success = cursor.rowcount > 0
    connection.close()
    return success


# ============================================================
# ★ متدهای وضعیت آنلاین/آفلاین ★
# ============================================================

def update_last_seen(user_id):
    """به‌روزرسانی آخرین فعالیت"""
    connection = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        connection.execute(
            "UPDATE users SET last_seen = ?, is_online = 1 WHERE id = ?",
            (now, user_id)
        )
        connection.commit()
        return True
    except Exception as e:
        print(f"Error update_last_seen: {e}")
        return False
    finally:
        connection.close()


def set_user_offline(user_id):
    """علامت‌گذاری کاربر به‌عنوان آفلاین (logout)"""
    connection = get_connection()
    try:
        connection.execute(
            "UPDATE users SET is_online = 0 WHERE id = ?",
            (user_id,)
        )
        connection.commit()
        return True
    except Exception as e:
        print(f"Error set_user_offline: {e}")
        return False
    finally:
        connection.close()


def is_user_online(user_id, threshold_minutes=5):
    """
    کاربر آنلاین محسوب میشه اگه:
    - is_online = 1 باشه
    - AND last_seen کمتر از threshold_minutes دقیقه پیش باشه
    """
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT last_seen, is_online FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        if not row or not row["last_seen"]:
            return False

        if row["is_online"] != 1:
            return False

        last_seen = datetime.strptime(row["last_seen"], "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - last_seen
        return diff < timedelta(minutes=threshold_minutes)
    except Exception as e:
        print(f"Error is_user_online: {e}")
        return False
    finally:
        connection.close()


def cleanup_stale_users(threshold_minutes=5):
    """
    ★ جدید: کاربرانی که مدت‌ها غیرفعال بودند رو آفلاین کن
    این تابع رو در before_request صدا می‌زنیم
    """
    connection = get_connection()
    try:
        threshold = (
            datetime.now() - timedelta(minutes=threshold_minutes)
        ).strftime("%Y-%m-%d %H:%M:%S")

        connection.execute(
            """
            UPDATE users
            SET is_online = 0
            WHERE is_online = 1
              AND (last_seen IS NULL OR last_seen < ?)
            """,
            (threshold,)
        )
        connection.commit()
        return True
    except Exception as e:
        print(f"Error cleanup_stale_users: {e}")
        return False
    finally:
        connection.close()


def get_online_users(threshold_minutes=5):
    """لیست کاربران آنلاین (واقعی، با چک last_seen)"""
    connection = get_connection()
    try:
        threshold = (
            datetime.now() - timedelta(minutes=threshold_minutes)
        ).strftime("%Y-%m-%d %H:%M:%S")

        rows = connection.execute(
            """
            SELECT id, username, full_name, role, avatar, last_seen
            FROM users
            WHERE is_online = 1 AND last_seen >= ?
            ORDER BY last_seen DESC
            """,
            (threshold,)
        ).fetchall()

        return rows
    except Exception as e:
        print(f"Error get_online_users: {e}")
        return []
    finally:
        connection.close()


def get_last_login_and_seen(user_id):
    """دریافت آخرین ورود و آخرین فعالیت کاربر"""
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT last_login, last_seen, is_online
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()
        return row
    except Exception as e:
        print(f"Error get_last_login_and_seen: {e}")
        return None
    finally:
        connection.close()