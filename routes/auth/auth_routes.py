from flask import Blueprint, render_template, redirect, url_for, session, flash
from forms.auth.forms import LoginForm, ChangePasswordForm
from services.users.user_service import UserService
from security.decorators import login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ============================================================
# ورود
# ============================================================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("main.index"))

    form = LoginForm()

    if form.validate_on_submit():
        user = UserService.authenticate(form.username.data, form.password.data)

        if user:
            session.clear()
            # ★ نشست ۱۲ ساعته (PERMANENT_SESSION_LIFETIME در config.py)
            session.permanent = True

            # ★ تبدیل به dict اگر sqlite3.Row است (برای استفاده از .get)
            if not isinstance(user, dict):
                user = dict(user)

            # ★ ذخیره اطلاعات پایه
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]

            # ★ آواتار و جنسیت
            avatar = user.get("avatar")
            gender = user.get("gender") or "male"

            # ★ اگر آواتار پیش‌فرض یا خالی بود، بر اساس جنسیت تنظیم کن
            default_avatars = {
                "default.png",
                "default-profile-male.png",
                "default-profile-female.png",
                None,
                "",
            }
            if avatar in default_avatars:
                if gender == "female":
                    avatar = "default-profile-female.png"
                else:
                    avatar = "default-profile-male.png"

            session["avatar"] = avatar
            session["gender"] = gender

            # ★ دپارتمان
            if user.get("department_id"):
                session["department_id"] = user["department_id"]

            flash("ورود با موفقیت انجام شد", "success")

            # ★★★ ریدایرکت هوشمند بر اساس نقش ★★★
            if user["role"] == "supervisor":
                department_id = user.get("department_id")

                if department_id:
                    return redirect(url_for(
                        "departments.view_department",
                        department_id=department_id
                    ))

            # بقیه نقش‌ها → main.index
            return redirect(url_for("main.index"))

        flash("نام کاربری یا رمز عبور اشتباه است", "danger")

    return render_template("login.html", form=form)
# ============================================================
# خروج
# ============================================================
# @auth_bp.route("/logout")
# @login_required
# def logout():
#     user_id = session.get("user_id")
#     if user_id:
#         UserService.set_offline(user_id)

#     session.clear()
#     flash("با موفقیت از حساب کاربری خارج شدید", "success")
#     return redirect(url_for("auth.login"))

@auth_bp.route("/logout")
@login_required
def logout():
    user_id = session.get("user_id")
    if user_id:
        UserService.set_offline(user_id)

    session.clear()
    flash("با موفقیت از حساب کاربری خارج شدید", "success")

    # ★ صفحه‌ای که localStorage رو پاک می‌کنه بعد redirect به login
    return render_template("auth/logout.html")


# ============================================================
# تغییر رمز عبور
# ============================================================
@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        user = UserService.authenticate(
            session.get("username"),
            form.current_password.data
        )

        if not user:
            flash("رمز عبور فعلی اشتباه است", "danger")
            return render_template("change_password.html", form=form)

        if form.new_password.data != form.confirm_password.data:
            flash("رمز عبور جدید و تکرار آن یکسان نیستند", "danger")
            return render_template("change_password.html", form=form)

        success = UserService.change_password(
            session["user_id"],
            form.new_password.data
        )

        if success:
            flash("رمز عبور با موفقیت تغییر کرد", "success")
            return redirect(url_for("main.index"))

        flash("خطا در تغییر رمز عبور", "danger")

    return render_template("change_password.html", form=form)