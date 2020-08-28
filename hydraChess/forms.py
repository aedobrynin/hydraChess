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
import re
import imghdr
from PIL import Image
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
        raise StopValidation(message=('Nickname already taken'))


def password_content_validator(form, field):
    password = field.data

    bad_char = re.search(r'[^a-zA-Z0-9_$&+,:;=?@#|<>.*()%!-]', password)
    if bad_char:
        raise StopValidation(message=("Only letters, digits and "
                                      "symbols are allowed"))

    if len(password) < 8:
        raise StopValidation(
            message="Password can't be shorter than 8 characters"
        )

    if len(password) > 127:
        raise StopValidation(
            message="Password can't be longer than 127 characters"
        )

def image_content_validator(form, field):
    image = field.data
    raw_img = BytesIO(image.read())
    if imghdr.what(raw_img) is None:
        raise StopValidation(message=("Can't read image data"))
    img = Image.open(raw_img)
    if img.width < 256 or img.height < 256:
        raise StopValidation(message=("Image size must be at least 256x256"))


class SignUpForm(FlaskForm):
    login = \
        StringField(
            'Nickname',
            validators=[
                validators.DataRequired(),
                login_content_validator,
                validators.Length(
                    min=3,
                    message="Nickname can't be shorter than %(min)d characters"
                ),
                validators.Length(
                    max=20,
                    message="Nickname can't be longer than %(max)d characters"
                )
            ]
        )

    password = \
        PasswordField(
            'Password',
            validators=[
                validators.DataRequired(),
                password_content_validator
            ]
        )

    confirm_password = \
        PasswordField(
            'Confirm password',
            validators=[
                validators.EqualTo(
                    'password',
                    message="Passwords must match"
                )
            ]
        )

    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    login = StringField('Nickname', validators=[validators.DataRequired()])
    password = PasswordField(
        'Password',
        validators=[validators.DataRequired()]
    )

    remember_me = BooleanField('Remember me')
    submit = SubmitField('Sign in')


class PictureForm(FlaskForm):
    image = \
        FileField(
            'Profile picture',
            validators=[
                FileRequired(),
                FileAllowed(
                    ['jpg', 'png', 'jpeg'],
                    'Only .png, .jpg, .jpeg images are allowed'
                ),
                image_content_validator
            ]
        )

    submit_picture = SubmitField('Update profile picture')


class ChangePasswordForm(FlaskForm):
    new_password = PasswordField(
        'New password',
        validators=[
            validators.DataRequired(),
            password_content_validator
        ]
    )

    repeat_password = PasswordField(
        'Repeat new password',
        validators=[
            validators.EqualTo(
                'new_password',
                message='Passwords must match'
            )
        ]
    )

    current_password = PasswordField(
        'Current password',
        validators=[validators.DataRequired()]
    )

    submit_password = SubmitField('Update password')
