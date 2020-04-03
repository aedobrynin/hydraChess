from gevent import monkey
monkey.patch_all()

from flask import Flask, request
from flask import render_template, redirect
from flask_socketio import SocketIO, join_room, disconnect, leave_room
from flask_login import LoginManager, login_user, logout_user
from flask_login import current_user, login_required
from flask_migrate import Migrate
from models import db, User, Game, CeleryTask
from forms import RegisterForm, LoginForm


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
    return render_template('index.html')


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
        return redirect('/sign_in')

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

    users_in_search = db.session.query(User).filter(User.in_search == 1).all()
    users_in_search.sort(key=lambda x: abs(current_user.rating - x.rating))

    if users_in_search and\
       abs(current_user.rating - users_in_search[0].rating) <= 200:
        user_to_play_with = users_in_search[0]

        game = Game(user_white_pieces_id=current_user.id,
                    user_black_pieces_id=user_to_play_with.id,
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
    else:
        current_user.in_search = True
        db.session.merge(current_user)
        db.session.commit()


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

    db.session.merge(current_user)
    db.session.commit()


@sio.on('move')
@authenticated_only
def move(*args, **kwargs):
    game_id = current_user.cur_game_id

    if game_id is None:
        return

    if args and isinstance(args[0], dict):
        user_id = current_user.id
        san = args[0].get("san")
        if san:
            game_management.update_game.delay(game_id, user_id, san)


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
