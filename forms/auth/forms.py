from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
class LoginForm(FlaskForm):
    username = StringField(
        "نام کاربری",
        validators=[DataRequired(), Length(min=3, max=50)]
    )
    password = PasswordField(
        "رمز عبور",
        validators=[DataRequired(), Length(min=4, max=100)]
    )
    submit = SubmitField("ورود")
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "رمز عبور فعلی",
        validators=[DataRequired()]
    )
    new_password = PasswordField(
        "رمز عبور جدید",
        validators=[DataRequired(), Length(min=4, max=100)]
    )
    confirm_password = PasswordField(
        "تکرار رمز عبور",
        validators=[DataRequired(), Length(min=4, max=100)]
    )
    submit = SubmitField("تغییر رمز عبور")