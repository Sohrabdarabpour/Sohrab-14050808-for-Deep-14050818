from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class PackageForm(FlaskForm):
    subject = StringField("موضوع نامه", validators=[DataRequired(), Length(max=250)])
    date_received = StringField("تاریخ دریافت", validators=[Optional()], description="مثال: 1405/01/01")
    
    source_type = SelectField("منبع سند", choices=[
        ("contractor", "پیمانکار"),
        ("client", "کارفرما"),
        ("internal", "داخلی"),
        ("other", "سایر")
    ])
    
    sender_name = StringField("نام فرستنده", validators=[Optional(), Length(max=100)])
    sender_ref_no = StringField("شماره نامه فرستنده", validators=[Optional(), Length(max=100)])
    contract_number = StringField("شماره قرارداد", validators=[Optional(), Length(max=100)])
    
    priority = SelectField("اولویت", choices=[
        ("low", "کم"),
        ("normal", "معمولی"),
        ("high", "بالا"),
        ("urgent", "فوری")
    ], default="normal")
    
    group_id = SelectField("گروه سند", coerce=int)
    subgroup_id = SelectField("زیرگروه سند", coerce=int)
    
    contractor_id = SelectField("پیمانکار", coerce=int)
    project_id = SelectField("پروژه", coerce=int)

    submit = SubmitField("ثبت سند")