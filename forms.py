import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField,\
                    BooleanField, validators
from wtforms.validators import StopValidation
from models import User


def login_content_validator(form, field):
    login = field.data

    if re.search(r'[^a-zA-Z0-9_]', login) is not None:
        raise StopValidation(message=('Only letters, digits and '
                                      'underscore are allowed'))

    if User.get_by(login=login.encode()):
        raise StopValidation(message=('Login already taken'))


def password_content_validator(form, field):
    password = field.data

    bad_char = re.search(r'[^a-zA-Z0-9_$&+,:;=?@#|<>.*()%!-]', password)
    if bad_char:
        raise StopValidation(message=("Only letters, digits and "
                                      "symbols are allowed"))


class RegisterForm(FlaskForm):
    login = \
        StringField('Login',
                    validators=[validators.DataRequired(),
                                login_content_validator,
                                validators.Length(max=20,
                                                  message=("Login can't be "
                                                           "longer than "
                                                           "%(max)d "
                                                           "characters"))])

    password = \
        PasswordField('Password',
                      validators=[validators.DataRequired(),
                                  validators.Length(min=8,
                                                    message=("Password can't "
                                                             "be shorter than "
                                                             "%(min)d "
                                                             "characters")),
                                  validators.Length(max=127,
                                                    message=("Password can't "
                                                             "be longer than "
                                                             "%(max)d "
                                                             "characters")),
                                  password_content_validator])

    confirm_password = \
        PasswordField('Confirm password',
                      validators=[validators.DataRequired(),
                                  validators.EqualTo('password',
                                                     message=("Passwords must "
                                                              "match"))])

    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    login = StringField('Login', validators=[validators.DataRequired()])
    password = PasswordField('Password',
                             validators=[validators.DataRequired()])

    remember_me = BooleanField('Remember me')
    submit = SubmitField('Sign in')
