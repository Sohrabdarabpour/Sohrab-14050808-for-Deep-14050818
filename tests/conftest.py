"""تنظیمات مشترک تست‌ها.

هدف: تست‌ها هرگز به دیتابیس واقعی (instance/database.db) دست نزنند.
یک کپی موقت از دیتابیس ساخته می‌شود و مسیر آن به Config داده می‌شود،
چون database/connection.py مقدار Config.DATABASE_PATH را در زمان فراخوانی می‌خواند.
"""

import os
import shutil
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

REAL_DB = os.path.join(PROJECT_ROOT, "instance", "database.db")


@pytest.fixture(scope="session")
def app_instance(tmp_path_factory):
    """اپلیکیشن Flask با دیتابیس موقت."""
    if not os.path.exists(REAL_DB):
        pytest.skip("instance/database.db یافت نشد؛ تست نیاز به دیتابیس دارد")

    tmp_db = str(tmp_path_factory.mktemp("db") / "test.db")
    shutil.copyfile(REAL_DB, tmp_db)

    import config

    config.Config.DATABASE_PATH = tmp_db
    config.Config.TESTING = True

    from app import create_app

    application = create_app()
    # CSRF در تست‌ها خاموش است تا تست‌های دامنه‌ای به توکن نیاز نداشته باشند؛
    # tests/test_security.py عمداً آن را روشن می‌کند و مسیر واقعی را می‌سنجد.
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application


@pytest.fixture()
def client(app_instance):
    """کلاینت تست Flask."""
    return app_instance.test_client()
