from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import redis
import rom
import rom.util

rom.util.set_connection_settings(db=1)
rom.util.use_null_session()


class User(rom.Model, UserMixin):
    _conn = redis.Redis(db=2)

    id = rom.PrimaryKey(index=True)

    login = rom.Text(unique=True)

    hashed_password = rom.Text()

    rating = rom.Integer(default=1200)

    games_played = rom.Integer(default=0)

    cur_game_id = rom.Integer(default=None)

    k_factor = rom.Integer(default=40)

    in_search = rom.Boolean(default=False)

    sid = rom.Text()

    def set_password(self, password: str) -> None:
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.hashed_password, password)


class Game(rom.Model):
    _conn = redis.Redis(db=3)

    id = rom.PrimaryKey(index=True)

    white_user = rom.OneToOne("User", 'no action')
    black_user = rom.OneToOne("User", 'no action')

    white_rating = rom.Integer()  # White rating before the game was played.
    black_rating = rom.Integer()  # Black rating before the game was played.
    fen = rom.Text()

    is_started = rom.Boolean(default=False)
    is_finished = rom.Boolean(default=False)
    result = rom.Text(default='*')
    result_reason = rom.Text(default="")

    moves = rom.Text(default="")
    last_move_datetime = rom.DateTime()

    white_clock = rom.Integer()
    black_clock = rom.Integer()

    first_move_timed_out_task_id = rom.Text()
    first_move_timed_out_task_eta = rom.DateTime()

    white_time_is_up_task_id = rom.Text()
    white_time_is_up_task_eta = rom.DateTime()

    white_disconnect_timed_out_task_id = rom.Text()
    white_disconnect_timed_out_task_eta = rom.DateTime()

    black_disconnect_timed_out_task_id = rom.Text()
    black_disconnect_timed_out_task_eta = rom.DateTime()

    white_time_is_up_task_id = rom.Text()
    black_time_is_up_task_id = rom.Text()

    draw_offer_sender = rom.Integer(default=None)
    draw_offer_try_this_move = rom.Boolean(default=False)


class GameRequest(rom.Model):
    _conn = redis.Redis(db=4)

    id = rom.PrimaryKey(index=True)

    time = rom.Float(index=True)
    user_id = rom.Integer(index=True)
