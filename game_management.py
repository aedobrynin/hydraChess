from datetime import datetime, timedelta, time
from typing import Dict
from math import ceil, floor
import chess
import rom
from celery.task.control import revoke
from flask_celery import make_celery
from main import app, sio
from models import User, Game, GameRequest


FIRST_MOVE_TIME_OUT = 15
DISCONNECT_TIME_OUT = 60


celery = make_celery(app)


def timedelta_to_dict(tdelta: timedelta) -> Dict[str, int]:
    """Returns {"min": minutes, "sec": seconds}
       extracted from timedelta object"""
    minutes = tdelta.seconds // 60
    seconds = tdelta.seconds % 60
    return {"min": minutes, "sec": seconds}


def time_to_timedelta(time_: time) -> timedelta:
    """Returns timedelta object, which is built from the time object"""
    return timedelta(minutes=time_.minute, seconds=time_.second)


def time_to_dict(time_: time) -> Dict[str, int]:
    """Returns {"min": minutes, "sec": seconds}
       extracted from time object"""
    return timedelta_to_dict(time_to_timedelta(time_))


def timedelta_to_time(tdelta: timedelta) -> time:
    """Returns time object, which is built from the timedelta object"""
    time_ = time(minute=tdelta.seconds // 60,
                 second=tdelta.seconds % 60)
    return time_


@celery.task(name='start_game', ignore_result=True)
def start_game(game_id: int) -> None:
    '''Marks game as started.
       Emits fen, pieces color, info about the opponent
        and rating changes to players'''

    game = Game.get(game_id)
    with rom.util.EntityLock(game, 10, 10):
        game.is_started = 1
        game.fen = chess.STARTING_FEN

        eta = datetime.utcnow() + timedelta(seconds=FIRST_MOVE_TIME_OUT)
        task = on_first_move_timed_out.apply_async(args=(game_id, ),
                                                   eta=eta)

        game.first_move_timed_out_task_id = task.id
        game.first_move_timed_out_task_eta = eta

        game.save()

    rating_changes = get_rating_changes(game_id)

    sio.emit('game_started',
             {"fen": game.fen,
              "color": "w",
              "opp_nickname": game.black_user.login,
              "opp_rating": game.black_user.rating,
              "opp_clock": time_to_dict(game.black_clock),
              "own_clock": time_to_dict(game.white_clock),
              "rating_changes": rating_changes["w"].to_dict()},
             room=game.white_user.sid)
    sio.emit('game_started',
             {"fen": game.fen,
              "color": "b",
              "opp_nickname": game.white_user.login,
              "opp_rating": game.white_user.rating,
              "opp_clock": time_to_dict(game.white_clock),
              "own_clock": time_to_dict(game.black_clock),
              "rating_changes": rating_changes["b"].to_dict()},
             room=game.black_user.sid)

    sio.emit('first_move_waiting',
             {'wait_time': FIRST_MOVE_TIME_OUT},
             room=game.white_user.sid)


@celery.task(name='make_move', ignore_result=True)
def make_move(user_id: int, game_id: int, move_san: str) -> None:
    '''Updates game state by user's move.
       Calls end_game(...) if the game is ended.'''

    request_datetime = datetime.utcnow()

    game = Game.get(game_id)

    if game.is_finished:
        return

    board = chess.Board(game.fen)
    is_user_white = user_id == game.white_user.id

    if (is_user_white and board.turn == chess.BLACK) or\
       (not is_user_white and board.turn == chess.WHITE):
        print(f"Wrong move side. User {User.get(user_id).login} plays {is_user_white} color, but now is {board.turn} turn. FEN: {game.fen}, move: {move_san} " )
        return

    try:
        with rom.util.EntityLock(game, 10, 10):
            board.push_san(move_san)
            game.fen = board.fen()

            if game.first_move_timed_out_task_id:
                revoke(game.first_move_timed_out_task_id)
                game.first_move_timed_out_task_id = None
                # game.first_move_timed_out_task_eta = None

            if is_user_white:
                revoke(game.white_time_is_up_task_id)
                # game.white_time_is_up_task_id = None
            else:
                revoke(game.black_time_is_up_task_id)
                # game.black_time_is_up_task_id = None

            if is_user_white and game.white_disconnect_timed_out_task_id:
                revoke(game.white_disconnect_timed_out_task_id)
                game.white_disconnect_timed_out_task_id = None
                sio.emit('opp_reconnected', room=game.black_user.sid)
            elif not is_user_white and game.black_disconnect_timed_out_task_id:
                revoke(game.black_disconnect_timed_out_task_id)
                game.black_disconnect_timed_out_task_id = None
                sio.emit('opp_reconnected', room=game.white_user.sid)

            if is_user_white:
                game.white_clock = \
                    timedelta_to_time(
                            time_to_timedelta(game.white_clock) -
                            (request_datetime - (game.last_move_datetime or
                                                 request_datetime)))

                eta = datetime.utcnow() + time_to_timedelta(game.black_clock)

                task = on_time_is_up.apply_async(args=(game.black_user.id,
                                                       game_id),
                                                 eta=eta)

                game.white_time_is_up_task_id = task.id
                game.white_time_is_up_task_eta = eta
            else:
                game.black_clock = \
                        timedelta_to_time(
                            time_to_timedelta(game.black_clock) -
                            (request_datetime - (game.last_move_datetime or
                                                 request_datetime)))

                eta = datetime.utcnow() + time_to_timedelta(game.white_clock)

                task = on_time_is_up.apply_async(args=(game.white_user.id,
                                                       game_id),
                                                 eta=eta)

                game.black_time_is_up_task_id = task.id
                game.black_time_is_up_task_eta = eta

            game.last_move_datetime = request_datetime

            if board.fullmove_number == 1:  # and board.turn == chess.BLACK
                sio.emit('first_move_waiting',
                         {'wait_time': FIRST_MOVE_TIME_OUT},
                         room=game.black_user.sid)

                eta = \
                    datetime.utcnow() + timedelta(seconds=FIRST_MOVE_TIME_OUT)
                task = on_first_move_timed_out.\
                    apply_async((game_id, ), eta=eta)

                game.first_move_timed_out_task_id = task.id
                game.first_move_timed_out_task_eta = eta

            game.save()

        white_clock_dict = time_to_dict(game.white_clock)
        black_clock_dict = time_to_dict(game.black_clock)
        sio.emit('game_updated',
                 {"san": move_san,
                  "opp_clock": black_clock_dict,
                  "own_clock": white_clock_dict},
                 room=game.white_user.sid)
        sio.emit('game_updated',
                 {"san": move_san,
                  "opp_clock": white_clock_dict,
                  "own_clock": black_clock_dict},
                 room=game.black_user.sid)

        result = board.result()
        if result != '*':
            end_game.delay(game_id, result)
    except ValueError:
        pass


@celery.task(name="on_resign", ignore_result=True)
def on_resign(user_id: int, game_id: int) -> None:
    """Ends the game due to one player's resignation"""
    game = Game.get(game_id)

    user_white = user_id == game.white_user.id

    result = "0-1" if user_white else "1-0"
    reason_white = "You've resigned" if user_white else "Opponent resigned"
    reason_black = "Opponent resigned" if user_white else "You've resigned"

    end_game.delay(game_id, result, reason_white, reason_black)


@celery.task(name="on_reconnect", ignore_result=True)
def on_reconnect(user_id: int, game_id: int) -> None:
    '''Emits fen, pieces color, info about the opponent and
        rating changes to player.
       Emits all info about timers (first move waiting, etc...)
       Emits 'opp_reconnected' to the opponent.'''

    game = Game.get(game_id)

    rating_changes = get_rating_changes(game_id)

    black_clock = time_to_timedelta(game.black_clock)
    white_clock = time_to_timedelta(game.white_clock)

    color_to_move = game.fen.split()[1]

    if game.last_move_datetime:
        if color_to_move == 'w':
            white_clock -= datetime.utcnow() - game.last_move_datetime
        else:
            black_clock -= datetime.utcnow() - game.last_move_datetime

    is_user_white = user_id == game.white_user.id

    if is_user_white:
        sio.emit('game_started',
                 {'fen': game.fen,
                  "color": "w",
                  "opp_nickname": game.black_user.login,
                  "opp_rating": game.black_user.rating,
                  "opp_clock": timedelta_to_dict(black_clock),
                  "own_clock": timedelta_to_dict(white_clock),
                  "rating_changes": rating_changes["w"].to_dict()},
                 room=game.white_user.sid)

        if game.white_disconnect_timed_out_task_id:
            revoke(game.white_disconnect_timed_out_task_id)
            with rom.util.EntityLock(game, 10, 10):
                game.white_disconnect_timed_out_task_id = None
                game.save()

        sio.emit('opp_reconnected',
                 room=game.black_user.sid)

    else:
        sio.emit('game_started',
                 {'fen': game.fen,
                  "color": "b",
                  "opp_nickname": game.white_user.login,
                  "opp_rating": game.white_user.rating,
                  "opp_clock": timedelta_to_dict(white_clock),
                  "own_clock": timedelta_to_dict(black_clock),
                  "rating_changes": rating_changes["b"].to_dict()},
                 room=game.black_user.sid)

        if game.black_disconnect_timed_out_task_id:
            revoke(game.black_disconnect_timed_out_task_id)
            with rom.util.EntityLock(game, 10, 10):
                game.black_disconnect_timed_out_task_id = None
                game.save()

        sio.emit('opp_reconnected',
                 room=game.white_user.sid)

    if is_user_white:
        if game.first_move_timed_out_task_id and color_to_move == 'w':
            wait_time = (game.first_move_timed_out_task_eta -
                         datetime.utcnow()).seconds
            sio.emit('first_move_waiting',
                     {'wait_time': wait_time},
                     room=game.white_user.sid)
    elif game.first_move_timed_out_task_id and color_to_move == 'b':
        wait_time = (game.first_move_timed_out_task_eta -
                     datetime.utcnow()).seconds
        sio.emit('first_move_waiting',
                 {'wait_time': wait_time},
                 room=game.black_user.sid)

    if is_user_white and game.black_disconnect_timed_out_task_id:
        wait_time = (game.black_disconnect_timed_out_task_eta -
                     datetime.utcnow()).seconds
        sio.emit('opp_disconnected',
                 {'wait_time': wait_time},
                 room=game.white_user.sid)
    elif not is_user_white and game.white_disconnect_timed_out_task_id:
        wait_time = (game.white_disconnect_timed_out_task_eta -
                     datetime.utcnow()).seconds
        sio.emit('opp_disconnected',
                 {'wait_time': wait_time},
                 room=game.black_user.sid)


@celery.task(name="on_connect", ignore_result=True)
def on_connect(user_id: int) -> None:
    '''Emits 'set_data' signal.
       If in game, revokes disconnect_timed_out task,
        calls on_reconnect()'''
    user = User.get(user_id)

    sio.emit('set_data',
             {'nickname': user.login,
              'rating': user.rating},
             room=user.sid)

    if user.cur_game_id:
        on_reconnect(user_id, user.cur_game_id)


@celery.task(name="on_disconnect", ignore_result=True)
def on_disconnect(user_id: int, game_id: int) -> None:
    '''Schedules on_disconnect_timed_out_task, adds it to database.
       Emits 'opp_disconnected' to the opponent'''

    eta = datetime.utcnow() + timedelta(seconds=DISCONNECT_TIME_OUT)
    task = on_disconnect_timed_out.apply_async(args=(user_id, game_id),
                                               eta=eta)

    game = Game.get(game_id)

    is_user_white = user_id == game.white_user.id

    opp_sid: int
    with rom.util.EntityLock(game, 10, 10):
        if is_user_white:
            game.white_disconnect_timed_out_task_id = task.id
            game.white_disconnect_timed_out_task_eta = eta
            opp_sid = game.black_user.sid
        else:
            game.black_disconnect_timed_out_task_id = task.id
            game.black_disconnect_timed_out_task_eta = eta
            opp_sid = game.white_user.sid

        game.save()

    if opp_sid:
        sio.emit('opp_disconnected',
                 {'wait_time': DISCONNECT_TIME_OUT},
                 room=opp_sid)


@celery.task(name='end_game', ignore_result=True)
def end_game(game_id: int, result: str,
             reason_white: str = '',
             reason_black: str = '',
             update_stats=True) -> None:
    '''Marks game as finished, emits 'game_ended' signal to users,
     closes the room,
     recalculates ratings and k-factors if update_stats is True'''

    game = Game.get(game_id)

    if game.first_move_timed_out_task_id:
        revoke(game.first_move_timed_out_task_id)

    if game.white_disconnect_timed_out_task_id:
        revoke(game.white_disconnect_timed_out_task_id)

    if game.black_disconnect_timed_out_task_id:
        revoke(game.black_disconnect_timed_out_task_id)

    if game.white_time_is_up_task_id:
        revoke(game.white_time_is_up_task_id)

    if game.black_time_is_up_task_id:
        revoke(game.black_time_is_up_task_id)

    results = {'1-0': ('won', 'lost'),
               '1/2-1/2': ('draw', 'draw'),
               '0-1': ('lost', 'won'),
               '-': ('interrupted', 'interrupted')}

    result_white, result_black = results[result]

    sio.emit('game_ended',
             {'result': result_white,
              'reason': reason_white},
             room=game.white_user.sid)
    sio.emit('game_ended',
             {'result': result_black,
              'reason': reason_black},
             room=game.black_user.sid)

    with rom.util.EntityLock(game, 10, 10):
        game.is_finished = 1
        game.result = result

        with rom.util.EntityLock(game.white_user, 10, 10):
            game.white_user.cur_game_id = None
            game.white_user.save()

        with rom.util.EntityLock(game.black_user, 10, 10):
            game.black_user.cur_game_id = None
            game.black_user.save()

        game.save()

    if update_stats is False:
        return

    rating_changes = get_rating_changes(game_id)

    with rom.util.EntityLock(game.white_user, 10, 10):
        game.white_user.games_played += 1
        game.white_user.save()

    with rom.util.EntityLock(game.black_user, 10, 10):
        game.black_user.games_played += 1
        game.black_user.save()

    if result == "1-0":
        update_rating.delay(game.white_user.id,
                            rating_changes["w"].win)
        update_rating.delay(game.black_user.id,
                            rating_changes["b"].lose)
    elif result == "1/2-1/2":
        update_rating.delay(game.white_user.id,
                            rating_changes["w"].draw)
        update_rating.delay(game.black_user.id,
                            rating_changes["b"].draw)
    elif result == "0-1":
        update_rating.delay(game.white_user.id,
                            rating_changes["w"].lose)
        update_rating.delay(game.black_user.id,
                            rating_changes["b"].win)

    update_k_factor.delay(game.white_user.id)
    update_k_factor.delay(game.black_user.id)


@celery.task(name="send_message", ignore_result=True)
def send_message(game_id: int, sender: str, message: str):
    '''Send chat message to game players'''
    game = Game.get(game_id)

    for sid in (game.white_user.sid, game.black_user.sid):
        if sid:
            sio.emit('get_message',
                     {'sender': sender,
                      'message': message},
                     room=sid)


@celery.task(name="on_first_move_timed_out", ignore_result=True)
def on_first_move_timed_out(game_id: int) -> None:
    """Interrupts game because of user didn't make first move for too long"""
    game = Game.get(game_id)

    color_to_move = game.fen.split()[1]

    reason_white = "You didn't make the first move"
    reason_black = "Your opponent didn't make the first move"
    if color_to_move == 'b':
        reason_white, reason_black = reason_black, reason_white

    end_game.delay(game_id, "-", reason_white, reason_black,
                   update_stats=False)


@celery.task(name="on_disconnect_timed_out", ignore_results=True)
def on_disconnect_timed_out(user_id: int, game_id: int) -> None:
    """Interrupts game because of user being disconnected for too long"""
    game = Game.get(game_id)

    result = "1-0"
    reason_white = "Opponent was disconnected too long"
    reason_black = "You was disconnected too long"
    if user_id == game.white_user.id:
        result = "0-1"
        reason_white, reason_black = reason_black, reason_white

    end_game(game_id, result, reason_white, reason_black)


@celery.task(name="on_time_is_up", ignore_results=True)
def on_time_is_up(user_id: int, game_id: int) -> None:
    """Interrupts game because of user's time is up"""
    game = Game.get(game_id)

    board = chess.Board(game.fen)

    is_user_white = user_id == game.white_user.id

    result: str
    reason_white: str
    reason_black: str
    # Finish game with draw if other player has insufficient material to win
    if (is_user_white and board.has_insufficient_material(chess.BLACK)) or\
       (not is_user_white and board.has_insufficient_material(chess.WHITE)):
        result = "1/2-1/2"
        reason_white = ("Opponent's time is up, "
                        "but you have an insufficient material")
        reason_black = ("Your time is up, "
                        "but opponent has an insufficient material")
        if user_id == game.white_user.id:
            reason_white, reason_black = reason_black, reason_white
    else:
        result = "1-0"
        reason_white = "Opponent's time is up"
        reason_black = "Your time is up"
        if user_id == game.white_user.id:
            result = "0-1"
            reason_white, reason_black = reason_black, reason_white

    end_game.delay(game_id, result, reason_white, reason_black)


class RatingChange:
    '''Class for comfortable work with rating changes'''
    def __init__(self, win=None, draw=None, lose=None):
        self.win = win
        self.draw = draw
        self.lose = lose

    @staticmethod
    def from_formula(k: int, e: float):
        '''Build up RatingChange object from ELO rating system formula'''
        win = ceil(k * (1 - e))
        draw = floor(k * (0.5 - e))
        lose = floor(k * (-e))
        return RatingChange(win, draw, lose)

    def to_dict(self):
        '''Get rating changes in dict'''
        return {"win": self.win,
                "draw": self.draw,
                "lose": self.lose}


def get_rating_changes(game_id: int) -> Dict[str, RatingChange]:
    '''Returns rating changes for game in dict.
       Example: {'w': RatingChange,
                 'b': RatingChange}'''
    game = Game.get(game_id)
    r_white = game.white_user.rating
    r_black = game.black_user.rating

    R_white = 10 ** (r_white / 400)
    R_black = 10 ** (r_black / 400)

    R_sum = R_white + R_black

    E_white = R_white / R_sum
    E_black = R_black / R_sum

    k_factor_white = game.white_user.k_factor
    k_factor_black = game.black_user.k_factor

    rating_change_white = RatingChange.from_formula(k_factor_white, E_white)
    rating_change_black = RatingChange.from_formula(k_factor_black, E_black)

    return {"w": rating_change_white,
            "b": rating_change_black}


@celery.task(name="update_k_factor", ignore_result=True)
def update_k_factor(user_id: int) -> None:
    '''Updates k_factor by FIDE rules (after 2014)'''
    user = User.get(user_id)

    with rom.util.EntityLock(user, 10, 10):
        if user.k_factor == 40 and user.games_played >= 30:
            user.k_factor = 20
            user.save()

        if (user.k_factor == 20 and user.games_played >= 3
                and user.rating >= 2400):
            user.k_factor = 10
            user.save()


@celery.task(name="update_rating", ignore_result=True)
def update_rating(user_id: int, rating_delta: int) -> None:
    '''Update database info about user's rating'''
    user = User.get(user_id)
    with rom.util.EntityLock(user, 10, 10):
        user.rating += rating_delta
        user.save()


@celery.task(name="search_game", ignore_result=True)
def search_game(user_id: int, minutes: int) -> None:
    game_time = time(minute=minutes)
    user = User.get(user_id)
    with rom.util.EntityLock(user, 10, 10):
        game_requests = rom.query.Query(GameRequest).filter(time=game_time).all()

        added_to_existed = False
        if game_requests:
            accepted_request = \
                min(game_requests,
                    key=lambda x: abs(User.get(x.user_id).rating -
                                      user.rating))
            if abs(user.rating -
                   User.get(accepted_request.user_id).rating) <= 200:
                added_to_existed = True

                accepted_request.delete()
                user_to_play_with = User.get(accepted_request.user_id)

                game = Game(white_user=user,
                            black_user=user_to_play_with,
                            white_clock=game_time,
                            black_clock=game_time,
                            is_started=0)
                game.save()

                user.cur_game_id = game.id
                user.save()

                with rom.util.EntityLock(user_to_play_with, 10, 10):
                    user_to_play_with.cur_game_id = game.id
                    user_to_play_with.in_search = False
                    user_to_play_with.save()

                start_game.delay(game.id)

        if added_to_existed is False:
            user.in_search = True
            user.save()

            game_request = GameRequest(time=game_time,
                                       user_id=user_id)
            game_request.save()

