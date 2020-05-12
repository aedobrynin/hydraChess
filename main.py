from gevent import monkey
monkey.patch_all()

from flask import Flask, request
from flask import render_template, redirect
from flask_socketio import SocketIO, disconnect, join_room
from flask_login import LoginManager, login_user, logout_user
from flask_login import current_user, login_required
from rom.util import EntityLock
from models import User, Game
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
        return redirect('/lobby')
    return render_template('index.html', title='Hydra Chess')


@app.route('/lobby', methods=['GET'])
@login_required
def lobby():
    return render_template('lobby.html', title='Lobby - Hydra Chess')


@app.route('/game/<int:game_id>', methods=['GET'])
def game(game_id: int):
    game = Game.get(game_id)
    if not game:
        return render_template('404.html'), 404

    is_player = current_user.is_authenticated and\
            current_user.id in (game.white_user.id, game.black_user.id)

    return render_template('game.html', title='Game - Hydra chess',
                           is_player=is_player)


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
            minutes = game.total_clock // 60
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


@sio.on('send_message')
@authenticated_only
def on_send_message(*args, **kwargs) -> None:
    """Sends message to game chat. Currently disabled."""
    return  # TODO
    '''
    if not current_user.cur_game_id:
        return

    if args and isinstance(args[0], dict):
        message = args[0].get('message', "").strip()[:70]
        if message:
            game_management.send_message.delay(current_user.cur_game_id,
                                               sender=current_user.login,
                                               message=message)
    '''


@sio.on('connect')
def on_connect(*args, **kwargs) -> None:
    game_id = request.args.get('game_id')
    game = None
    try:
        game_id = int(game_id)
    except (ValueError, TypeError):
        pass

    if isinstance(game_id, int):
        game = Game.get(game_id)

    if current_user.is_authenticated:
        cur_user = User.get(current_user.id)
        with EntityLock(cur_user, 10, 10):
            cur_user.sid = request.sid
            cur_user.save()

        if not game:
            if cur_user.cur_game_id:
                sio.emit('redirect',
                         {'url': f'/game/{cur_user.cur_game_id}'},
                         room=cur_user.sid,
                         )
            return

    is_player = current_user.is_authenticated and\
            current_user.id in (game.white_user.id, game.black_user.id)

    #  If the user is player and game isn't finished, we update user sid and
    #   reconnect him to the game.
    #  If the game is finished, we only send game info to the user.
    #  If the game isn't finished and user isn't player, we send him the game
    #   info and join him to the game room.

    if is_player and not game.is_finished:
        game_management.reconnect.delay(current_user.id, game_id)
    elif game.is_finished:
        game_management.send_game_info.delay(game_id, request.sid, is_player)
        # TODO: disconnect here
    else:
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
        if san and game_id:
            game_management.make_move.delay(user_id, game_id, san)


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
    sio.run(app, port=8000, debug=True)
