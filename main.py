from datetime import time
from gevent import monkey
monkey.patch_all()

from flask import Flask, request
from flask import render_template, redirect
from flask_socketio import SocketIO, disconnect
from flask_login import LoginManager, login_user, logout_user
from flask_login import current_user, login_required
import rom
from models import User, GameRequest
from forms import RegisterForm, LoginForm
import game_management


app = Flask(__name__)
app.config['SECRET_KEY'] = 'abacabadabacaba'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'

login_manager = LoginManager()
login_manager.init_app(app)

sio = SocketIO(app, message_queue="redis://localhost:6379/1")


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
        return redirect('/play')
    return render_template('index.html', title="Hydra Chess")


@app.route('/play', methods=['GET'])
@login_required
def play():
    return render_template('play.html', title="Play chess")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/')
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(login=form.login.data)
        user.set_password(form.password.data)
        user.save()

        login_user(user)
        return redirect('/')

    return render_template('register.html', title='Register', form=form)


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
        return render_template('sign_in.html',
                               title="Sign in",
                               message="Wrong login or password",
                               form=form)
    return render_template('sign_in.html', title="Sign in", form=form)


@sio.on('search')
@authenticated_only
def search_game(*args, **kwargs):
    """Marks user as "in search" or pairs him with another user from search.
        Chooses opponent by |opp.rating - user.rating|.
        If the value more than 200, user marks as 'in search'"""

    if any([current_user.cur_game_id, current_user.in_search]):
        print("Already in search/in game")
        return

    if not(args and isinstance(args[0], dict)):
        print("Bad arguments")
        return

    minutes = args[0].get('minutes', None)
    if isinstance(minutes, int) is False or minutes not in [1, 3, 5, 10]:
        print("Bad arguments")
        return

    game_management.search_game.delay(current_user.id, minutes)


@sio.on('resign')
@authenticated_only
def resign(*args, **kwargs) -> None:
    if current_user.cur_game_id is None:
        return

    game_management.on_resign.delay(current_user.id, current_user.cur_game_id)


@sio.on('send_message')
@authenticated_only
def send_message(*args, **kwargs) -> None:
    """Sends message to game chat"""
    if not current_user.cur_game_id:
        return

    if args and isinstance(args[0], dict):
        message = args[0].get('message', "").strip()[:70]
        if message:
            game_management.send_message.delay(current_user.cur_game_id,
                                               sender=current_user.login,
                                               message=message)


@sio.on('connect')
@authenticated_only
def on_connect(*args, **kwargs) -> None:
    cur_user = User.get(current_user.id)
    with rom.util.EntityLock(cur_user, 10, 10):
        cur_user.sid = request.sid
        cur_user.save()

    game_management.on_connect.delay(current_user.id)


@sio.on('disconnect')
@authenticated_only
def on_disconnect(*args, **kwargs) -> None:
    if current_user.cur_game_id:
        game_management.on_disconnect.delay(current_user.id,
                                            current_user.cur_game_id)

    cur_user = User.get(current_user.id)
    with rom.util.EntityLock(cur_user, 10, 10):
        if cur_user.in_search:
            cur_user.in_search = False
            cur_user.save()

            game_request = GameRequest.get_by(user_id=cur_user.id,
                                              _limit=(0, 1))
            if game_request:
                game_request[0].delete()


@sio.on('make_move')
@authenticated_only
def move(*args, **kwargs):
    game_id = current_user.cur_game_id

    if game_id is None:
        return

    if args and isinstance(args[0], dict):
        user_id = current_user.id
        san = args[0].get("san")
        if san:
            game_management.make_move.delay(user_id, game_id, san)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.login_manager.unauthorized_handler
def unauth_handler():
    return redirect('/')


if __name__ == '__main__':
    sio.run(app, port=8000, debug=True)
