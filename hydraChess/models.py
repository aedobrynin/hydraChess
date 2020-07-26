from __future__ import annotations
from typing import Dict
from enum import Enum
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from chess import Board
from flask_login import UserMixin
from redis import Redis, ConnectionPool, exceptions


DEFAULT_POOL = ConnectionPool(host='localhost', port=6379, db=0)
DEFAULT_REDIS = Redis(connection_pool=DEFAULT_POOL)


class Model:
    '''Base class for Redis model'''
    def __init__(
            self,
            class_name: str,
            _id: int,
            redis: Redis) -> None:
        self._redis = redis
        self.__class_name = class_name
        self.__id = _id
        self._fetched = False
        self._data: Dict[str, str] = dict()

    @property
    def class_name(self) -> str:
        return self.__class_name

    @property
    def id(self) -> int:
        return self.__id

    @property
    def key(self) -> str:
        '''Get Redis key for the object'''
        return f"{self.class_name}:{self.id}"

    def fetch(self) -> None:
        '''Fetch object data from Redis.
        Raises LockNotOwnedError if the lock is expired'''
        bytes_data = self._redis.hgetall(self.key)
        self._data =\
            {key.decode(): val.decode() for key, val in bytes_data.items()}
        self._fetched = True

    def push(self) -> None:
        '''Update object data in Redis.
           Raises LockNotOwnedError if the lock is expired'''
        self._redis.hset(self.key, mapping=self._data)

    def __getitem__(self, key: str) -> str:
        '''Returns object field.
           Raises KeyError if the field is nonexistent'''
        if not self._fetched:
            self.fetch()
        try:
            return self._data[key]
        except KeyError as ex:
            raise KeyError("tried to access nonexistent field") from ex

    def __setitem__(self, key: str, val: str) -> None:
        '''Set field value'''
        if not self._fetched:
            self.fetch()
        self._data[key] = val

    def delete(self) -> None:
        '''Delete object from Redis'''
        self._redis.delete(self.key)
        self._data.clear()
        self._fetched = False


class LockableModel(Model):
    '''Model for data, which can be used in several threads'''
    def __init__(
            self,
            class_name: str,
            _id: int,
            redis: Redis) -> None:
        super().__init__(class_name, _id, redis)
        self._lock = self._redis.lock(
            f"{self.key}_lock",
            timeout=5,
            blocking_timeout=5)

        while not self._lock.acquire():
            pass

    def fetch(self) -> None:
        '''Fetch object data from Redis.
        Raises LockNotOwnedError if the lock is expired'''
        if self._lock.owned():
            super().fetch()
        else:
            raise exceptions.LockNotOwnedError(
                "tried to fetch data from Redis without acquired lock")

    def push(self) -> None:
        '''Update object data in Redis.
           Raises LockNotOwnedError if the lock is expired'''
        if self._lock.owned():
            super().push()
        else:
            raise exceptions.LockNotOwnedError(
                "tried to push data to Redis without acquired lock")

    def __setitem__(self, key: str, val: str) -> None:
        '''Set field value.
           Raises LockNotOwnedError if the lock is expired'''

        if self._lock.owned():
            super().__setitem__(key, val)
        else:
            raise exceptions.LockNotOwnedError(
                "tried to set value without acquired lock")

    def __del__(self) -> None:
        '''If the object is destroyed, release its' lock'''
        try:
            self._lock.release()
        except exceptions.LockError:
            pass


class User(Model, UserMixin):
    def __init__(self, _id: int, redis: Redis = DEFAULT_REDIS) -> None:
        super().__init__("User", _id, redis)

    @classmethod
    def create_new_user(cls, redis: Redis = DEFAULT_REDIS) -> int:
        '''Create new user and fill all fields with default values.
           Returns new user id.'''
        new_user_id = redis.get("UserID")
        if new_user_id:
            new_user_id = int(new_user_id) + 1
        else:
            new_user_id = 1

        new_user = User(new_user_id, redis)
        new_user.hashed_password = ""
        new_user.nickname = ""
        new_user.rating = 1200
        new_user.games_cnt = 0
        new_user.cur_game_id = 0
        new_user.k_factor = 40
        new_user.in_search = False
        new_user.sid = ""
        new_user.avatar_hash = "default"
        new_user.push()

        redis.set("UserID", str(new_user_id))

        return new_user_id

    @classmethod
    def get_user_id_by_nickname(cls, nickname: str,
                                redis: Redis = DEFAULT_REDIS) -> int:
        '''Returns user id by nickname index from Redis.
           Returns 0 if user not found.'''
        key = f"UserIdByNickname:{nickname}"
        _id = redis.get(key)
        if _id:
            return int(_id)
        return 0

    @property
    def hashed_password(self) -> str:
        return self["hashed_password"]

    @hashed_password.setter
    def hashed_password(self, val: str) -> None:
        self["hashed_password"] = generate_password_hash(val)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.hashed_password, password)

    @property
    def nickname(self) -> str:
        return self["nickname"]

    @nickname.setter
    def nickname(self, val: str) -> None:
        '''val can be empty only if it is a default value. There is
           no need to do anything with index in Redis,
           because the user doesn't exist for now.'''
        if val:
            old_nickname = self.nickname
            if old_nickname:
                self._redis.delete(f"UserIdByNickname:{old_nickname}")
            self._redis.set(f"UserIdByNickname:{val}", str(self.id))
        self["nickname"] = val

    @property
    def rating(self) -> int:
        return int(self["rating"])

    @rating.setter
    def rating(self, val: int) -> None:
        self["rating"] = str(val)

    @property
    def games_cnt(self) -> int:
        return int(self["games_cnt"])

    @games_cnt.setter
    def games_cnt(self, val: int) -> None:
        self["games_cnt"] = str(val)

    @property
    def cur_game_id(self) -> int:
        return int(self["cur_game_id"])

    @cur_game_id.setter
    def cur_game_id(self, val: int) -> None:
        self["cur_game_id"] = str(val)

    def is_playing(self) -> bool:
        return self.cur_game_id != 0

    @property
    def k_factor(self) -> int:
        return int(self["k_factor"])

    @k_factor.setter
    def k_factor(self, val: int) -> None:
        self["k_factor"] = str(val)

    @property
    def in_search(self) -> bool:
        return self["in_search"] == "1"

    @in_search.setter
    def in_search(self, val: bool) -> None:
        if val:
            self["in_search"] = "1"
        else:
            self["in_search"] = "0"

    @property
    def sid(self) -> str:
        return self["sid"]

    @sid.setter
    def sid(self, val: str) -> None:
        self["sid"] = val

    @property
    def avatar_hash(self) -> str:
        return self["avatar_hash"]

    @avatar_hash.setter
    def avatar_hash(self, val: str) -> None:
        self["avatar_hash"] = val

    def delete(self) -> None:
        nickname = self.nickname
        if nickname:
            self._redis.delete(f"UserIdByNickname:{nickname}")
        super().delete()


class Game(LockableModel):
    class State(Enum):
        NOT_STARTED = 0
        STARTED = 1
        FINISHED = 2

    class Result(Enum):
        NOT_DETERMINED = 0
        BLACK_WON = 1
        WHITE_WON = 2
        DRAW = 3
        CANCELLED = 4

    class Color(Enum):
        NONE = 0
        WHITE = 1
        BLACK = 2

    def __init__(self, _id: int, redis: Redis = DEFAULT_REDIS):
        super().__init__("Game", _id, redis)

    @classmethod
    def create_new_game(cls, redis: Redis = DEFAULT_REDIS) -> int:
        '''Create new game and fill all fields with default values.
           Returns new game id.'''
        new_game_id = redis.get("GameID")
        if new_game_id:
            new_game_id = int(new_game_id) + 1
        else:
            new_game_id = 1

        game = Game(new_game_id, redis)
        game.black_user_id = 0
        game.white_user_id = 0
        game.black_rating_before = 0
        game.white_rating_before = 0
        game.state = Game.State.NOT_STARTED
        game.result = Game.Result.NOT_DETERMINED
        game.draw_offer_sender = Game.Color.NONE
        game.last_move_datetime = datetime.min
        game.total_time = timedelta(seconds=0)
        game.black_clock = timedelta(seconds=0)
        game.white_clock = timedelta(seconds=0)
        game.moves = []
        game.push()

        redis.set("GameID", new_game_id)

        return new_game_id

    @property
    def black_user_id(self) -> int:
        return int(self["black_user_id"])

    @black_user_id.setter
    def black_user_id(self, val: int) -> None:
        self["black_user_id"] = str(val)

    @property
    def black_user(self) -> User:
        black_user_id = self.black_user_id
        if black_user_id == 0:
            raise ValueError("User id can't be 0")
        return User(black_user_id, self._redis)

    @black_user.setter
    def black_user(self, black_user: User) -> None:
        self.black_user_id = black_user.id
        self.black_rating_before = black_user.rating

    @property
    def white_user_id(self) -> int:
        return int(self["white_user_id"])

    @white_user_id.setter
    def white_user_id(self, val: int) -> None:
        self["white_user_id"] = str(val)

    @property
    def white_user(self) -> User:
        white_user_id = self.white_user_id
        if white_user_id == 0:
            raise ValueError("User id can't be 0")
        return User(white_user_id, self._redis)

    @white_user.setter
    def white_user(self, white_user: User) -> None:
        self.white_user_id = white_user.id
        self.white_rating_before = white_user.rating

    @property
    def black_rating_before(self) -> int:
        return int(self["black_rating_before"])

    @black_rating_before.setter
    def black_rating_before(self, val: int) -> None:
        self["black_rating_before"] = str(val)

    @property
    def white_rating_before(self) -> int:
        return int(self["white_rating_before"])

    @white_rating_before.setter
    def white_rating_before(self, val: int) -> None:
        self["white_rating_before"] = str(val)

    @property
    def state(self) -> Game.State:
        return Game.State(int(self["state"]))

    @state.setter
    def state(self, state: Game.State) -> None:
        self["state"] = str(state.value)

    @property
    def result(self) -> Game.Result:
        return Game.Result(int(self["result"]))

    @result.setter
    def result(self, result: Game.Result) -> None:
        self["result"] = str(result.value)

    @property
    def draw_offer_sender(self) -> Game.Color:
        return Game.Color(int(self["draw_offer_sender"]))

    @draw_offer_sender.setter
    def draw_offer_sender(self, color: Game.Color):
        self["draw_offer_sender"] = str(color.value)

    @property
    def last_move_datetime(self) -> datetime:
        return datetime.fromisoformat(self["last_move_datetime"])

    @last_move_datetime.setter
    def last_move_datetime(self, dtime: datetime) -> None:
        self["last_move_datetime"] = dtime.isoformat()

    @property
    def total_time(self) -> timedelta:
        seconds, microseconds = map(int, self["total_time"].split('.'))
        return timedelta(seconds=seconds, microseconds=microseconds)

    @total_time.setter
    def total_time(self, tdelta: timedelta) -> None:
        seconds = tdelta.seconds
        microseconds = tdelta.microseconds
        self["total_time"] = f"{seconds}.{microseconds}"

    @property
    def black_clock(self) -> timedelta:
        seconds, microseconds = map(int, self["black_clock"].split('.'))
        return timedelta(seconds=seconds, microseconds=microseconds)

    @black_clock.setter
    def black_clock(self, tdelta: timedelta) -> None:
        seconds = tdelta.seconds
        microseconds = tdelta.microseconds
        self["black_clock"] = f"{seconds}.{microseconds}"

    @property
    def white_clock(self) -> timedelta:
        seconds, microseconds = map(int, self["white_clock"].split('.'))
        return timedelta(seconds=seconds, microseconds=microseconds)

    @white_clock.setter
    def white_clock(self, tdelta: timedelta) -> None:
        seconds = tdelta.seconds
        microseconds = tdelta.microseconds
        self["white_clock"] = f"{seconds}.{microseconds}"

    @property
    def moves(self) -> list:
        raw_moves = self["moves"]
        if raw_moves:
            return list(raw_moves.split(','))
        return []

    @moves.setter
    def moves(self, moves: list) -> None:
        if not moves:
            self["moves"] = ""
        else:
            self["moves"] = ','.join(moves)

    def get_moves_cnt(self) -> int:
        raw_moves = self["moves"]
        if raw_moves:
            return raw_moves.count(',') + 1
        return 0

    def append_move(self, move_san: str) -> None:
        raw_moves = self["moves"]
        if raw_moves:
            self["moves"] += f",{move_san}"
        else:
            self["moves"] = move_san

    def get_next_to_move(self) -> Game.Color:
        moves_cnt = self.get_moves_cnt()
        if moves_cnt % 2 == 0:
            return Game.Color.WHITE
        return Game.Color.BLACK

    def get_board(self) -> Board:
        board = Board()
        for move in self.moves:
            board.push_san(move)
        return board
