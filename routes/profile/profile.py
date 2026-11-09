# routes/profile/profile.py

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    session,
    jsonify
)
import os
import time
from werkzeug.utils import secure_filename
from routes.profile import profile_bp
from security.decorators import role_required
from services.profile.profile_service import ProfileService
from services.users.avatar_service import AvatarService


# ============================================
# پسوندهای مجاز و حداکثر حجم
# ============================================
ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
MAX_AVATAR_SIZE = 5 * 1024 * 1024   # 5MB
DEFAULT_AVATAR = "default.png"


# ============================================
# توابع کمکی
# ============================================
def _row_get(row, key, default=None):
    """دریافت امن مقدار از sqlite3.Row یا dict یا آبجکت."""
    if row is None:
        return default
    try:
        keys = row.keys()
        if key in keys:
            return row[key]
        return default
    except (AttributeError, IndexError):
        pass
    try:
        return row.get(key, default)
    except AttributeError:
        pass
    try:
        return getattr(row, key, default)
    except Exception:
        return default


def _is_ajax():
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _get_upload_folder():
    folder = os.path.join(
        current_app.root_path,
        "static", "uploads", "avatar"
    )
    os.makedirs(folder, exist_ok=True)
    return folder


def _delete_avatar_file(filename):
    """حذف فایل آواتار از دیسک (به‌جز پیش‌فرض‌ها)."""
    default_avatars = {
        "default.png",
        "default-profile-male.png",
        "default-profile-female.png",
    }
    if not filename or filename in default_avatars:
        return
    filepath = os.path.join(_get_upload_folder(), filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            current_app.logger.warning(f"Could not delete avatar: {e}")


def _json_error(message, status=400):
    return jsonify({"success": False, "message": message}), status


# ============================================
# Route اصلی پروفایل
# ============================================
@profile_bp.route("/", methods=["GET", "POST"])
@role_required("admin", "manager", "supervisor", "expert")
def profile():

    user_id = session.get("user_id")
    if not user_id:
        flash("ابتدا وارد شوید", "danger")
        return redirect(url_for("auth.login"))

    # ============================================
    # POST
    # ============================================
    if request.method == "POST":
        action = request.form.get("action")

        # --------------------------------------------
        # ۱) بروزرسانی اطلاعات پروفایل
        # --------------------------------------------
        if action == "update":
            full_name = (request.form.get("full_name") or "").strip()
            email = (request.form.get("email") or "").strip() or None
            phone = (request.form.get("phone") or "").strip() or None
            position = (request.form.get("position") or "").strip() or None
            national_code = (request.form.get("national_code") or "").strip() or None
            gender = (request.form.get("gender") or "").strip() or None

            # ★ اعتبارسنجی جنسیت
            if gender not in ("male", "female"):
                gender = "male"

            # ★ اعتبارسنجی سرور
            errors = []
            if len(full_name) < 3:
                errors.append("نام باید حداقل ۳ کاراکتر باشد")

            if email and ("@" not in email or "." not in email):
                errors.append("ایمیل معتبر نیست")

            if phone and not (
                phone.isdigit()
                and len(phone) == 11
                and phone.startswith("09")
            ):
                errors.append("شماره تماس باید ۱۱ رقم و با ۰۹ شروع شود")

            if national_code and not (
                national_code.isdigit() and len(national_code) == 10
            ):
                errors.append("کد ملی باید ۱۰ رقم باشد")

            if errors:
                for err in errors:
                    flash(err, "danger")
                return redirect(url_for("profile.profile"))

            success = ProfileService.update_profile(
                user_id=user_id,
                full_name=full_name,
                email=email,
                phone=phone,
                position=position,
                national_code=national_code,
                gender=gender,
            )

            if success:
                session['full_name'] = full_name
                session['gender'] = gender
                session.modified = True

                # ★ به‌روزرسانی آواتار در سشن (اگر عوض شده باشد)
                updated_user = ProfileService.get_profile(user_id)
                if updated_user:
                    new_avatar = _row_get(updated_user, 'avatar')
                    if new_avatar:
                        session['avatar'] = new_avatar
                        session.modified = True

                flash("اطلاعات پروفایل بروزرسانی شد", "success")
            else:
                flash("خطا در ذخیره اطلاعات", "danger")

            return redirect(url_for("profile.profile"))

        # --------------------------------------------
        # ۲) تغییر رمز عبور
        # --------------------------------------------
        if action == "password":
            old_password = request.form.get("old_password") or ""
            new_password = request.form.get("new_password") or ""
            confirm_password = request.form.get("confirm_password") or ""

            if not old_password:
                flash("رمز فعلی را وارد کنید", "danger")
                return redirect(url_for("profile.profile"))

            if len(new_password) < 8:
                flash("رمز جدید باید حداقل ۸ کاراکتر باشد", "danger")
                return redirect(url_for("profile.profile"))

            if new_password != confirm_password:
                flash("رمز جدید و تکرار آن یکسان نیستند", "danger")
                return redirect(url_for("profile.profile"))

            if new_password == old_password:
                flash("رمز جدید نباید با رمز فعلی یکسان باشد", "warning")
                return redirect(url_for("profile.profile"))

            result = ProfileService.change_password(
                user_id=user_id,
                old_password=old_password,
                new_password=new_password
            )

            if result:
                flash("رمز عبور تغییر کرد", "success")
            else:
                flash("رمز فعلی صحیح نیست", "danger")

            return redirect(url_for("profile.profile"))

        # --------------------------------------------
        # ۳) آپلود آواتار
        # --------------------------------------------
        if action == "avatar":
            file = request.files.get("avatar")

            if not file or not file.filename:
                if _is_ajax():
                    return _json_error("فایلی برای آپلود انتخاب نشده است")
                flash("فایلی برای آپلود انتخاب نشده است", "warning")
                return redirect(url_for("profile.profile"))

            # ★ اعتبارسنجی پسوند
            original_filename = secure_filename(file.filename)
            ext = (
                original_filename.rsplit('.', 1)[-1].lower()
                if '.' in original_filename else ''
            )

            if ext not in ALLOWED_AVATAR_EXTENSIONS:
                msg = (
                    "فرمت فایل مجاز نیست. فقط PNG، JPG، JPEG، "
                    "WebP و GIF پذیرفته می‌شوند."
                )
                if _is_ajax():
                    return _json_error(msg)
                flash(msg, "danger")
                return redirect(url_for("profile.profile"))

            # ★ اعتبارسنجی حجم
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            if file_size > MAX_AVATAR_SIZE:
                msg = "حجم فایل نباید بیشتر از ۵ مگابایت باشد"
                if _is_ajax():
                    return _json_error(msg)
                flash(msg, "danger")
                return redirect(url_for("profile.profile"))

            upload_folder = _get_upload_folder()

            # ★ نام یکتا
            unique_filename = f"user_{user_id}_{int(time.time())}.{ext}"
            filepath = os.path.join(upload_folder, unique_filename)

            # ★ حذف آواتار قبلی (اگر اختصاصی بود)
            try:
                old_user = ProfileService.get_profile(user_id)
                old_avatar = _row_get(old_user, 'avatar')
                if old_avatar:
                    _delete_avatar_file(old_avatar)
            except Exception as e:
                current_app.logger.warning(f"Could not delete old avatar: {e}")

            # ★ ذخیره فایل
            file.save(filepath)

            # ★ پردازش تصویر
            try:
                AvatarService.process_avatar(filepath, filepath)
            except Exception as e:
                current_app.logger.warning(f"Avatar processing failed: {e}")

            # ★ ذخیره در دیتابیس
            ProfileService.update_avatar(user_id, unique_filename)

            # ★ سشن
            session['avatar'] = unique_filename
            session.modified = True

            if _is_ajax():
                return jsonify({
                    "success": True,
                    "avatar": unique_filename,
                    "message": "تصویر پروفایل تغییر کرد"
                })

            flash("تصویر پروفایل تغییر کرد", "success")
            return redirect(url_for("profile.profile"))

        # --------------------------------------------
        # ۴) حذف آواتار (بازگشت به پیش‌فرض بر اساس جنسیت)
        # --------------------------------------------
        if action == "remove_avatar":
            old_user = ProfileService.get_profile(user_id)
            old_avatar = _row_get(old_user, 'avatar')

            if old_avatar:
                _delete_avatar_file(old_avatar)

            # ★ حذف هوشمند — پیش‌فرض بر اساس جنسیت
            ProfileService.remove_avatar(user_id)

            # ★ به‌روزرسانی session با آواتار جدید
            user_row = ProfileService.get_profile(user_id)
            new_avatar = _row_get(user_row, 'avatar') or "default-profile-male.png"
            session['avatar'] = new_avatar
            session.modified = True

            flash("تصویر پروفایل حذف شد", "success")
            return redirect(url_for("profile.profile"))

        # --------------------------------------------
        # action ناشناخته
        # --------------------------------------------
        flash("درخواست نامعتبر", "danger")
        return redirect(url_for("profile.profile"))

    # ============================================
    # GET
    # ============================================
    user = ProfileService.get_profile(user_id)

    # ★ همگام‌سازی سشن
    if user:
        db_avatar = _row_get(user, 'avatar')
        db_full_name = _row_get(user, 'full_name')
        db_role = _row_get(user, 'role')
        db_gender = _row_get(user, 'gender')

        if db_avatar != session.get('avatar'):
            session['avatar'] = db_avatar
            session.modified = True

        if db_full_name and db_full_name != session.get('full_name'):
            session['full_name'] = db_full_name
            session.modified = True

        if db_role and db_role != session.get('role'):
            session['role'] = db_role
            session.modified = True

        # ★ همگام‌سازی جنسیت در session (برای سایدبار)
        if db_gender and db_gender != session.get('gender'):
            session['gender'] = db_gender
            session.modified = True

    return render_template(
        "profile/profile.html",
        user=user
    )