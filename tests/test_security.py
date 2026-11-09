"""تست‌های امنیتی — رمز عبور، CSRF و جدول‌های دستیار.

هدف: قفل‌کردن رفتار امن جدید تا در تغییرات بعدی بی‌سروصدا برنگردد.
"""

import hashlib

import pytest

from security.passwords import (
    hash_password,
    is_legacy_hash,
    needs_rehash,
    verify_password,
)


# ============================================================
# ★ هش رمز عبور
# ============================================================
def test_new_hash_is_salted_and_modern():
    first = hash_password("Secret123!")
    second = hash_password("Secret123!")

    assert first.startswith("scrypt:")
    assert first != second, "هش بدون نمک است — دو هش یکسان نباید باشند"
    assert verify_password(first, "Secret123!")
    assert not verify_password(first, "wrong-password")


def test_legacy_sha256_is_still_accepted():
    legacy = hashlib.sha256("admin123".encode("utf-8")).hexdigest()

    assert is_legacy_hash(legacy)
    assert verify_password(legacy, "admin123")
    assert not verify_password(legacy, "ADMIN123")
    assert needs_rehash(legacy)


def test_modern_hash_does_not_need_rehash():
    assert not needs_rehash(hash_password("x"))


@pytest.mark.parametrize("stored,raw", [(None, "x"), ("", "x"), ("garbage", "x"), ("x", None)])
def test_invalid_hash_inputs_fail_closed(stored, raw):
    assert verify_password(stored, raw) is False


# ============================================================
# ★ ارتقای خودکار هش در ورود
# ============================================================
def test_login_upgrades_legacy_hash(app_instance):
    from database.connection import get_connection
    from database.users import authenticate_user

    username = "legacy_user_for_test"
    legacy = hashlib.sha256("oldpass123".encode("utf-8")).hexdigest()

    connection = get_connection()
    try:
        connection.execute(
            """
            INSERT INTO users (username, password, full_name, role, is_active)
            VALUES (?, ?, ?, 'expert', 1)
            """,
            (username, legacy, "Legacy User"),
        )
        connection.commit()
    finally:
        connection.close()

    assert authenticate_user(username, "wrongpass") is None

    user = authenticate_user(username, "oldpass123")
    assert user is not None

    connection = get_connection()
    try:
        stored = connection.execute(
            "SELECT password FROM users WHERE username = ?", (username,)
        ).fetchone()["password"]
    finally:
        connection.close()

    assert stored.startswith("scrypt:"), "هش قدیمی پس از ورود ارتقا نیافت"
    assert verify_password(stored, "oldpass123")


# ============================================================
# ★ CSRF — بررسی Origin/Referer
# ============================================================
def test_cross_site_post_is_rejected(client):
    response = client.post(
        "/auth/login",
        data={"username": "someone", "password": "whatever"},
        headers={"Origin": "http://evil.example"},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_null_origin_post_is_rejected(client):
    response = client.post(
        "/auth/login",
        data={"username": "someone", "password": "whatever"},
        headers={"Origin": "null"},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_same_origin_post_passes_origin_check(client):
    response = client.post(
        "/auth/login",
        data={"username": "someone", "password": "whatever"},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    assert response.status_code != 403


def test_get_requests_are_not_affected(client):
    assert client.get("/auth/login", headers={"Origin": "http://evil.example"}).status_code == 200


# ============================================================
# ★ هدرهای امنیتی
# ============================================================
def test_security_headers_are_present(client):
    response = client.get("/auth/login")

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ============================================================
# ★ لایه دوم CSRF — توکن Flask-WTF
# ============================================================
def _csrf_token_from_login(client):
    import re

    html = client.get("/auth/login").get_data(as_text=True)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert match, "توکن CSRF در فرم ورود پیدا نشد"
    return match.group(1)


def test_form_post_without_token_is_rejected(app_instance, client, monkeypatch):
    monkeypatch.setitem(app_instance.config, "WTF_CSRF_ENABLED", True)

    response = client.post(
        "/auth/login",
        data={"username": "someone", "password": "whatever"},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_form_post_with_token_is_accepted(app_instance, client, monkeypatch):
    monkeypatch.setitem(app_instance.config, "WTF_CSRF_ENABLED", True)

    token = _csrf_token_from_login(client)
    response = client.post(
        "/auth/login",
        data={"username": "someone", "password": "whatever", "csrf_token": token},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    assert response.status_code != 400


def test_json_post_without_token_is_rejected(app_instance, client, monkeypatch):
    monkeypatch.setitem(app_instance.config, "WTF_CSRF_ENABLED", True)

    with client.session_transaction() as session:
        session["user_id"] = 1

    response = client.post("/assistant/ask", json={"question": "چند سند داریم؟"})
    assert response.status_code == 400


def test_json_post_with_header_token_is_accepted(app_instance, client, monkeypatch):
    monkeypatch.setitem(app_instance.config, "WTF_CSRF_ENABLED", True)

    token = _csrf_token_from_login(client)
    with client.session_transaction() as session:
        session["user_id"] = 1

    response = client.post(
        "/assistant/ask",
        json={"question": "چند سند داریم؟"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200
    assert response.get_json()["meta"]["intent"] != ""


def test_csrf_meta_tag_is_rendered(client):
    html = client.get("/auth/login").get_data(as_text=True)
    assert 'name="csrf-token"' in html


# ============================================================
# ★ جدول‌های دستیار (لاگ و بازخورد)
# ============================================================
def test_assistant_tables_exist(app_instance):
    from database.connection import get_connection

    connection = get_connection()
    try:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        connection.close()

    assert "assistant_logs" in names
    assert "assistant_feedback" in names


def test_feedback_is_persisted(client):
    from database.connection import get_connection

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["role"] = "admin"

    response = client.post(
        "/assistant/feedback",
        json={
            "question": "چند سند داریم؟",
            "answer": "۷۰۰۰",
            "rating": "up",
            "comment": "دقیق بود",
        },
    )
    assert response.status_code == 200
    assert response.get_json()["ok"] is True

    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT rating, comment FROM assistant_feedback ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        connection.close()

    assert row is not None
    assert row["rating"] == "up"
    assert row["comment"] == "دقیق بود"
