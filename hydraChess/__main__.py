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


from gevent import monkey
monkey.patch_all()

import os
import uuid
from io import BytesIO
from PIL import Image
from flask import Flask, request, url_for
from flask import render_template, redirect
from rom.util import EntityLock
import rom.util
from flask_socketio import SocketIO, disconnect, join_room
from flask_login import LoginManager, login_user, logout_user
from flask_login import current_user, login_required
from flask_restful import Api
import sass
from hydraChess.config import ProductionConfig
from hydraChess.forms import SignUpForm, LoginForm, SettingsForm
from hydraChess.models import User, Game
from hydraChess.resources import GamesPlayed, GamesList, GameResource


app = Flask(__name__)
app.config.from_object(ProductionConfig)

rom.util.set_connection_settings(db=app.config['REDIS_DB_ID'])
rom.util.use_null_session()

login_manager = LoginManager()
login_manager.init_app(app)

sio = SocketIO(app, message_queue=app.config['SOCKET_IO_URL'])

api = Api(app)
api.add_resource(GamesPlayed, '/api/v1.x/games_played/')
api.add_resource(GamesList, '/api/v1.x/games_list/')
api.add_resource(GameResource, '/api/v1.x/game/')


from hydraChess import game_management


def authenticated_only(func):
    """Decorator for socket auth checking"""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return disconnect()
        return func(*args, **kwargs)
    return wrapper


@login_manager.user_loader
def load_user(user_id: int) -> User:
    return User.get(user_id)


@app.route('/index', methods=['GET'])
@app.route('/', methods=['GET'])
def index():
    if current_user.is_authenticated:
        return redirect('/lobby')
    return render_template('index.html', title='Hydra Chess')


@app.route('/lobby', methods=['GET'])
@login_required
def lobby():
    return render_template('lobby.html', title='Lobby - Hydra Chess')


@app.route('/game/<int:game_id>', methods=['GET'])
def game_page(game_id: int):
    game = Game.get(game_id)
    if not game:
        return render_template('404.html'), 404

    if game.is_finished:
        return render_template(
                'game_static.html',
                title='Game - Hydra Chess'
        )

    return render_template('game.html', title='Game - Hydra Chess')


@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if current_user.is_authenticated:
        return redirect('/')
    form = SignUpForm()
    if form.validate_on_submit():
        user = User(login=form.login.data)
        user.set_password(form.password.data)
        user.save()

        login_user(user)
        return redirect('/')

    return render_template(
            'sign_up.html',
            title='Sign up - Hydra Chess',
            form=form
           )


@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if current_user.is_authenticated:
        return redirect('/')

    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by(login=form.login.data)
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template(
                'sign_in.html',
                title="Log in - Hydra Chess",
                message="Wrong login or password",
                form=form
               )
    return render_template(
            'sign_in.html',
            title="Log in - Hydra Chess",
            form=form
           )


@app.route('/user/<nickname>', methods=['GET'])
def user_profile(nickname: str):
    user = User.get_by(login=nickname)
    if not user:
        return render_template('404.html'), 404
    return render_template('user_profile.html',
                           title=f"{user.login}'s profile - Hydra Chess",
                           nickname=user.login,
                           rating=user.rating,
                           avatar_hash=user.avatar_hash)


@sio.on('search_game')
@authenticated_only
def on_search_game(*args, **kwargs):
    if any([current_user.cur_game_id, current_user.in_search]):
        print("Already in search/in game")
        return

    if not(args and isinstance(args[0], dict)):
        print("Bad arguments")
        return

    # If valid minutes value provided, create game request with it.
    # If valid game_id provided, create game request with the same game time as
    # the game.
    minutes = args[0].get('minutes', None)
    if isinstance(minutes, int) is False or\
            minutes not in (1, 2, 3, 5, 10, 20, 30, 60):
        try:
            game_id = args[0].get('game_id', None)
            game = Game.get(game_id)
            if not game:
                return
            minutes = game.total_clock.total_seconds() // 60
        except (ValueError, TypeError):
            return

    game_management.search_game.delay(current_user.id, minutes * 60)


@sio.on('cancel_search')
@authenticated_only
def on_cancel_search(*args, **kwargs):
    game_management.cancel_search.delay(current_user.id)


@sio.on('resign')
@authenticated_only
def on_resign(*args, **kwargs) -> None:
    if current_user.cur_game_id is None:
        return

    game_management.resign.delay(current_user.id, current_user.cur_game_id)


# TODO
"""
@sio.on('send_message')
@authenticated_only
def on_send_message(*args, **kwargs) -> None:
    if not current_user.cur_game_id:
        return

    if args and isinstance(args[0], dict):
        message = args[0].get('message', "").strip()[:70]
        if message:
            game_management.send_message.delay(current_user.cur_game_id,
                                               sender=current_user.login,
                                               message=message)
"""


@sio.on('connect')
def on_connect(*args, **kwargs) -> None:
    game_id = request.args.get('game_id')

    if not game_id:  # We are in lobby
        if current_user.is_authenticated:
            cur_user = User.get(current_user.id)
            with EntityLock(cur_user, 10, 10):
                cur_user.sid = request.sid
                cur_user.save()
        else:
            disconnect()
        return

    if not game_id.isdigit():  # Bad game id value
        disconnect()

    game_id = int(game_id)
    game = Game.get(game_id)

    if game is None:  # There is no game with current id
        disconnect()

    # If the game is finished, just use template with AJAX request
    # Else if the user is player, reconnect him to the game
    # Else connect the user to the spectators room

    if game.is_finished:
        disconnect()
        #  Render template
    else:
        if current_user.is_authenticated:
            cur_user = User.get(current_user.id)
            with EntityLock(cur_user, 10, 10):
                cur_user.sid = request.sid
                cur_user.save()

            if current_user.id in (game.white_user.id, game.black_user.id):
                game_management.reconnect.delay(current_user.id, game_id)
                return

        game_management.send_game_info.delay(game_id, request.sid, False)
        join_room(game_id)


@sio.on('make_draw_offer')
@authenticated_only
def on_make_draw_offer(*args, **kwargs) -> None:
    if current_user.cur_game_id:
        game_management.make_draw_offer.delay(current_user.id,
                                              current_user.cur_game_id)


@sio.on('accept_draw_offer')
@authenticated_only
def on_accept_draw_offer(*args, **kwargs) -> None:
    if current_user.cur_game_id:
        game_management.accept_draw_offer.delay(current_user.id,
                                                current_user.cur_game_id)


@sio.on('disconnect')
@authenticated_only
def on_disconnect(*args, **kwargs) -> None:
    if current_user.cur_game_id:
        game_management.on_disconnect.delay(current_user.id,
                                            current_user.cur_game_id)
    game_management.cancel_search.delay(current_user.id)


@sio.on('make_move')
@authenticated_only
def on_make_move(*args, **kwargs):
    if args and isinstance(args[0], dict):
        user_id = current_user.id
        san = args[0].get('san')
        game_id = args[0].get('game_id')
        try:
            game_id = int(game_id)
        except (TypeError, ValueError):
            return
        if san and game_id:
            game_management.make_move.delay(user_id, game_id, san)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = SettingsForm()

    message = ""
    if form.validate_on_submit():
        form.image.data.seek(0)  # Because the stream was already read on validation
        raw_img = BytesIO(form.image.data.read())

        img = Image.open(raw_img)
        img_new_side = min(img.width // 256, img.height // 256) * 256

        crop_left = (img.width - img_new_side) // 2
        crop_upper = (img.height - img_new_side) // 2
        crop_box = (
            crop_left,
            crop_upper,
            crop_left + img_new_side,
            crop_upper + img_new_side
        )
        img = img.crop(box=crop_box)
        img.thumbnail((256, 256), Image.ANTIALIAS)

        img_hash = uuid.uuid4().hex
        path = os.path.dirname(os.path.realpath(__file__)) +\
            url_for('static', filename=f'img/profiles/{img_hash}.jpg')

        img.convert('RGB').save(path)

        current_user.avatar_hash = img_hash
        current_user.save()
        message = "Your settings were successfuly updated!"

    return render_template('settings.html', title='Settings - Hydra Chess',
                           form=form, message=message)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.login_manager.unauthorized_handler
def unauth_handler():
    return redirect('/')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    compiled_bulma =\
        sass.compile(
            filename=os.path.join(
                app.root_path,
                app.static_url_path[1:],
                'sass/bulma.sass'
            ),
            output_style='compressed'
        )

    path_to_bulma_css =\
        os.path.join(app.root_path, app.static_url_path[1:], 'css/bulma.css')

    with open(path_to_bulma_css, "w") as bulma_css:
        bulma_css.write(compiled_bulma)

    #  Set debug to False in production
    sio.run(
        app,
        port=app.config['PORT'],
        debug=True,
    )
