import re
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_serializer import SerializerMixin
from flask_login import UserMixin
from sqlalchemy.dialects.sqlite import DATETIME


db = SQLAlchemy(session_options={"autoflush": False},
                engine_options={'connect_args': {'timeout': 10}})


class User(db.Model, UserMixin, SerializerMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   unique=True,
                   nullable=False)

    login = db.Column(db.String,
                      unique=True,
                      nullable=False)

    hashed_password = db.Column(db.String,
                                nullable=False)

    rating = db.Column(db.Integer, default=1200)

    games_played = db.Column(db.Integer, default=0)

    k_factor = db.Column(db.Integer, default=40)

    cur_game_id = db.Column(db.Integer, db.ForeignKey('games.id'))

    in_search = db.Column(db.Boolean, default=False)

    sid = db.Column(db.String, nullable=True)

    def set_password(self, password: str) -> None:
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.hashed_password, password)


class Game(db.Model, SerializerMixin):
    __tablename__ = "games"

    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   unique=True,
                   nullable=False)

    white_user_id = db.Column(db.Integer,
                              db.ForeignKey('users.id'))
    black_user_id = db.Column(db.Integer,
                              db.ForeignKey('users.id'))

    white_user = db.relationship('User',
                                 primaryjoin="User.id == \
                                              Game.white_user_id")
    black_user = db.relationship('User',
                                 primaryjoin="User.id == \
                                              Game.black_user_id")

    fen = db.Column(db.String)

    is_started = db.Column(db.Boolean,
                           default=0)
    is_finished = db.Column(db.Boolean,
                            default=0)

    white_clock = db.Column(db.Interval())
    black_clock = db.Column(db.Interval())

    last_move_datetime = \
        db.Column(DATETIME(storage_format="%(year)04d/%(month)02d/%(day)02d "
                                          "%(hour)02d:%(minute)02d:%(second)02d",
                           regexp=re.compile(r"(\d+)/(\d+)/(\d+) (\d+):(\d+):(\d+)")))

    result = db.Column(db.String)


class CeleryTaskTypes(db.Model):
    __tablename__ = "celery_task_types"

    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String, nullable=False)


class CeleryTask(db.Model):
    __tablename__ = "celery_tasks"

    id = db.Column(db.Integer, primary_key=True, unique=True)
    type_id = db.Column(db.Integer, db.ForeignKey('celery_task_types.id'),
                        primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    eta = db.Column(DATETIME(storage_format="%(year)04d/%(month)02d/%(day)02d "
                                            "%(hour)02d:%(minute)02d:%(second)02d",
                             regexp=re.compile(r"(\d+)/(\d+)/(\d+) "
                                               r"(\d+):(\d+):(\d+)")))


class GameRequest(db.Model):
    __tablename__ = "game_requests"

    id = db.Column(db.Integer, primary_key=True, unique=True)

    time = db.Column(db.Interval)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User')
