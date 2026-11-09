from functools import wraps
from flask import session, redirect, url_for, abort


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped_view


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth.login"))

            if session.get("role") not in roles:
                abort(403)  # ← Flask خودش می‌ره سراغ errors/403.html

            return view(*args, **kwargs)
        return wrapped_view
    return decorator