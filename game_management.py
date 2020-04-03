from datetime import datetime, timedelta
from typing import Dict
from math import ceil, floor
import chess
from celery.task.control import revoke
from flask_socketio import close_room
from flask_celery import make_celery
from main import app, sio
from models import db, Game, User, CeleryTask


ON_FIRST_MOVE_TIMED_OUT = 0
ON_DISCONNECT_TIMED_OUT = 1
USER_ACCEPTABLE = (ON_FIRST_MOVE_TIMED_OUT, ON_DISCONNECT_TIMED_OUT)

celery = make_celery(app)


@celery.task(name='start_game', ignore_result=True)
def start_game(game_id: int) -> None:
    '''Marks game as started.
       Emits fen, pieces color, info about the opponent
        and rating changes to players'''

    game = db.session.query(Game).get(game_id)
    game.is_started = 1
    game.fen = chess.STARTING_FEN
    db.session.merge(game)
    db.session.commit()

    rating_changes = get_rating_changes(game_id)

    sio.emit('game_started',
             {"fen": game.fen,
              "color": "w",
              "opp_nickname": game.user_black_pieces.login,
              "opp_rating": game.user_black_pieces.rating,
              "rating_changes": rating_changes["w"].to_dict()},
             room=game.user_white_pieces.sid)
    sio.emit('game_started',
             {"fen": game.fen,
              "color": "b",
              "opp_nickname": game.user_white_pieces.login,
              "opp_rating": game.user_white_pieces.rating,
              "rating_changes": rating_changes["b"].to_dict()},
             room=game.user_black_pieces.sid)

    sio.emit('first_move_waiting',
             {'wait_time': 15},
             room=game.user_white_pieces.sid)

    task = on_first_move_timed_out.apply_async(args=(game_id, ), countdown=16)
    celery_task = CeleryTask(id=task.id,
                             type_id=ON_FIRST_MOVE_TIMED_OUT,
                             game_id=game_id,
                             user_id=game.user_white_pieces_id,
                             eta=datetime.now() + timedelta(seconds=16))

    db.session.add(celery_task)
    db.session.commit()


@celery.task(name='update_game', ignore_result=True)
def update_game(game_id: int, user_id: int, move_san: str = "",
                draw_offer: bool = False, surrender: bool = False) -> None:
    '''Updates game state by user's data.
       Calls end_game(...) if the game is ended.'''
    # TODO: draw offer and surrender support

    game = db.session.query(Game).get(game_id)

    if game.is_finished:
        return

    board = chess.Board(game.fen)
    user_white = game.user_white_pieces_id == user_id

    if (user_white and board.turn == chess.BLACK) or\
       (not user_white and board.turn == chess.WHITE):
        print("Wrong move side.")
        return

    if move_san:
        try:
            board.push_san(move_san)
            game.fen = board.fen()

            task = db.session.query(CeleryTask).\
                filter(CeleryTask.game_id == game_id).\
                filter(CeleryTask.type_id == ON_FIRST_MOVE_TIMED_OUT).first()
            if task is not None:
                revoke(task.id)
                db.session.delete(task)

            if board.fullmove_number == 1:  # and board.turn == chess.BLACK
                sio.emit('first_move_waiting',
                         {'wait_time': 15},
                         room=game.user_black_pieces.sid)

                task = on_first_move_timed_out.apply_async((game_id, ),
                                                           countdown=16)

                celery_task = CeleryTask(id=task.id,
                                         type_id=ON_FIRST_MOVE_TIMED_OUT,
                                         game_id=game_id,
                                         user_id=game.user_black_pieces_id,
                                         eta=datetime.now() +
                                         timedelta(seconds=16))
                db.session.add(celery_task)

            db.session.merge(game)
            db.session.commit()

            result = board.result()
            sio.emit('game_updated',
                     {"san": move_san},
                     room=game_id)
            if result != '*':
                end_game.delay(game_id, result)
        except ValueError:
            pass


@celery.task(name="on_reconnect", ignore_result=True)
def on_reconnect(user_id: int, game_id: int) -> None:
    '''Emits fen, pieces color, info about the opponent and
        rating changes to player.
       Emits all info about timers (first move waiting, etc...)
       Emits 'opp_reconnected' to the opponent.'''

    game = db.session.query(Game).get(game_id)

    rating_changes = get_rating_changes(game_id)

    sid = db.session.query(User).get(user_id).sid

    if user_id == game.user_white_pieces_id:
        sio.emit('game_started',
                 {'fen': game.fen,
                  "color": "w",
                  "opp_nickname": game.user_black_pieces.login,
                  "opp_rating": game.user_black_pieces.rating,
                  "rating_changes": rating_changes["w"].to_dict()},
                 room=sid)
        sio.emit('opp_reconnected',
                 room=game.user_black_pieces.sid)
    else:
        sio.emit('game_started',
                 {'fen': game.fen,
                  "color": "b",
                  "opp_nickname": game.user_white_pieces.login,
                  "opp_rating": game.user_white_pieces.rating,
                  "rating_changes": rating_changes["b"].to_dict()},
                 room=sid)
        sio.emit('opp_reconnected',
                 room=game.user_white_pieces.sid)

    celery_tasks = db.session.query(CeleryTask).\
        filter(CeleryTask.game_id == game_id).\
        filter(CeleryTask.type_id.in_(USER_ACCEPTABLE))

    for task in celery_tasks:
        if task.type_id == ON_FIRST_MOVE_TIMED_OUT and\
           task.user_id == user_id:
            wait_time = (task.eta - datetime.now()).seconds
            sio.emit('first_move_waiting',
                     {'wait_time': wait_time},
                     room=sid)
        elif task.type_id == ON_DISCONNECT_TIMED_OUT and\
                task.user_id != user_id:
            wait_time = (task.eta - datetime.now()).seconds
            sio.emit('opp_disconnected',
                     {'wait_time': wait_time},
                     room=sid)


@celery.task(name="on_connect", ignore_result=True)
def on_connect(user_id: int) -> None:
    '''Emits 'set_data' signal.
       If in game, revokes disconnect_timed_out task,
        calls on_reconnect()'''
    user = db.session.query(User).get(user_id)

    sio.emit('set_data',
             {'nickname': user.login,
              'rating': user.rating},
             room=user.sid)

    if user.cur_game_id:
        celery_task = db.session.query(CeleryTask).\
            filter(CeleryTask.type_id == ON_DISCONNECT_TIMED_OUT).\
            filter(CeleryTask.user_id == user_id).\
            filter(CeleryTask.game_id == user.cur_game_id).first()
        if celery_task:
            revoke(celery_task.id)
            db.session.delete(celery_task)
            db.session.commit()

        on_reconnect(user_id, user.cur_game_id)


@celery.task(name="on_disconnect", ignore_result=True)
def on_disconnect(user_id: int, game_id: int) -> None:
    '''Schedules on_disconnect_timed_out_task, adds it to database.
       Emits 'opp_disconnected' to the opponent'''
    task = on_disconnect_timed_out.apply_async(args=(user_id, game_id),
                                               countdown=60)
    celery_task = CeleryTask(id=task.id,
                             type_id=ON_DISCONNECT_TIMED_OUT,
                             game_id=game_id,
                             user_id=user_id,
                             eta=datetime.now() + timedelta(seconds=60))

    game = db.session.query(Game).get(game_id)
    opp_sid: int
    if user_id == game.user_white_pieces_id:
        opp_sid = game.user_black_pieces.sid
    else:
        opp_sid = game.user_white_pieces.sid

    sio.emit('opp_disconnected',
             {'wait_time': 60},
             room=opp_sid)

    db.session.add(celery_task)
    db.session.commit()


@celery.task(name='end_game', ignore_result=True)
def end_game(game_id: int, result: str,
             reason_white: str = '',
             reason_black: str = '',
             update_stats=True) -> None:
    '''Marks game as finished, emits 'game_ended' signal to users,
     closes the room,
     recalculates ratings and k-factors if update_stats is True'''

    game_celery_tasks = db.session.query(CeleryTask).\
        filter(CeleryTask.game_id == game_id)
    for task in game_celery_tasks:
        revoke(task.id)
        db.session.delete(task)

    game = db.session.query(Game).get(game_id)

    results = {'1-0': ('won', 'lost'),
               '1/2-1/2': ('draw', 'draw'),
               '0-1': ('lost', 'won'),
               '-': ('interrupted', 'interrupted')}

    result_white, result_black = results[result]
    sio.emit('game_ended',
             {'result': result_white,
              'reason': reason_white},
             room=game.user_white_pieces.sid)
    sio.emit('game_ended',
             {'result': result_black,
              'reason': reason_black},
             room=game.user_black_pieces.sid)

    close_room(game_id, namespace='/')

    game.is_finished = 1
    game.result = result

    game.user_white_pieces.cur_game_id = None
    game.user_black_pieces.cur_game_id = None

    db.session.merge(game)
    db.session.commit()

    if update_stats is False:
        return

    rating_changes = get_rating_changes(game_id)

    game.user_white_pieces.games_played += 1
    game.user_black_pieces.games_played += 1

    db.session.merge(game.user_white_pieces)
    db.session.merge(game.user_black_pieces)
    db.session.commit()

    if result == "1-0":
        update_rating.delay(game.user_white_pieces_id,
                            rating_changes["w"].win)
        update_rating.delay(game.user_black_pieces_id,
                            rating_changes["b"].lose)
    elif result == "1/2-1/2":
        update_rating.delay(game.user_white_pieces_id,
                            rating_changes["w"].draw)
        update_rating.delay(game.user_black_pieces_id,
                            rating_changes["b"].draw)
    elif result == "0-1":
        update_rating.delay(game.user_white_pieces_id,
                            rating_changes["w"].lose)
        update_rating.delay(game.user_black_pieces_id,
                            rating_changes["b"].win)

    update_k_factor.delay(game.user_white_pieces_id)
    update_k_factor.delay(game.user_black_pieces_id)


@celery.task(name="send_message", ignore_result=True)
def send_message(game_id: int, sender: str, message: str):
    '''Send chat message to game players'''
    sio.emit('get_message',
             {'sender': sender,
              'message': message},
             room=game_id)


@celery.task(name="on_first_move_timed_out", ignore_result=True)
def on_first_move_timed_out(game_id: int) -> None:
    """Interrupts game because of too long first move waiting"""
    game = db.session.query(Game).get(game_id)

    board = chess.Board(game.fen)

    reason_white = "You didn't make the first move"
    reason_black = "Your opponent didn't make the first move"
    if board.turn == chess.BLACK:
        reason_white, reason_black = reason_black, reason_white

    end_game(game_id, "-", reason_white, reason_black,
             update_stats=False)


@celery.task(name="on_disconnect_timed_out", ignore_results=True)
def on_disconnect_timed_out(user_id: int, game_id: int) -> None:
    game = db.session.query(Game).get(game_id)

    result = "1-0"
    reason_white = "Opponent was disconnected too long"
    reason_black = "You was disconnected too long"
    if user_id == game.user_white_pieces_id:
        result = "0-1"
        reason_white, reason_black = reason_black, reason_white

    end_game(game_id, result, reason_white, reason_black)


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
    game = db.session.query(Game).get(game_id)
    r_white = game.user_white_pieces.rating
    r_black = game.user_black_pieces.rating

    R_white = 10 ** (r_white / 400)
    R_black = 10 ** (r_black / 400)

    R_sum = R_white + R_black

    E_white = R_white / R_sum
    E_black = R_black / R_sum

    k_factor_white = game.user_white_pieces.k_factor
    k_factor_black = game.user_black_pieces.k_factor

    rating_change_white = RatingChange.from_formula(k_factor_white, E_white)
    rating_change_black = RatingChange.from_formula(k_factor_black, E_black)

    return {"w": rating_change_white,
            "b": rating_change_black}


@celery.task(name="update_k_factor", ignore_result=True)
def update_k_factor(user_id: int) -> None:
    '''Updates k_factor by FIDE rules (after 2014)'''
    user = db.session.query(User).get(user_id)

    if user.k_factor == 40 and user.games_played >= 30:
        user.k_factor = 20

    if user.k_factor == 20 and user.games_played >= 30 and user.rating >= 2400:
        user.k_factor = 10

    db.session.merge(user)
    db.session.commit()


@celery.task(name="update_rating", ignore_result=True)
def update_rating(user_id: int, rating_delta: float) -> None:
    '''Update database info about user's rating'''
    user = db.session.query(User).get(user_id)
    user.rating += rating_delta
    db.session.merge(user)
    db.session.commit()
