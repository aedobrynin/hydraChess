from datetime import datetime, timedelta
from typing import Dict, Optional
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


@celery.task(name='send_game_info', ignore_result=True)
def send_game_info(game_id: int, room_id: int, is_player: bool):
    request_datetime = datetime.utcnow()
    game = Game.get(game_id)

    #  rating_changes = get_rating_changes(game_id)

    data = {
        "black_user": {"nickname": game.black_user.login,
                       "rating": game.black_rating},
        "white_user": {"nickname": game.white_user.login,
                       "rating": game.white_rating},
        "moves": game.moves,
        "is_player": is_player
        }

    if is_player:
        data['color'] = 'w' if game.white_user.sid == room_id else 'b'

    if not game.is_finished:
        black_clock = timedelta(seconds=game.black_clock)
        white_clock = timedelta(seconds=game.white_clock)
        if game.moves:
            next_to_move = game.fen.split()[1]
            if next_to_move == 'w':
                white_clock -= request_datetime - game.last_move_datetime
            else:
                black_clock -= request_datetime - game.last_move_datetime

        data["black_clock"] = int(black_clock.total_seconds())
        data["white_clock"] = int(white_clock.total_seconds())
        if is_player:
            rating_changes = get_rating_changes(game_id)
            data["can_send_draw_offer"] = not game.draw_offer_try_this_move
            data['rating_changes'] = rating_changes[data['color']].to_dict()
    else:
        data["result"] = game.result

    sio.emit('game_started', data, room=room_id)


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

    send_game_info.delay(game_id, game.white_user.sid, True)
    send_game_info.delay(game_id, game.black_user.sid, True)
    sio.emit('first_move_waiting',
             {'wait_time': FIRST_MOVE_TIME_OUT},
             room=game.white_user.sid)


@celery.task(name='make_move', ignore_result=True)
def make_move(user_id: int, game_id: int, move_san: str) -> None:
    '''Updates game state by user's move.
       Calls end_game(...) if the game is ended.'''

    request_datetime = datetime.utcnow()

    game = Game.get(game_id)

    if game.is_finished or\
            user_id not in (game.white_user.id, game.black_user.id):
        return

    board = chess.Board(game.fen)
    is_user_white = user_id == game.white_user.id

    if (is_user_white and board.turn == chess.BLACK) or\
       (not is_user_white and board.turn == chess.WHITE):
        print(f"Wrong move side. User {User.get(user_id).login} "
              f"plays {is_user_white} color, but now is {board.turn} "
              f"turn. FEN: {game.fen}, move: {move_san}")
        return

    try:
        with rom.util.EntityLock(game, 10, 10):
            board.push_san(move_san)
            game.fen = board.fen()
            game.moves += (',' if game.moves else '') + move_san

            if game.first_move_timed_out_task_id:
                revoke(game.first_move_timed_out_task_id)
                game.first_move_timed_out_task_id = None

            if is_user_white:
                revoke(game.white_time_is_up_task_id)
            else:
                revoke(game.black_time_is_up_task_id)

            if game.draw_offer_sender and game.draw_offer_sender != user_id:
                # Decline draw offer only if it was asked by the opp
                # This call is waiting because of an entity lock
                decline_draw_offer.delay(user_id, game_id)
            game.draw_offer_try_this_move = False

            if is_user_white:
                white_clock = timedelta(seconds=game.white_clock) -\
                        (request_datetime - (game.last_move_datetime or
                                             request_datetime))
                game.white_clock = white_clock.total_seconds()

                eta = datetime.utcnow() + timedelta(seconds=game.black_clock)

                task = on_time_is_up.apply_async(args=(game.black_user.id,
                                                       game_id),
                                                 eta=eta)

                game.black_time_is_up_task_id = task.id
                game.black_time_is_up_task_eta = eta
            else:
                black_clock = timedelta(seconds=game.black_clock) -\
                        (request_datetime - (game.last_move_datetime or
                                             request_datetime))
                game.black_clock = black_clock.total_seconds()

                eta = datetime.utcnow() + timedelta(seconds=game.white_clock)

                task = on_time_is_up.apply_async(args=(game.white_user.id,
                                                       game_id),
                                                 eta=eta)

                game.white_time_is_up_task_id = task.id
                game.white_time_is_up_task_eta = eta

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

        data = {'san': move_san,
                'black_clock': game.black_clock,
                'white_clock': game.white_clock}

        sio.emit('game_updated', data, room=game_id)
        # DO NOT REMOVE NEXT STRING. SIO CAN'T EMIT TO SPECTATORS WITHOUT
        # THIS :/
        data = data
        sio.emit('game_updated', data, room=game.black_user.sid)
        sio.emit('game_updated', data, room=game.white_user.sid)

        result = board.result()
        if result != '*':
            reason: str
            if result == '1/2-1/2':
                reason = "Draw"
            elif result == '1-0':
                reason = "Checkmate. White won."
            else:
                reason = "Checkmate. Black won."

            end_game.delay(game_id, result, reason)
    except ValueError:
        pass


@celery.task(name="resign", ignore_result=True)
def resign(user_id: int, game_id: int) -> None:
    """Ends the game due to one player's resignation"""
    game = Game.get(game_id)

    # If there is no moves in the game, just cancel it.
    if not game.moves:
        end_game.delay(game_id, '-', 'Game canceled.', update_stats=False)
        return

    user_white = user_id == game.white_user.id

    result: str
    reason: str
    if user_white:
        result = "0-1"
        reason = "White resigned. Black won."
    else:
        result = "1-0"
        reason = "Black resigned. White won."

    end_game.delay(game_id, result, reason)


@celery.task(name="reconnect", ignore_result=True)
def reconnect(user_id: int, game_id: int) -> None:
    '''Emits fen, pieces color, info about the opponent and
        rating changes to player.
       Emits all info about timers (first move waiting, etc...)
       Emits 'opp_reconnected' to the opponent.'''

    game = Game.get(game_id)

    color_to_move = game.fen.split()[1]

    is_user_white = user_id == game.white_user.id

    if is_user_white:
        # Not ".delay()", because of bad emition order
        send_game_info(game_id, game.white_user.sid, True)
        if game.white_disconnect_timed_out_task_id:
            revoke(game.white_disconnect_timed_out_task_id)
            with rom.util.EntityLock(game, 10, 10):
                game.white_disconnect_timed_out_task_id = None
                game.save()

        sio.emit('opp_reconnected',
                 room=game.black_user.sid)

    else:
        send_game_info.delay(game_id, game.black_user.sid, True)

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


@celery.task(name="on_disconnect", ignore_result=True)
def on_disconnect(user_id: int, game_id: int) -> None:
    '''Schedules on_disconnect_timed_out_task, adds it to database.
       Emits 'opp_disconnected' to the opponent'''

    eta = datetime.utcnow() + timedelta(seconds=DISCONNECT_TIME_OUT)
    task = on_disconnect_timed_out.apply_async(args=(user_id, game_id),
                                               eta=eta)

    game = Game.get(game_id)

    if game.draw_offer_sender:
        #  We aren't checking user_id != draw_offer_sender
        #  It'll be checked in decline_draw_offer func
        decline_draw_offer.delay(user_id, game_id)

    is_user_white = user_id == game.white_user.id

    opp_sid: Optional[int]
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


@celery.task(name='make_draw_offer', ignore_result=True)
def make_draw_offer(user_id: int, game_id: int):
    '''Makes draw offer, if it's possible.'''
    game = Game.get(game_id)

    with rom.util.EntityLock(game, 10, 10):
        if game.draw_offer_sender and game.draw_offer_sender != user_id:
            #  Accept draw offer if it's already exist
            accept_draw_offer.delay(user_id, game_id)
        elif game.draw_offer_try_this_move:
            return

        game.draw_offer_try_this_move = True
        game.draw_offer_sender = user_id
        game.save()

    opp_sid = game.black_user.sid if user_id == game.white_user.id\
        else game.white_user.sid

    sio.emit('draw_offer', room=opp_sid)


@celery.task(name='accept_draw_offer', ignore_result=True)
def accept_draw_offer(user_id: int, game_id: int):
    '''Accepts draw offer, if it exists'''
    game = Game.get(game_id)

    with rom.util.EntityLock(game, 10, 10):
        if game.draw_offer_sender and game.draw_offer_sender != user_id:
            # opp_sid = User.get(game.draw_offer_sender).sid
            # sio.emit('draw_offer_accepted', room=opp_sid)
            game.draw_offer_sender = None
            game.save()
            end_game.delay(game_id, "1/2-1/2", "Draw.")


@celery.task(name='decline_draw_offer', ignore_result=True)
def decline_draw_offer(user_id: int, game_id: int):
    '''Declines draw offer, if it exists'''
    game = Game.get(game_id)

    with rom.util.EntityLock(game, 10, 10):
        if game.draw_offer_sender and game.draw_offer_sender != user_id:
            # opp_sid = User.get(game.draw_offer_sender).sid
            # sio.emit('draw_offer_declined', room=opp_sid)
            game.draw_offer_sender = None
            game.save()


@celery.task(name='end_game', ignore_result=True)
def end_game(game_id: int, result: str,
             reason: str, update_stats=True) -> None:
    '''Marks game as finished, emits 'game_ended' signal to users,
     closes the room,
     recalculates ratings and k-factors if update_stats is True'''

    game = Game.get(game_id)

    if game.is_finished:
        return

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

    data = {'result': result}
    sio.emit('game_ended', data, room=game_id)  # Emit to spectators

    data['reason'] = reason
    sio.emit('game_ended', data, room=game.white_user.sid)
    sio.emit('game_ended', data, room=game.black_user.sid)

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


# TODO
'''
@celery.task(name="send_message", ignore_result=True)
def send_message(game_id: int, sender: str, message: str):
    """Sends chat message to game players. Currently disabled."""
    game = Game.get(game_id)

    for sid in (game.white_user.sid, game.black_user.sid):
        if sid:
            sio.emit('get_message',
                     {'sender': sender,
                      'message': message},
                     room=sid)
'''


@celery.task(name="on_first_move_timed_out", ignore_result=True)
def on_first_move_timed_out(game_id: int) -> None:
    """Interrupts game because of user didn't make first move for too long"""
    end_game.delay(game_id, "-", 'Game cancelled', update_stats=False)


@celery.task(name="on_disconnect_timed_out", ignore_results=True)
def on_disconnect_timed_out(user_id: int, game_id: int) -> None:
    """Interrupts game because of user being disconnected for too long"""
    game = Game.get(game_id)

    is_user_white = user_id == game.white_user.id

    result: str
    reason: str
    if is_user_white:
        result = "0-1"
        reason = "White player disconnected. Black won."
    else:
        result = "1-0"
        reason = "Black player disconnected. White won."

    end_game(game_id, result, reason)


@celery.task(name="on_time_is_up", ignore_results=True)
def on_time_is_up(user_id: int, game_id: int) -> None:
    """Interrupts game because of user's time is up"""
    game = Game.get(game_id)

    board = chess.Board(game.fen)

    is_user_white = user_id == game.white_user.id

    result: str
    reason: str
    # Finish game with draw if other player has insufficient material to win
    if (is_user_white and board.has_insufficient_material(chess.BLACK)) or\
       (not is_user_white and board.has_insufficient_material(chess.WHITE)):
        result = "1/2-1/2"

        if user_id == game.white_user.id:
            reason = "White's time is up. Draw due to insufficient material."
        else:
            reason = "Black's time is up. Draw due to insufficient material."
    else:
        if user_id == game.white_user.id:
            result = "0-1"
            reason = "White's time is up."
        else:
            result = "1-0"
            reason = "Black's time is up."

    end_game.delay(game_id, result, reason)


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
def search_game(user_id: int, seconds: int) -> None:
    '''If there is appropriate game request, it starts a new game.
       Else it makes the game request and adds it to the database.'''
    user = User.get(user_id)
    with rom.util.EntityLock(user, 10, 10):
        game_requests = \
            rom.query.Query(GameRequest).filter(time=seconds).all()

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
                            total_clock=seconds,
                            white_clock=seconds,
                            black_clock=seconds,
                            white_rating=user.rating,
                            black_rating=user_to_play_with.rating,
                            is_started=0)
                game.save()

                user.cur_game_id = game.id
                user.save()

                with rom.util.EntityLock(user_to_play_with, 10, 10):
                    user_to_play_with.cur_game_id = game.id
                    user_to_play_with.in_search = False
                    user_to_play_with.save()

                sio.emit('redirect', {'url': f'/game/{game.id}'},
                         room=user.sid)
                sio.emit('redirect', {'url': f'/game/{game.id}'},
                         room=user_to_play_with.sid)
                start_game.delay(game.id)

        if added_to_existed is False:
            user.in_search = True
            user.save()

            game_request = GameRequest(time=seconds,
                                       user_id=user_id)
            game_request.save()


@celery.task(name="cancel_search", ignore_result=True)
def cancel_search(user_id: int):
    '''Cancel game search, if it's possible'''
    user = User.get(user_id)

    if not user.in_search:
        return

    with rom.util.EntityLock(user, 10, 10):
        user.in_search = False
        user.save()

    game_request = GameRequest.get_by(user_id=user_id,
                                      _limit=(0, 1))
    if game_request:
        game_request[0].delete()
