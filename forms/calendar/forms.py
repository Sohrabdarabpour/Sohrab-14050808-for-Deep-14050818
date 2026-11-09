"""فرم‌های تقویم کاری."""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError

from helpers.date_helper import DateHelper

KIND_CHOICES = [
    ("official", "تعطیل رسمی"),
    ("company", "تعطیل سازمانی"),
    ("other", "سایر"),
]


class HolidayForm(FlaskForm):
    """افزودن تعطیلی به تقویم."""

    holiday_date = StringField(
        "تاریخ شمسی",
        validators=[DataRequired(), Length(max=10)],
        description="نمونه: ۱۴۰۵/۰۱/۰۱",
    )
    title = StringField(
        "عنوان",
        validators=[DataRequired(), Length(max=120)],
    )
    kind = SelectField(
        "نوع",
        choices=KIND_CHOICES,
        default="official",
    )
    submit = SubmitField("افزودن")

    def validate_holiday_date(self, field):
        if DateHelper.parse_jalali_date(field.data) is None:
            raise ValidationError("تاریخ شمسی نامعتبر است (نمونه: ۱۴۰۵/۰۱/۰۱).")
