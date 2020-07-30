from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from chess import Board, WHITE, BLACK
from flask_login import UserMixin
import rom
import rom.util


class User(rom.Model, UserMixin):
    id = rom.PrimaryKey(index=True)

    login = rom.Text(unique=True, index=True, keygen=rom.FULL_TEXT)

    hashed_password = rom.Text()

    rating = rom.Integer(default=1200)

    games_played = rom.Integer(default=0)

    cur_game_id = rom.Integer(default=None)

    k_factor = rom.Integer(default=40)

    in_search = rom.Boolean(default=False)

    sid = rom.Text()

    avatar_hash = rom.Text(default="default")

    def set_password(self, password: str) -> None:
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.hashed_password, password)


class Game(rom.Model):
    id = rom.PrimaryKey(index=True)

    white_user = rom.OneToOne("User", 'no action')
    black_user = rom.OneToOne("User", 'no action')

    white_rating = rom.Integer()  # White rating before the game was played.
    black_rating = rom.Integer()  # Black rating before the game was played.

    is_started = rom.Boolean(default=False)
    is_finished = rom.Boolean(default=False)
    result = rom.Text(default='*')

    raw_moves = rom.Text(default="")
    last_move_datetime = rom.DateTime()

    raw_total_clock = rom.Text(default="0.0")
    raw_white_clock = rom.Text(default="0.0")
    raw_black_clock = rom.Text(default="0.0")

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

    @property
    def total_clock(self) -> timedelta:
        seconds, microseconds = map(int, self.raw_total_clock.split('.'))
        return timedelta(seconds=seconds, microseconds=microseconds)

    @total_clock.setter
    def total_clock(self, tdelta: timedelta) -> None:
        seconds = tdelta.seconds
        microseconds = tdelta.microseconds
        self.raw_total_clock = f"{seconds}.{microseconds}"

    @property
    def black_clock(self) -> timedelta:
        seconds, microseconds = map(int, self.raw_black_clock.split('.'))
        return timedelta(seconds=seconds, microseconds=microseconds)

    @black_clock.setter
    def black_clock(self, tdelta: timedelta) -> None:
        seconds = tdelta.seconds
        microseconds = tdelta.microseconds
        self.raw_black_clock = f"{seconds}.{microseconds}"

    @property
    def white_clock(self) -> timedelta:
        seconds, microseconds = map(int, self.raw_white_clock.split('.'))
        return timedelta(seconds=seconds, microseconds=microseconds)

    @white_clock.setter
    def white_clock(self, tdelta: timedelta) -> None:
        seconds = tdelta.seconds
        microseconds = tdelta.microseconds
        self.raw_white_clock = f"{seconds}.{microseconds}"

    @property
    def moves(self) -> list:
        raw_moves = self.raw_moves
        if raw_moves:
            return list(raw_moves.split(','))
        return []

    @moves.setter
    def moves(self, moves: list) -> None:
        if not moves:
            self.raw_moves = ""
        else:
            self.raw_moves = ','.join(moves)

    def get_moves_cnt(self) -> int:
        raw_moves = self.raw_moves
        if raw_moves:
            return raw_moves.count(',') + 1
        return 0

    def append_move(self, move_san: str) -> None:
        if self.raw_moves:
            self.raw_moves += f",{move_san}"
        else:
            self.raw_moves = move_san

    def get_next_to_move(self) -> bool:
        moves_cnt = self.get_moves_cnt()
        if moves_cnt % 2 == 0:
            return WHITE
        return BLACK

    def get_board(self) -> Board:
        board = Board()
        for move in self.moves:
            board.push_san(move)
        return board


class GameRequest(rom.Model):
    id = rom.PrimaryKey(index=True)

    time = rom.Float(index=True)
    user_id = rom.Integer(index=True)
