"""
فرم نت — ساختار فیلدها و اعتبارسنجی
"""


class NoteForm:
    """فرم ثبت و ویرایش نت"""

    # ============================================================
    # ★ فیلدهای فرم
    # ============================================================
    FIELDS = [
        {
            "name": "content",
            "label": "متن نت",
            "type": "textarea",
            "required": True,
            "rows": 5,
            "icon": "fa-note-sticky",
            "placeholder": "نت خود را اینجا بنویسید...",
            "help": "این نت برای بررسی به مرحله بعد ارسال می‌شود",
        },
    ]

    # ============================================================
    # ★ اقدامات گردش‌کار
    # ============================================================
    ACTIONS = {
        "approve": {
            "title": "تایید و ارسال به مرحله بعد",
            "icon": "fa-circle-check",
            "color": "#16a34a",
            "confirm": "آیا از تایید این نت مطمئن هستید؟",
            "requires_reason": False,
        },
        "reject": {
            "title": "رد و برگشت به کارشناس",
            "icon": "fa-circle-xmark",
            "color": "#dc2626",
            "confirm": "آیا از رد این نت مطمئن هستید؟",
            "requires_reason": True,
        },
        "edit": {
            "title": "ویرایش نت",
            "icon": "fa-pen",
            "color": "#f59e0b",
            "confirm": None,
            "requires_reason": False,
        },
        "return": {
            "title": "برگشت به مرحله قبلی",
            "icon": "fa-rotate-left",
            "color": "#0891b2",
            "confirm": "آیا از برگشت این نت مطمئن هستید؟",
            "requires_reason": True,
        },
        "finalize": {
            "title": "خاتمه و تایید نهایی",
            "icon": "fa-flag-checkered",
            "color": "#7c3aed",
            "confirm": "آیا از خاتمه این نت مطمئن هستید؟",
            "requires_reason": False,
        },
    }

    # ============================================================
    # ★ API
    # ============================================================
    @classmethod
    def get_fields(cls):
        return cls.FIELDS

    @classmethod
    def get_actions(cls):
        return cls.ACTIONS

    @classmethod
    def get_action(cls, action_code):
        return cls.ACTIONS.get(action_code)

    @classmethod
    def empty_data(cls):
        """داده‌های خالی برای فرم جدید"""
        return {f["name"]: "" for f in cls.FIELDS}

    @classmethod
    def from_model(cls, note):
        """تبدیل رکورد دیتابیس به داده فرم"""
        if not note:
            return cls.empty_data()
        return {
            f["name"]: note.get(f["name"], "")
            for f in cls.FIELDS
        }

    # ============================================================
    # ★ اعتبارسنجی
    # ============================================================
    @staticmethod
    def validate(data):
        """اعتبارسنجی داده‌های فرم"""
        errors = {}

        content = (data.get("content") or "").strip()
        if not content:
            errors["content"] = "متن نت الزامی است"
        elif len(content) < 3:
            errors["content"] = "متن نت باید حداقل ۳ کاراکتر باشد"
        elif len(content) > 5000:
            errors["content"] = "متن نت نباید بیشتر از ۵۰۰۰ کاراکتر باشد"

        return errors

    # ============================================================
    # ★ اعتبارسنجی دلیل (برای رد و برگشت)
    # ============================================================
    @staticmethod
    def validate_reason(reason, required=False):
        """اعتبارسنجی دلیل رد/برگشت"""
        reason = (reason or "").strip()

        if required and not reason:
            return "وارد کردن دلیل الزامی است"

        if len(reason) > 1000:
            return "دلیل نباید بیشتر از ۱۰۰۰ کاراکتر باشد"

        return None