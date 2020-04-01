from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_serializer import SerializerMixin
from flask_login import UserMixin


db = SQLAlchemy()


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

    rating = db.Column(db.Float(precision=2), default=1200)

    games_played = db.Column(db.Integer, default=0)

    k_factor = db.Column(db.Integer, default=40)

    cur_game_id = db.Column(db.Integer, default=None)

    in_search = db.Column(db.Boolean, default=False)

    sid = db.Column(db.String, nullable=True, default=None)

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

    user_white_pieces_id = db.Column(db.Integer,
                                     db.ForeignKey('users.id'))
    user_black_pieces_id = db.Column(db.Integer,
                                     db.ForeignKey('users.id'))

    user_white_pieces = db.relationship('User',
                                        primaryjoin="User.id == \
                                        Game.user_white_pieces_id")
    user_black_pieces = db.relationship('User',
                                        primaryjoin="User.id == \
                                        Game.user_black_pieces_id")

    fen = db.Column(db.String, default=None)

    is_started = db.Column(db.Boolean,
                           default=0)
    is_finished = db.Column(db.Boolean,
                            default=0)

    result = db.Column(db.String)


class CeleryScheduled(db.Model):
    __tablename__ = "celery_scheduled"

    task_id = db.Column(db.Integer, unique=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'),
                        primary_key=True)
