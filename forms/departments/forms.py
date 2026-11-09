from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class DepartmentForm(FlaskForm):
    title = StringField(
        "عنوان دپارتمان",
        validators=[
            DataRequired(),
            Length(min=2, max=150)
        ]
    )
    code = StringField(
        "کد دپارتمان",
        validators=[
            Optional(),
            Length(max=100)
        ]
    )
    sort_order = IntegerField(
        "ترتیب نمایش",
        default=0,
        validators=[
            Optional(),
            NumberRange(min=0)
        ]
    )
    supervisor_id = SelectField(
        "سرپرست دپارتمان",
        coerce=int,
        choices=[(0, "بدون سرپرست")],
        validators=[Optional()]
    )
    is_active = BooleanField(
        "دپارتمان فعال باشد",
        default=True
    )
    submit = SubmitField("ذخیره")