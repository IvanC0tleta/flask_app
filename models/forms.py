from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, PasswordField, DateField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[Email("Некорректный email")])
    psw = PasswordField("Пароль", validators=[DataRequired(), Length(min=4, max=100, message="От 4 до 100 символов")])
    remember = BooleanField("Запомнить", default=False)
    submit = SubmitField("Войти")


class RegisterForm(FlaskForm):
    name = StringField("ФИО ", validators=[Length(min=2, max=100, message="От 2 до 100 символов")])
    birth = DateField("Дата рождения ", validators=[])
    city = StringField("Город ", validators=[Length(min=2, max=100, message="От 2 до 100 символов")])
    email = StringField("Email ", validators=[Email("Некорректный email")])
    psw = PasswordField("Пароль ", validators=[DataRequired(), Length(min=4, max=100, message="От 4 до 100 символов")])
    psw2 = PasswordField("Повторите пароль ", validators=[DataRequired(), EqualTo('psw', message="Пароли не совпадают")])
    submit = SubmitField("Зарегистрироваться")


