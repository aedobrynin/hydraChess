"""
    This module is needed to test the project under load.
    Bots will stop searching for new games after EXEC_TIME seconds.
    Use BOTS_QUANTITY constant in order to change bots quantity.
    The module doesn't run the server, because bots and the server should be
    runned on different servers in order to get accurate results.
    You have to provide URL to the server in ROOT_URL constant.
"""


from string import ascii_letters, digits
from random import choice, seed
from threading import Thread
import re
from time import sleep, time
from requests import Session
import chess
import socketio


ROOT_URL = "http://localhost:8000"
EXEC_TIME = 60 * 47
BOTS_QUANTITY = 100


def gen_login(length=8):
    login = ''.join([choice(ascii_letters) for _ in range(length)])
    return login


def gen_password(length=8):
    passwd = ''.join([choice(ascii_letters + digits) for _ in range(length)])
    return passwd


class Bot(Thread):
    def __init__(self):
        seed(time())
        Thread.__init__(self)

        self.sio = socketio.Client()
        self.session = Session()
        self.board = None

        self.sio.on('redirect', self.on_redirect)
        self.sio.on('game_started', self.on_game_started)
        self.sio.on('game_updated', self.on_game_updated)
        self.sio.on('game_ended', self.on_game_ended)

        self.start_time = None
        self.color = None
        self.game_id = None

    def run(self):
        self.start_time = time()

        self.register()

        self.session.close()

        cookies = ';'.join(map(lambda x: f"{x[0]}={x[1]}",
                               self.session.cookies.get_dict().items()))

        self.sio.connect(
            ROOT_URL + '?request_type=lobby',
            headers={'Cookie': cookies}
        )

        self.start_search()
        self.sio.wait()

    def register(self):
        url = f"{ROOT_URL}/sign_up"

        response = self.session.get(url)
        find_token = re.search(
            r'"csrf_token" type="hidden" value="([^"]*)"',
            response.text
        )
        csrf_token = find_token.groups()[0]

        login = gen_login()
        password = gen_password()

        self._name = f"{login}:{password}"

        data = {'login': login,
                'password': password,
                'csrf_token': csrf_token}
        data['confirm_password'] = data['password']

        response = self.session.post(url, data=data)
        assert response.url.rsplit('/', 1)[1] == 'lobby'

    def start_search(self):
        self.sio.emit('search_game', {'minutes': 1})

    def on_redirect(self, data):
        self.game_id = int(data['url'].split('/')[-1])

    def on_game_started(self, data):
        self.board = chess.Board()

        self.color = data['color'] == 'w'

        if self.color == self.board.turn:
            self.sio.sleep(2)
            self.make_move()

    def make_move(self):
        possible_moves = list(self.board.legal_moves)
        move = choice(possible_moves)
        self.sio.emit(
            'make_move',
            {
                "san": self.board.san(move),
                "game_id": self.game_id
            }
        )

    def on_game_updated(self, data):
        self.board.push_san(data['san'])

        if self.board.is_game_over() is False \
                and self.color == self.board.turn:
            self.sio.sleep(2)
            self.make_move()

    def on_game_ended(self, data):
        if time() - self.start_time > EXEC_TIME:
            return
        self.start_search()


if __name__ == "__main__":
    threads = list()
    for i in range(BOTS_QUANTITY):
        threads.append(Bot())

    for i, thread in enumerate(threads):
        sleep(2)
        thread.start()
        print(f"Started: {i + 1}/{BOTS_QUANTITY}")

    print("Bots're started")

    for thread in threads:
        thread.join()
