# app.py
import mimetypes
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse

from flask import Flask, session, render_template, request, abort, jsonify
from flask_wtf.csrf import CSRFError, CSRFProtect
from config import Config
from database.init_db import init_db
from routes import (
    auth_bp, main_bp, dashboard_bp, panel_bp,
    excel_bp, documents_bp, departments_bp,
)
from routes.reports import reports_bp
from helpers.date_helper import DateHelper
from routes.profile import profile_bp
from services.users.user_service import UserService
from routes.document_group import document_group_bp
from routes.ai import assistant_bp
from routes.contractors import contractor_bp
from routes.contract_types import contract_types_bp
from routes.project_roles import project_roles_bp
from routes.projects import projects_bp
from routes.workflow import workflow_bp, notification_bp

# ============================================================
# ★ جستجوی پیشرفته
# ============================================================
from routes.search import search_bp
from routes.calendar import calendar_bp


# ============================================================
# ★ کش‌ها برای جلوگیری از اجرای زیاد
# ============================================================
_last_seen_cache = {}
_last_cleanup_time = None

#: متدهایی که تغییری ایجاد نمی‌کنند و نیازی به بررسی CSRF ندارند
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _url_host(url):
    """میزبان (host:port) یک URL را برمی‌گرداند؛ برای URL نامعتبر رشته خالی."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
    except ValueError:
        return ""
    return (parsed.netloc or "").lower()


def _is_same_origin(url, host):
    """آیا این URL به همان میزبان درخواست اشاره می‌کند؟"""
    return bool(_url_host(url)) and _url_host(url) == host.lower()


def _trusted_origins():
    """میزبان‌های اضافی مجاز (برای قرار گرفتن پشت reverse proxy)."""
    raw = os.environ.get("SSPE_TRUSTED_ORIGINS", "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def create_app():
    # Windows may register .js as text/plain, which browsers reject with nosniff.
    mimetypes.add_type("text/javascript", ".js", strict=True)
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    @app.url_defaults
    def version_javascript_assets(endpoint, values):
        if endpoint != "static":
            return

        filename = values.get("filename")
        if not isinstance(filename, str) or not filename.lower().endswith(".js"):
            return

        asset_path = os.path.join(app.static_folder, filename)
        if os.path.isfile(asset_path):
            values.setdefault("v", f"{os.path.getmtime(asset_path):.6f}")

    # ============================================================
    # ★★★ محافظت CSRF بر پایه Origin/Referer ★★★
    # ============================================================
    # همه‌ی POST/PUT/PATCH/DELETE باید از همین دامنه آمده باشند.
    # مرورگرها برای درخواست‌های cross-site همیشه Origin می‌فرستند؛
    # اگر Origin نبود از Referer استفاده می‌شود.
    # (توکن CSRF فرم‌ها هم در Flask-WTF برای فرم‌های WTForms فعال است.)
    @app.before_request
    def verify_request_origin():
        if request.method in SAFE_METHODS:
            return None

        host = request.host
        origin = request.headers.get("Origin")

        if origin:
            # Origin: null یعنی صفحه‌ای با مبدأ مبهم (file:// و…) → رد
            if origin == "null":
                abort(403)
            if not _is_same_origin(origin, host):
                if _url_host(origin) not in _trusted_origins():
                    abort(403)
            return None

        referer = request.headers.get("Referer")
        if referer and not _is_same_origin(referer, host):
            if _url_host(referer) not in _trusted_origins():
                abort(403)

        return None

    # ============================================================
    # ★ هدرهای امنیتی پاسخ‌ها
    # ============================================================
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        return response

    # ============================================================
    # ★★★ لایه دوم CSRF: توکن Flask-WTF ★★★
    # ============================================================
    # بررسی Origin بالا برای درخواست‌های cross-site کافی است، ولی توکن
    # دقیق‌تر است. این لایه بعد از بررسی Origin ثبت می‌شود تا ترتیب
    # بررسی‌ها حفظ شود. توکن در قالب‌ها با {{ csrf_token() }} و در
    # درخواست‌های AJAX با هدر X-CSRFToken فرستاده می‌شود.
    csrf = CSRFProtect()
    csrf.init_app(app)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if request.is_json:
            return jsonify({
                "ok": False,
                "error": "csrf_error",
                "message": "اعتبار درخواست منقضی شده است؛ صفحه را دوباره بارگذاری کنید.",
            }), 400
        return render_template("errors/400.html"), 400

    # ---- هشدار برای SECRET_KEY پیش‌فرض ----
    # پیام انگلیسی است تا روی کنسول‌های با کدپیج غیر UTF-8 هم خوانا بماند.
    if Config.is_default_secret():
        app.logger.warning(
            "SECRET_KEY is still the development default. "
            "Set SECRET_KEY in .env before using this app for real data."
        )

    # ============================================================
    # ★ فیلترهای جلالی برای تاریخ
    # ============================================================
    @app.template_filter("jalali_date")
    def jalali_date_filter(value):
        return DateHelper.format_jalali(value)

    @app.template_filter("jalali_datetime")
    def jalali_datetime_filter(value):
        return DateHelper.format_jalali_datetime(value, show_time=True)

    @app.template_filter("fa_digits")
    def fa_digits_filter(value):
        """نمایش اعداد با ارقام فارسی."""
        if value is None or value == "":
            return ""
        return DateHelper.to_persian_digits(value)

    # ============================================================
    # ★★★ ردیابی فعالیت کاربران (هر درخواست) ★★★
    # ============================================================
    @app.before_request
    def track_user_activity():
        """هر درخواست، فعالیت کاربر رو ثبت کن"""
        global _last_cleanup_time

        user_id = session.get("user_id")
        if not user_id:
            return

        now = datetime.now()

        # ---- ۱. به‌روزرسانی last_seen (هر ۳۰ ثانیه) ----
        last_update = _last_seen_cache.get(user_id)
        if last_update is None or (now - last_update) > timedelta(seconds=30):
            try:
                UserService.update_last_seen(user_id)
                _last_seen_cache[user_id] = now
            except Exception as e:
                print(f"Error updating last_seen: {e}")

        # ---- ۲. پاکسازی کاربران قدیمی (هر ۲ دقیقه) ----
        if _last_cleanup_time is None or (now - _last_cleanup_time) > timedelta(minutes=2):
            try:
                UserService.cleanup_stale_users(threshold_minutes=5)
                _last_cleanup_time = now
            except Exception as e:
                print(f"Error cleaning up users: {e}")

    # ============================================================
    # ★★★ Context Processor — توابع کمکی در همه قالب‌ها ★★★
    # ============================================================
    @app.context_processor
    def inject_globals():
        """تزریق متغیرهای سراسری به همه قالب‌ها"""
        from helpers.workflow import (
            can_add_note,
            can_approve_note,
            can_reject_note,
            can_edit_note,
            can_return_note,
            can_finalize_note,
            can_reopen_note,
            can_view_note,
            get_note_actions_for_user,
            is_workflow_admin,
            is_final_step,
        )
        from services.workflow import NotificationService, NoteService

        # ---- تعداد نوتیف‌های نخوانده ----
        unread_notif_count = 0
        try:
            user_id = session.get("user_id")
            if user_id:
                unread_notif_count = NotificationService.get_unread_count(user_id)
        except Exception:
            pass

        # ---- تعداد یادداشت‌های در انتظار ----
        pending_notes_count = 0
        try:
            user_id = session.get("user_id")
            if user_id:
                pending_notes_count = NoteService.get_pending_count(user_id)
        except Exception:
            pass

        return {
            # ---- Workflow permissions ----
            "can_add_note": can_add_note,
            "can_approve_note": can_approve_note,
            "can_reject_note": can_reject_note,
            "can_edit_note": can_edit_note,
            "can_return_note": can_return_note,
            "can_finalize_note": can_finalize_note,
            "can_reopen_note": can_reopen_note,
            "can_view_note": can_view_note,
            "get_note_actions_for_user": get_note_actions_for_user,
            "is_workflow_admin": is_workflow_admin,
            "is_final_step": is_final_step,

            # ---- Counters ----
            "unread_notif_count": unread_notif_count,
            "pending_notes_count": pending_notes_count,
        }

    # ============================================================
    # ★ مقداردهی اولیه دیتابیس
    # ============================================================
    init_db()

    # ============================================================
    # ★ ثبت Blueprintها
    # ============================================================
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(panel_bp)
    app.register_blueprint(excel_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(document_group_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(contractor_bp)
    app.register_blueprint(contract_types_bp)
    app.register_blueprint(project_roles_bp)
    app.register_blueprint(projects_bp)

    # ---- ★ Workflow & Notifications ----
    app.register_blueprint(workflow_bp)
    app.register_blueprint(notification_bp)

    # ============================================================
    # ★ جستجوی پیشرفته
    # ============================================================
    app.register_blueprint(search_bp)
    app.register_blueprint(calendar_bp)

    # ============================================================
    # ★ هندلرهای خطا
    # ============================================================
    @app.errorhandler(400)
    def error_400(error):
        return render_template("errors/400.html"), 400

    @app.errorhandler(401)
    def error_401(error):
        return render_template("errors/401.html"), 401

    @app.errorhandler(403)
    def error_403(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def error_404(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def error_500(error):
        if app.debug:
            raise error
        return render_template("errors/500.html"), 500

    return app


# ============================================================
# ★ اجرای مستقیم (فقط برای توسعه — برای production از gunicorn)
# ============================================================
if __name__ == "__main__":
    app = create_app()
    app.run(debug=Config.DEBUG)