# This file is part of the hydraChess project.
# Copyright (C) 2019-2020 Anton Dobrynin <hashlib@yandex.ru>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


from io import BytesIO
import imghdr
import re
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField,\
                    BooleanField, validators
from wtforms.validators import StopValidation
from hydraChess.models import User


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


def image_content_validator(form, field):
    image = field.data
    raw_img = BytesIO(image.read())
    if imghdr.what(raw_img) is None:
        raise StopValidation(message=("Can't read image data"))


class RegisterForm(FlaskForm):
    login = \
        StringField('Login',
                    validators=[validators.DataRequired(),
                                login_content_validator,
                                validators.Length(min=3,
                                                  message=("Login can't be "
                                                           "shorter than "
                                                           "%(min)d "
                                                           "characters")),
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


class SettingsForm(FlaskForm):
    image = FileField('Profile image',
                      validators=[FileRequired(),
                                  FileAllowed(['jpg', 'png', 'jpeg'],
                                              ('Only .png, .jpg, .jpeg '
                                               ' images are allowed')),
                                  image_content_validator])
    submit = SubmitField('Update settings')
