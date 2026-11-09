from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    SelectField,
    SelectMultipleField,
    IntegerField,
    BooleanField,
    SubmitField,
    HiddenField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    Optional,
    NumberRange,
)
from wtforms.widgets import CheckboxInput, ListWidget


# ============================================================
# ★ ویجت checkbox list برای multi-select
# ============================================================
class MultiCheckboxField(SelectMultipleField):
    """
    فیلد multi-select با نمایش checkbox

    استفاده:
        field = MultiCheckboxField("عنوان", coerce=int, choices=[...])
    """
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


# ============================================================
# ★ فرم گروه سند
# ============================================================
class DocumentGroupForm(FlaskForm):
    """فرم ایجاد/ویرایش گروه سند"""

    title = StringField(
        "عنوان گروه",
        validators=[
            DataRequired(message="عنوان گروه الزامی است"),
            Length(
                min=2,
                max=150,
                message="عنوان باید بین ۲ تا ۱۵۰ کاراکتر باشد"
            ),
        ],
    )

    code = StringField(
        "کد گروه",
        validators=[
            Optional(),
            Length(
                max=50,
                message="کد نباید بیشتر از ۵۰ کاراکتر باشد"
            ),
        ],
    )

    color = StringField(
        "رنگ گروه",
        validators=[Optional()],
        default="#3D8499",
    )

    description = TextAreaField(
        "توضیحات",
        validators=[Optional(), Length(max=500)],
    )

    sort_order = IntegerField(
        "ترتیب نمایش",
        validators=[Optional(), NumberRange(min=0, max=9999)],
        default=0,
    )

    is_active = BooleanField(
        "گروه فعال باشد",
        default=True,
    )

    # ★ زیرگروه‌های مرتبط (M:N)
    subgroup_ids = MultiCheckboxField(
        "زیرگروه‌های این گروه",
        coerce=int,
        validators=[Optional()],
        choices=[],  # در route پر میشه
    )

    # ★ برای ارسال ترتیب زیرگروه‌ها (اختیاری)
    subgroup_sort_orders = HiddenField(
        "ترتیب زیرگروه‌ها",
        default="{}",
    )

    submit = SubmitField("ذخیره")


# ============================================================
# ★ فرم زیرگروه سند
# ============================================================
class DocumentSubgroupForm(FlaskForm):
    """فرم ایجاد/ویرایش زیرگروه سند"""

    title = StringField(
        "عنوان زیرگروه",
        validators=[
            DataRequired(message="عنوان زیرگروه الزامی است"),
            Length(
                min=2,
                max=150,
                message="عنوان باید بین ۲ تا ۱۵۰ کاراکتر باشد"
            ),
        ],
    )

    code = StringField(
        "کد زیرگروه",
        validators=[
            Optional(),
            Length(
                max=50,
                message="کد نباید بیشتر از ۵۰ کاراکتر باشد"
            ),
        ],
    )

    color = StringField(
        "رنگ زیرگروه",
        validators=[Optional()],
        default="#3D8499",
    )

    days_review = IntegerField(
        "بازه بررسی (روز)",
        validators=[
            Optional(),
            NumberRange(
                min=0,
                max=999,
                message="بازه بررسی باید بین ۰ تا ۹۹۹ روز باشد"
            ),
        ],
        default=0,
    )

    description = TextAreaField(
        "توضیحات",
        validators=[Optional(), Length(max=500)],
    )

    sort_order = IntegerField(
        "ترتیب نمایش پیش‌فرض",
        validators=[Optional(), NumberRange(min=0, max=9999)],
        default=0,
    )

    is_active = BooleanField(
        "زیرگروه فعال باشد",
        default=True,
    )

    # ============================================================
    # ★ گروه‌های مرتبط (M:N)
    # ============================================================
    group_ids = MultiCheckboxField(
        "گروه‌های این زیرگروه",
        coerce=int,
        validators=[Optional()],
        choices=[],  # در route پر میشه
    )

    # ★ برای ارسال ترتیب زیرگروه در هر گروه (اختیاری)
    group_sort_orders = HiddenField(
        "ترتیب در هر گروه",
        default="{}",
    )

    # ============================================================
    # ★ دپارتمان‌های متولی (M:N)
    #    بدون دپارتمان اصلی — همه یکسان
    # ============================================================
    department_ids = MultiCheckboxField(
        "دپارتمان‌های متولی",
        coerce=int,
        validators=[Optional()],
        choices=[],  # در route پر میشه
    )

    submit = SubmitField("ذخیره")