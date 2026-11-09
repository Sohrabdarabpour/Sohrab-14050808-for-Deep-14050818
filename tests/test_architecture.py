"""تست‌های معماری — قواعد ساختار پوشه‌ها را تضمین می‌کنند.

این تست‌ها جلوی خطاهایی را می‌گیرند که با چشم دیده نمی‌شوند، مثلاً:
    ماژولی در routes/ وجود دارد ولی هیچ‌جا import نمی‌شود
    (بنابراین مسیرش هرگز ثبت نمی‌شود و صفحه ۴۰۴ می‌دهد)
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROUTES_DIR = os.path.join(PROJECT_ROOT, "routes")
SERVICES_DIR = os.path.join(PROJECT_ROOT, "services")
FORMS_DIR = os.path.join(PROJECT_ROOT, "forms")
DATABASE_DIR = os.path.join(PROJECT_ROOT, "database")

# ماژول‌هایی که عمداً import نمی‌شوند
NOT_ROUTE_MODULES = {"helpers", "base"}


def _python_modules(folder):
    """همه ماژول‌های .py یک پوشه (بدون __init__)."""
    if not os.path.isdir(folder):
        return []
    return [
        name[:-3]
        for name in os.listdir(folder)
        if name.endswith(".py") and name != "__init__.py"
    ]


def test_every_route_module_is_imported(app_instance):
    """هر فایل داخل routes/ باید بعد از ساخت اپ در sys.modules باشد.

    اگر ماژولی import نشود، blueprint آن ثبت نمی‌شود و مسیرهایش ۴۰۴ می‌دهند.
    """
    missing = []
    for root, dirs, files in os.walk(ROUTES_DIR):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if not name.endswith(".py") or name == "__init__.py":
                continue
            stem = name[:-3]
            if stem in NOT_ROUTE_MODULES:
                continue
            rel_dir = os.path.relpath(root, PROJECT_ROOT).replace("\\", "/")
            module_name = f"{rel_dir.replace('/', '.')}.{stem}"
            if module_name not in sys.modules:
                missing.append(module_name)

    assert not missing, (
        "این ماژول‌های routes هیچ‌جا import نشده‌اند و مسیرهایشان ثبت نمی‌شود:\n"
        + "\n".join(sorted(missing))
    )


def test_services_are_packaged_per_entity():
    """هیچ سرویس تختی در ریشه services/ نمانده باشد."""
    flat = _python_modules(SERVICES_DIR)
    assert not flat, f"سرویس‌های بدون پوشه: {flat}"


def test_forms_are_packaged_per_entity():
    """هیچ فرم تختی در ریشه forms/ نمانده باشد."""
    flat = _python_modules(FORMS_DIR)
    assert not flat, f"فرم‌های بدون پوشه: {flat}"


def test_one_file_per_table():
    """هر جدول باید فایل جداگانه در database/tables/ داشته باشد."""
    tables_dir = os.path.join(DATABASE_DIR, "tables")
    assert os.path.isdir(tables_dir), "database/tables/ وجود ندارد"

    from database.tables import TABLES

    table_files = set(_python_modules(tables_dir))
    table_names = {module.TABLE_NAME for module in TABLES}
    assert len(TABLES) == len(table_files), f"تعداد جداول: {len(TABLES)}"
    assert table_names == table_files, (
        f"فایل‌ها و ماژول‌های جدول هم‌خوانی ندارند: "
        f"فایل‌ها={table_files}، ماژول‌ها={table_names}"
    )

    for module in TABLES:
        path = os.path.join(tables_dir, f"{module.TABLE_NAME}.py")
        assert os.path.isfile(path), f"فایل جدول پیدا نشد: {path}"
        assert module.CREATE_SQL.strip().startswith("CREATE TABLE"), module.TABLE_NAME


def test_init_db_is_thin():
    """init_db.py باید فقط هماهنگ‌کننده باشد، نه محل تعریف جداول."""
    path = os.path.join(DATABASE_DIR, "init_db.py")
    with open(path, encoding="utf-8") as handle:
        line_count = len(handle.read().splitlines())

    assert line_count < 120, (
        f"init_db.py دوباره بزرگ شده ({line_count} خط)؛ "
        "ساختار جداول باید در database/tables/ باشد"
    )


def test_static_references_resolve():
    """هر فایل CSS/JS که در قالب‌ها ارجاع داده شده باید واقعاً وجود داشته باشد."""
    import re

    ref_re = re.compile(r"filename=['\"]([^'\"]+)['\"]")
    static_dir = os.path.join(PROJECT_ROOT, "static")
    missing = set()

    for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, "templates")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if not name.endswith(".html"):
                continue
            with open(os.path.join(root, name), encoding="utf-8") as handle:
                text = handle.read()
            for match in ref_re.finditer(text):
                target = match.group(1).replace("/", os.sep)
                if not os.path.exists(os.path.join(static_dir, target)):
                    missing.add(match.group(1))

    assert not missing, "فایل‌های استاتیک گمشده:\n" + "\n".join(sorted(missing))


def test_no_inline_page_styles():
    """استایل صفحه نباید داخل قالب باشد؛ باید در static/css/pages/ باشد."""
    import re

    style_re = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
    offenders = []

    for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, "templates")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if not name.endswith(".html"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            for match in style_re.finditer(text):
                if match.group(1).count("\n") > 5:
                    offenders.append(os.path.relpath(path, PROJECT_ROOT))
                    break

    assert not offenders, "این قالب‌ها استایل داخلی دارند:\n" + "\n".join(sorted(offenders))


def test_css_is_linked_from_base():
    """ترتیب آبشاری: core → base → app-ui → components → صفحه."""
    path = os.path.join(PROJECT_ROOT, "templates", "base.html")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()

    order = [
        "css/core/variables.css",
        "css/core/reset.css",
        "css/core/utilities.css",
        "css/base/base.css",
        "css/app-ui.css",
    ]
    positions = [text.find(item) for item in order]
    assert all(p >= 0 for p in positions), "یکی از فایل‌های CSS پایه در base.html نیست"
    assert positions == sorted(positions), "ترتیب بارگذاری CSS پایه به‌هم ریخته است"

    assert "{% block styles %}" in text, "بلوک styles در base.html نیست"


# الگوهای mojibake که در فارسی واقعی هرگز پشت‌سرهم نمی‌آیند.
# وقتی UTF-8 فارسی با کدپیج cp1256 خوانده و بازنویسی شود، این‌ها ظاهر می‌شوند.
MOJIBAKE_MARKERS = ("ط¨", "ظ¾", "ع©", "غŒ", "ط§ظ", "â€Œ")


def test_source_files_are_not_mojibake():
    """فایل‌های سورس نباید متن فارسی خراب‌شده (mojibake) داشته باشند.

    این تست جلوی تکرار یک باگ واقعی را می‌گیرد: نوشتن متن فارسی با
    PowerShell (که فایل را cp1256 می‌خواند) کل توضیحات `llm_tools.py` را
    خراب کرده بود و LLM دیگر نمی‌توانست ابزار درست را انتخاب کند.
    """
    offenders = []

    for folder in ("services", "routes", "database", "forms", "helpers", "templates"):
        base = os.path.join(PROJECT_ROOT, folder)
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                if not name.endswith((".py", ".html", ".js")):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()

                hits = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
                if hits >= 3:
                    offenders.append(f"{os.path.relpath(path, PROJECT_ROOT)} ({hits} hits)")

    assert not offenders, "متن فارسی خراب‌شده (mojibake) پیدا شد:\n" + "\n".join(offenders)
