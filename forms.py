import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField,\
                    BooleanField, validators
from wtforms.validators import StopValidation
from models import db, User


def login_content_validator(form, field):
    login = field.data

    if re.search(r'[^a-zA-Z0-9_]', login) is not None:
        raise StopValidation(message=('The login can only consist of '
                                      'letters (a-z, A-Z), digits (0-9) '
                                      'and underscore (_)'))

    if db.session.query(User).filter(User.login == login).first() is not None:
        raise StopValidation(message=('Login already taken'))


def password_content_validator(form, field):
    password = field.data

    bad_char = re.search(r'[^a-zA-Z0-9_$&+,:;=?@#|<>.*()%!-]', password)
    if bad_char:
        raise StopValidation(message=(f"Character ({bad_char.group(0)}) "
                                      "can't be used in your password"))


class RegisterForm(FlaskForm):
    login = StringField(
                'Login',
                validators=[validators.DataRequired(),
                            login_content_validator,
                            validators.Length(max=20,
                                              message=("Login can't be "
                                                       "longer than "
                                                       "%(max)d characters"))])

    password = PasswordField(
                'Password',
                validators=[validators.DataRequired(),
                            validators.Length(min=8,
                                              max=127,
                                              message=("Password must "
                                                       "be between %(min)d "
                                                       "and %(max)d "
                                                       "characters long")),
                            password_content_validator,
                            validators.EqualTo('confirm_password',
                                               message="Passwords must match")])

    confirm_password = PasswordField('Confirm password',
                                     validators=[validators.DataRequired()])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    login = StringField('Login', validators=[validators.DataRequired()])
    password = PasswordField('Password',
                             validators=[validators.DataRequired()])

    remember_me = BooleanField('Remember me')
    submit = SubmitField('Sign in')
