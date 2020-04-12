from gevent import monkey
monkey.patch_all()

from flask import Flask, request
from flask import render_template, redirect
from flask_socketio import SocketIO, join_room, disconnect, leave_room
from flask_login import LoginManager, login_user, logout_user
from flask_login import current_user, login_required
from flask_migrate import Migrate
from models import db, User, Game, CeleryTask, GameRequest
from forms import RegisterForm, LoginForm
from datetime import timedelta


app = Flask(__name__)
app.config['SECRET_KEY'] = 'abacabadabacaba'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./database.db'
app.config['CELERY_BROKER_URL'] = 'amqp://localhost//'
app.config['CELERY_RESULT_BACKEND'] = 'rpc'

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)

sio = SocketIO(app, message_queue="amqp://localhost//")

import game_management  # Don't move it anywhere!


def authenticated_only(func):
    """Decorator for socket auth checking"""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return disconnect()
        return func(*args, **kwargs)
    return wrapper


@login_manager.user_loader
def load_user(user_id: int) -> User:
    return db.session.query(User).get(user_id)


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
        user = User(
            login=form.login.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect('/')

    return render_template('register.html', title='Register', form=form)


@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if current_user.is_authenticated:
        return redirect('/')

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).\
            filter(User.login == form.login.data).first()
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

    game_time = timedelta(minutes=minutes)

    game_requests = db.session.query(GameRequest).\
        filter(GameRequest.time == game_time).all()

    added_to_existed = False
    if game_requests:
        accepted_request = \
            min(game_requests,
                key=lambda x: abs(current_user.rating - x.user.rating))
        if abs(current_user.rating - accepted_request.user.rating) <= 200:
            added_to_existed = True

            db.session.delete(accepted_request)
            user_to_play_with = accepted_request.user

            game = Game(white_user_id=current_user.id,
                        black_user_id=user_to_play_with.id,
                        white_clock=game_time,
                        black_clock=game_time,
                        is_started=0)

            db.session.add(game)
            db.session.commit()

            current_user.cur_game_id = game.id
            user_to_play_with.cur_game_id = game.id

            user_to_play_with.in_search = False

            join_room(game.id, sid=current_user.sid)
            join_room(game.id, sid=user_to_play_with.sid)

            db.session.merge(current_user)
            db.session.merge(user_to_play_with)
            db.session.commit()

            game_management.start_game.delay(game.id)

    if added_to_existed is False:
        current_user.in_search = True
        db.session.merge(current_user)

        game_request = GameRequest(time=game_time,
                                   user_id=current_user.id)
        db.session.add(game_request)
        db.session.commit()


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
    if current_user.cur_game_id is None:
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
    current_user.sid = request.sid
    db.session.merge(current_user)
    db.session.commit()

    if current_user.cur_game_id:
        join_room(current_user.cur_game_id, sid=current_user.sid)
    game_management.on_connect.delay(current_user.id)


@sio.on('disconnect')
@authenticated_only
def on_disconnect(*args, **kwargs) -> None:
    if current_user.cur_game_id is not None:
        leave_room(current_user.cur_game_id, sid=request.sid)
        game_management.on_disconnect.delay(current_user.id,
                                            current_user.cur_game_id)
    if current_user.in_search:
        current_user.in_search = False

        for game_request in db.session.query(GameRequest).\
                filter(GameRequest.user_id == current_user.id):
            db.session.delete(game_request)
    db.session.merge(current_user)
    db.session.commit()


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


@app.before_first_request
def prepare_database():
    """Clears user sids and drops celery_scheduled table"""
    for user in db.session.query(User):
        user.sid = None
        db.session.merge(user)

    db.session.query(CeleryTask).delete()
    db.session.commit()


if __name__ == '__main__':
    sio.run(app, port=8000, debug=True)
