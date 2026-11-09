"""تست دود (smoke) — سلامت کلی برنامه پس از هر تغییر ساختاری.

اجرا:
    pytest
یا فقط این فایل:
    pytest tests/test_smoke.py -v
"""

import os

EXPECTED_BLUEPRINTS = {
    "assistant",
    "auth",
    "calendar",
    "contract_types",
    "contractors",
    "dashboard",
    "departments",
    "document_group",
    "documents",
    "excel",
    "main",
    "notifications",
    "panel",
    "profile",
    "project_roles",
    "projects",
    "reports",
    "search",
    "workflow",
}

MIN_EXPECTED_ROUTES = 150

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "templates")


def test_all_blueprints_registered(app_instance):
    assert set(app_instance.blueprints) == EXPECTED_BLUEPRINTS


def test_route_count(app_instance):
    rules = list(app_instance.url_map.iter_rules())
    assert len(rules) >= MIN_EXPECTED_ROUTES, f"only {len(rules)} routes registered"


def test_login_page_renders(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert "html" in response.data.decode("utf-8", "ignore").lower()


def test_javascript_static_files_have_executable_mime_type(client):
    response = client.get("/static/js/app.js")

    assert response.status_code == 200
    assert response.mimetype == "text/javascript"


def test_javascript_urls_are_versioned(client):
    response = client.get("/auth/login")
    html = response.data.decode("utf-8")

    assert "/static/js/app.js?v=" in html
    assert "/static/js/pages/login.js?v=" in html


def test_root_redirects_to_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "login" in response.headers.get("Location", "").lower()


def test_protected_pages_redirect_anonymous(client):
    for path in ("/dashboard/", "/search/"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302, f"{path} should redirect anonymous users"


def test_unknown_url_returns_404(client):
    assert client.get("/this-url-does-not-exist").status_code == 404


def test_all_templates_compile(app_instance):
    broken = []
    for root, _dirs, files in os.walk(TEMPLATE_DIR):
        for name in files:
            if not name.endswith(".html"):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, TEMPLATE_DIR).replace("\\", "/")
            try:
                with open(full, "r", encoding="utf-8") as handle:
                    app_instance.jinja_env.from_string(handle.read())
            except Exception as exc:  # noqa: BLE001 - گزارش همه خطاها
                broken.append(f"{rel}: {exc}")
    assert not broken, "template errors:\n" + "\n".join(broken)


def test_no_duplicate_copy_files():
    """هیچ فایل تکراری با نام 'copy' نباید داخل کد پروژه بماند."""
    offenders = []
    for folder in ("routes", "services", "forms", "helpers", "templates", "static"):
        for root, _dirs, files in os.walk(os.path.join(PROJECT_ROOT, folder)):
            for name in files:
                lowered = name.lower()
                if " copy" in lowered or lowered.endswith(("- copy.py", " copy.html")):
                    offenders.append(os.path.join(root, name))
    assert not offenders, "duplicate files found:\n" + "\n".join(offenders)
