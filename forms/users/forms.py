from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Optional

USER_ROLES = [
    ("expert", "کارشناس"),
    ("supervisor", "سرپرست"),
    ("manager", "مدیر"),
    ("admin", "مدیر نرم افزار")
]

GENDER_CHOICES = [
    ("male", "آقا"),
    ("female", "خانم"),
]


class UserForm(FlaskForm):
    username = StringField(
        "نام کاربری",
        validators=[DataRequired(), Length(min=3, max=50)]
    )
    password = PasswordField(
        "رمز عبور",
        validators=[Optional(), Length(min=4, max=100)]
    )
    full_name = StringField(
        "نام و نام خانوادگی",
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    role = SelectField(
        "نقش",
        choices=USER_ROLES,
        validators=[DataRequired()]
    )
    department_id = SelectField(
        "دپارتمان",
        coerce=int,
        choices=[(0, "بدون دپارتمان")],
        validators=[Optional()]
    )

    # ★ فیلدهای جدید
    gender = SelectField(
        "جنسیت",
        choices=GENDER_CHOICES,
        validators=[Optional()]
    )
    is_active = BooleanField(
        "کاربر فعال باشد",
        default=True
    )

    submit = SubmitField("ذخیره")


class UserRoleForm(FlaskForm):
    role = SelectField(
        "نقش",
        choices=USER_ROLES,
        validators=[DataRequired()]
    )
    submit = SubmitField("ذخیره نقش")