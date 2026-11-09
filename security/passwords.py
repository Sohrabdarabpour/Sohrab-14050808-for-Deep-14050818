"""هش کردن و بررسی رمز عبور.

سازگاری با نسخه‌های قبلی
------------------------
نسخه‌های قدیمی برنامه رمزها را با ``SHA-256`` بدون نمک ذخیره می‌کردند.
این ماژول:

* برای رمزهای جدید از ``scrypt`` (Werkzeug) استفاده می‌کند؛
* رمزهای قدیمی ``SHA-256`` را هنوز می‌پذیرد تا کاربران فعلی قفل نشوند؛
* با :func:`needs_rehash` مشخص می‌کند هش باید بعد از ورود موفق ارتقا یابد.

بنابراین مهاجرت **تدریجی و بدون قطعی** انجام می‌شود: هر کاربر در اولین
ورود بعدی‌اش به‌طور خودکار به scrypt منتقل می‌شود.
"""

import hashlib
import hmac

from werkzeug.security import check_password_hash, generate_password_hash

#: الگوریتم پیش‌فرض رمزهای جدید
DEFAULT_METHOD = "scrypt"

#: پیشوندهایی که نشان می‌دهند هش با یک الگوریتم امن و نمک‌دار ساخته شده است
MODERN_PREFIXES = ("scrypt:", "pbkdf2:", "argon2")


def hash_password(password):
    """ساخت هش امن (نمک‌دار) برای رمز عبور."""
    if password is None:
        raise ValueError("password must not be None")
    return generate_password_hash(str(password), method=DEFAULT_METHOD)


def _legacy_sha256(password):
    """هش قدیمی برنامه — فقط برای بررسی رمزهای موجود."""
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()


def is_legacy_hash(stored_hash):
    """آیا این هش با روش قدیمی (SHA-256 بدون نمک) ساخته شده است؟"""
    if not stored_hash:
        return False
    value = str(stored_hash).strip()
    if value.startswith(MODERN_PREFIXES):
        return False
    # هش SHA-256 هگزادسیمال و ۶۴ کاراکتری است
    return len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)


def verify_password(stored_hash, password):
    """بررسی رمز در برابر هش ذخیره‌شده (هم مدرن و هم قدیمی)."""
    if not stored_hash or password is None:
        return False

    value = str(stored_hash).strip()

    if value.startswith(MODERN_PREFIXES):
        try:
            return check_password_hash(value, str(password))
        except (ValueError, TypeError):
            return False

    if is_legacy_hash(value):
        return hmac.compare_digest(value, _legacy_sha256(password))

    return False


def needs_rehash(stored_hash):
    """آیا هش باید بعد از ورود موفق با الگوریتم جدید بازسازی شود؟"""
    return not str(stored_hash or "").strip().startswith(MODERN_PREFIXES)
